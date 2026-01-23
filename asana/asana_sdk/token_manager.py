#!/usr/bin/env python3
"""
Asana OAuth Token Manager

Manages OAuth token lifecycle including loading, saving, refreshing, and expiry checking.
Supports multiple token sources: local file, environment variables, and AWS Secrets Manager.

Design Philosophy:
- Fail loudly with clear error messages
- Automatic token refresh when expired
- Secure token storage with proper file permissions
- Replay attack protection (when available)
"""

import hashlib
import json
import os
import time
import urllib.request
import urllib.parse
import urllib.error
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from .errors import AsanaAuthenticationError

# Configure logging
logger = logging.getLogger(__name__)

# Import replay protection (optional)
try:
    from token_refresh_protection import RefreshProtector, ReplayAttackDetected

    REPLAY_PROTECTION_AVAILABLE = True
except ImportError:
    RefreshProtector = None  # type: ignore
    ReplayAttackDetected = Exception  # type: ignore
    REPLAY_PROTECTION_AVAILABLE = False
    logger.debug("Replay protection not available")

# Import boto3 for AWS Secrets Manager (optional)
try:
    import boto3

    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None  # type: ignore
    BOTO3_AVAILABLE = False
    logger.debug("boto3 not available - Secrets Manager integration disabled")


# Default token file path (can be overridden)
DEFAULT_TOKEN_FILE = Path.home() / ".config" / "asana" / "tokens.json"


class TokenManager:
    """
    Manages OAuth token lifecycle for Asana API access.

    Supports three token resolution strategies:
    1. AWS Secrets Manager (via ASANA_OAUTH_SECRET env var)
    2. Static token from environment (ASANA_ACCESS_TOKEN)
    3. Local file-based OAuth tokens with auto-refresh

    Example:
        manager = TokenManager(token_file_path)
        token = manager.get_valid_token()  # Returns valid token, refreshing if needed
    """

    def __init__(
        self,
        token_file: Path = None,
        warn_threshold_seconds: int = 300,
        refresh_help_command: str = None,
    ):
        """
        Initialize TokenManager.

        Args:
            token_file: Path to JSON file storing OAuth tokens (default: ~/.config/asana/tokens.json)
            warn_threshold_seconds: Warning threshold for token expiry (default 5 minutes)
            refresh_help_command: Command to show in error messages for re-authentication
        """
        self.token_file = token_file or DEFAULT_TOKEN_FILE
        self.warn_threshold_seconds = warn_threshold_seconds
        self.refresh_help_command = refresh_help_command or "re-authenticate with Asana OAuth"
        self._cache: Optional[Dict[str, Any]] = None

    def get_valid_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.

        Token resolution order:
        1. ASANA_ACCESS_TOKEN env var (static token - legacy)
        2. ASANA_OAUTH_SECRET env var (Secrets Manager ARN with OAuth credentials for auto-refresh)
        3. Local token file

        For ECS/remote execution, set ASANA_OAUTH_SECRET to enable auto-refresh.
        The secret should contain JSON with: refresh_token, client_id, client_secret

        Returns:
            Valid access token string

        Raises:
            AsanaAuthenticationError: If unable to get valid token
        """
        # Check for OAuth secret ARN (AWS ECS with auto-refresh capability)
        oauth_secret = os.environ.get("ASANA_OAUTH_SECRET")
        if oauth_secret:
            return self._get_token_from_secrets_manager(oauth_secret)

        # Check for static access token (legacy - no auto-refresh)
        env_token = os.environ.get("ASANA_ACCESS_TOKEN")
        if env_token:
            logger.debug(
                "Using ASANA_ACCESS_TOKEN from environment variable (no auto-refresh)"
            )
            # Strip whitespace/newlines that may come from Secrets Manager
            return env_token.strip()

        # Fall back to token file (local development)
        tokens = self.load_tokens()

        # Check if token needs refresh
        if self.is_token_expired(tokens):
            logger.info("Access token expired or expiring soon, refreshing...")
            tokens = self.refresh_token(tokens)

        # Check for token expiring soon (within threshold) and raise warning
        self.check_token_expiry_warning(tokens)

        return tokens["access_token"]

    def load_tokens(self) -> Dict[str, Any]:
        """
        Load OAuth tokens from JSON file.

        Returns:
            Dictionary with access_token, refresh_token, expires_at, etc.

        Raises:
            AsanaAuthenticationError: If tokens cannot be loaded
        """
        if not self.token_file.exists():
            raise AsanaAuthenticationError(
                f"Token file not found: {self.token_file}\n"
                f"Please {self.refresh_help_command}"
            )

        try:
            with open(self.token_file) as f:
                tokens = json.load(f)

            if "access_token" not in tokens:
                raise AsanaAuthenticationError(
                    f"Invalid token file: missing access_token\n"
                    f"Please {self.refresh_help_command}"
                )

            logger.debug("Loaded tokens from JSON file")
            return tokens

        except json.JSONDecodeError as e:
            raise AsanaAuthenticationError(
                f"Token file is corrupt: {e}\n"
                f"Please {self.refresh_help_command}"
            )

    def save_tokens(self, tokens: Dict[str, Any]):
        """
        Save OAuth tokens to JSON file with secure permissions.

        Args:
            tokens: Dictionary with access_token, refresh_token, etc.
        """
        self.token_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.token_file, "w") as f:
            json.dump(tokens, f, indent=2)

        # Set file permissions to 0600 (owner read/write only)
        os.chmod(self.token_file, 0o600)

        logger.info(f"Tokens saved to {self.token_file} (permissions: 0600)")

    def is_token_expired(self, tokens: Dict[str, Any]) -> bool:
        """
        Check if access token is expired or expiring soon.

        Returns:
            True if token is expired or expires in <30 minutes

        Note: We refresh proactively at 30 minutes to:
        - Ensure token is always fresh BEFORE the warning threshold (default 5 minutes)
        - Provide ample time for retries if refresh fails (3 retries with exponential backoff)
        - Prevent rate limiting exhaustion from frequent refresh attempts
        """
        expires_at = tokens.get("expires_at")
        if not expires_at:
            # If no expiry info, assume needs refresh
            return True

        try:
            if isinstance(expires_at, (int, float)):
                expiry_time = datetime.fromtimestamp(expires_at, tz=timezone.utc)
            else:
                expiry_time = datetime.fromisoformat(
                    str(expires_at).replace("Z", "+00:00")
                )

            now = datetime.now(timezone.utc)
            time_until_expiry = expiry_time - now

            # Refresh if expires in <30 minutes (proactive refresh with better safety margin)
            return time_until_expiry.total_seconds() < 1800

        except (ValueError, TypeError) as e:
            logger.warning(f"Could not parse expiry time: {e}")
            return True

    def refresh_token(
        self, tokens: Dict[str, Any], max_retries: int = 3, initial_backoff: float = 1.0
    ) -> Dict[str, Any]:
        """
        Refresh access token using refresh token with replay attack protection and retry logic.

        Args:
            tokens: Current token data with refresh_token
            max_retries: Maximum number of retry attempts for transient failures (default: 3)
            initial_backoff: Initial backoff delay in seconds for exponential backoff (default: 1.0)

        Returns:
            New token data

        Raises:
            AsanaAuthenticationError: If refresh fails after all retries
        """
        # Initialize replay protection if available
        if REPLAY_PROTECTION_AVAILABLE:
            protector = RefreshProtector()
            replay_protection_enabled = protector.enabled
        else:
            protector = None
            replay_protection_enabled = False

        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            raise AsanaAuthenticationError(
                f"No refresh token available. Please re-authenticate.\n"
                f"Please {self.refresh_help_command}"
            )

        # Prepare refresh request with replay protection
        nonce = None
        timestamp = None
        refresh_token_hash = None

        if replay_protection_enabled:
            try:
                nonce, timestamp = protector.prepare_refresh_request(refresh_token)
                refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
                logger.info(f"Replay protection enabled: nonce={nonce}")
            except ReplayAttackDetected as e:
                error_msg = f"SECURITY: Replay attack detected - {e}"
                logger.error(error_msg)
                raise AsanaAuthenticationError(
                    "Replay attack detected during token refresh.\n"
                    "This request was blocked for security reasons.\n"
                    "Check security logs immediately."
                )
            except Exception as e:
                logger.warning(f"Replay protection check failed: {e}")
                # Continue without protection rather than blocking refresh

        # Get OAuth credentials from environment
        client_id = os.environ.get("ASANA_CLIENT_ID")
        client_secret = os.environ.get("ASANA_CLIENT_SECRET")

        if not client_id or not client_secret:
            error_msg = "ASANA_CLIENT_ID or ASANA_CLIENT_SECRET not set in environment"

            # Record failed attempt if protection enabled
            if replay_protection_enabled and nonce:
                try:
                    protector.record_failed_refresh(
                        nonce, timestamp, refresh_token_hash, error_msg
                    )
                except Exception as log_error:
                    logger.warning(f"Failed to log refresh failure: {log_error}")

            raise AsanaAuthenticationError(
                f"{error_msg}.\nCheck .env file or environment variables."
            )

        # Make refresh request with exponential backoff retry logic
        TOKEN_URL = "https://app.asana.com/-/oauth_token"
        request_data = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        }

        # Wrap retry loop in try-except to handle final errors
        try:
            # Retry loop for transient network failures
            last_error = None
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        backoff_delay = initial_backoff * (
                            2 ** (attempt - 1)
                        )  # Exponential backoff: 1s, 2s, 4s
                        logger.info(
                            f"Retry attempt {attempt + 1}/{max_retries} after {backoff_delay}s delay..."
                        )
                        time.sleep(backoff_delay)

                    req = urllib.request.Request(
                        TOKEN_URL,
                        data=urllib.parse.urlencode(request_data).encode(),
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )

                    with urllib.request.urlopen(req, timeout=30) as response:
                        new_tokens = json.load(response)

                    # Success! Break out of retry loop
                    break

                except urllib.error.HTTPError as e:
                    # Retry on 5xx server errors, but not on 4xx client errors
                    if 500 <= e.code < 600 and attempt < max_retries - 1:
                        logger.warning(
                            f"Server error {e.code} on attempt {attempt + 1}, will retry..."
                        )
                        last_error = e
                        continue
                    else:
                        raise

                except urllib.error.URLError as e:
                    last_error = e
                    error_reason = str(e.reason)

                    is_retryable = (
                        "timed out" in error_reason.lower()
                        or "timeout" in error_reason.lower()
                        or "name or service not known" in error_reason.lower()
                        or "nodename nor servname" in error_reason.lower()
                        or "connection refused" in error_reason.lower()
                        or "network" in error_reason.lower()
                    )

                    if is_retryable and attempt < max_retries - 1:
                        logger.warning(
                            f"Network error on attempt {attempt + 1}: {error_reason}"
                        )
                        continue
                    else:
                        raise

            else:
                if last_error:
                    raise last_error
                else:
                    raise Exception("Retry loop completed without success or error")

            # Check for token rotation (OAuth 2.0 best practice)
            if "refresh_token" not in new_tokens:
                logger.warning(
                    "Asana did not rotate refresh token (OAuth 2.0 best practice violation)"
                )
                new_tokens["refresh_token"] = refresh_token
            else:
                logger.info("Refresh token rotated successfully")

            # Calculate expiry time
            expires_in = new_tokens.get("expires_in", 3600)
            new_tokens["expires_at"] = (
                datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            ).isoformat()
            new_tokens["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Preserve user data
            if "data" in tokens:
                new_tokens["data"] = tokens["data"]

            # Save new tokens
            self.save_tokens(new_tokens)

            # Record successful refresh with replay protection
            if replay_protection_enabled and nonce:
                try:
                    protector.record_successful_refresh(
                        nonce,
                        timestamp,
                        refresh_token_hash,
                        new_tokens["refresh_token"],
                    )
                    logger.info("Refresh logged securely")
                except Exception as e:
                    logger.warning(f"Failed to log refresh attempt: {e}")

            logger.info("Access token refreshed successfully")
            return new_tokens

        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else "No error details"
            error_msg = f"Token refresh failed after {max_retries} attempts (HTTP {e.code}): {error_body}"

            if replay_protection_enabled and nonce:
                try:
                    protector.record_failed_refresh(
                        nonce, timestamp, refresh_token_hash, error_msg
                    )
                except Exception as log_error:
                    logger.warning(f"Failed to log refresh failure: {log_error}")

            raise AsanaAuthenticationError(
                f"{error_msg}\n"
                f"You may need to re-authenticate.\n"
                f"Please {self.refresh_help_command}"
            )

        except urllib.error.URLError as e:
            error_reason = str(e.reason)
            error_msg = f"Token refresh failed after {max_retries} attempts: Network error: {error_reason}"

            if replay_protection_enabled and nonce:
                try:
                    protector.record_failed_refresh(
                        nonce, timestamp, refresh_token_hash, error_msg
                    )
                except Exception as log_error:
                    logger.warning(f"Failed to log refresh failure: {log_error}")

            raise AsanaAuthenticationError(
                f"{error_msg}\nPlease {self.refresh_help_command}"
            )

        except Exception as e:
            error_msg = f"Token refresh failed after {max_retries} attempts: {type(e).__name__}: {e}"

            if replay_protection_enabled and nonce:
                try:
                    protector.record_failed_refresh(
                        nonce, timestamp, refresh_token_hash, error_msg
                    )
                except Exception as log_error:
                    logger.warning(f"Failed to log refresh failure: {log_error}")

            raise AsanaAuthenticationError(
                f"{error_msg}\nPlease {self.refresh_help_command}"
            )

    def check_token_expiry_warning(
        self, tokens: Dict[str, Any], alert_callback: Optional[Callable] = None
    ) -> None:
        """
        Check if token is expiring soon and raise warning.

        Args:
            tokens: Token data dictionary
            alert_callback: Optional callback function for raising alerts.
                          Should accept (severity, category, message, context) parameters.
        """
        expires_at = tokens.get("expires_at")
        if not expires_at:
            return

        try:
            if isinstance(expires_at, (int, float)):
                expiry_time = datetime.fromtimestamp(expires_at, tz=timezone.utc)
            else:
                expiry_time = datetime.fromisoformat(
                    str(expires_at).replace("Z", "+00:00")
                )

            now = datetime.now(timezone.utc)
            time_until_expiry = expiry_time - now
            seconds_remaining = time_until_expiry.total_seconds()

            if 0 < seconds_remaining < self.warn_threshold_seconds:
                minutes_remaining = (seconds_remaining % 3600) / 60

                if alert_callback:
                    alert_callback(
                        severity="warning",
                        category="token_expiring_soon",
                        message=f"Asana OAuth token expires in {int(minutes_remaining)} minutes",
                        context={
                            "expiry_time": expiry_time.isoformat(),
                            "minutes_remaining": int(minutes_remaining),
                            "seconds_remaining": int(seconds_remaining),
                            "remediation": f"Token will auto-refresh on next API call, or {self.refresh_help_command}",
                        },
                    )

        except (ValueError, TypeError) as e:
            logger.debug(f"Could not check token expiry warning: {e}")

    def _get_token_from_secrets_manager(
        self, secret_arn: str, max_retries: int = 3, initial_backoff: float = 1.0
    ) -> str:
        """
        Get a valid access token from AWS Secrets Manager with auto-refresh.

        Args:
            secret_arn: ARN or name of the Secrets Manager secret
            max_retries: Maximum number of retry attempts
            initial_backoff: Initial backoff delay in seconds

        Returns:
            Valid access token string

        Raises:
            AsanaAuthenticationError: If unable to get valid token
        """
        if not BOTO3_AVAILABLE:
            raise AsanaAuthenticationError(
                "boto3 is required for Secrets Manager integration.\n"
                "Install with: pip install boto3"
            )

        logger.debug(f"Loading OAuth credentials from Secrets Manager: {secret_arn}")

        region = os.environ.get("SECRETS_REGION") or os.environ.get(
            "AWS_REGION", "us-west-1"
        )
        client = boto3.client("secretsmanager", region_name=region)

        try:
            response = client.get_secret_value(SecretId=secret_arn)
            secret_data = json.loads(response["SecretString"])
        except Exception as e:
            raise AsanaAuthenticationError(
                f"Failed to load OAuth credentials from Secrets Manager: {e}\n"
                f"Secret: {secret_arn}"
            )

        refresh_token = secret_data.get("refresh_token")
        client_id = secret_data.get("client_id")
        client_secret = secret_data.get("client_secret")

        if not all([refresh_token, client_id, client_secret]):
            raise AsanaAuthenticationError(
                f"Secret {secret_arn} missing required fields.\n"
                f"Required: refresh_token, client_id, client_secret"
            )

        # Check if we have a valid cached access token
        access_token = secret_data.get("access_token")
        expires_at = secret_data.get("expires_at")

        if access_token and expires_at:
            try:
                if isinstance(expires_at, (int, float)):
                    expiry_time = datetime.fromtimestamp(expires_at, tz=timezone.utc)
                else:
                    expiry_time = datetime.fromisoformat(
                        str(expires_at).replace("Z", "+00:00")
                    )

                if (expiry_time - datetime.now(timezone.utc)).total_seconds() > 1800:
                    logger.debug("Using cached access token from Secrets Manager")
                    return access_token
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not parse cached token expiry: {e}")

        # Need to refresh the token
        logger.info("Refreshing Asana access token via OAuth...")

        TOKEN_URL = "https://app.asana.com/-/oauth_token"
        request_data = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        }

        try:
            last_error = None
            new_tokens = None

            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        backoff_delay = initial_backoff * (2 ** (attempt - 1))
                        logger.info(
                            f"Retry attempt {attempt + 1}/{max_retries} after {backoff_delay}s delay..."
                        )
                        time.sleep(backoff_delay)

                    req = urllib.request.Request(
                        TOKEN_URL,
                        data=urllib.parse.urlencode(request_data).encode(),
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )

                    with urllib.request.urlopen(req, timeout=30) as response:
                        new_tokens = json.load(response)

                    break

                except urllib.error.HTTPError as e:
                    if 500 <= e.code < 600 and attempt < max_retries - 1:
                        logger.warning(f"Server error {e.code} on attempt {attempt + 1}, will retry...")
                        last_error = e
                        continue
                    else:
                        raise

                except urllib.error.URLError as e:
                    last_error = e
                    error_reason = str(e.reason)

                    is_retryable = (
                        "timed out" in error_reason.lower()
                        or "timeout" in error_reason.lower()
                        or "connection refused" in error_reason.lower()
                        or "network" in error_reason.lower()
                    )

                    if is_retryable and attempt < max_retries - 1:
                        logger.warning(f"Network error on attempt {attempt + 1}: {error_reason}")
                        continue
                    else:
                        raise

            else:
                if last_error:
                    raise last_error
                else:
                    raise Exception("Retry loop completed without success or error")

            new_access_token = new_tokens.get("access_token")
            if not new_access_token:
                raise AsanaAuthenticationError("OAuth refresh response missing access_token")

            expires_in = new_tokens.get("expires_in", 3600)
            new_expires_at = (
                datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            ).isoformat()

            # Update the secret with new access token (for caching)
            secret_data["access_token"] = new_access_token
            secret_data["expires_at"] = new_expires_at
            if "refresh_token" in new_tokens:
                secret_data["refresh_token"] = new_tokens["refresh_token"]
                logger.info("Refresh token rotated by Asana")

            try:
                client.put_secret_value(
                    SecretId=secret_arn, SecretString=json.dumps(secret_data)
                )
                logger.info("Updated Secrets Manager with new access token")
            except Exception as e:
                logger.warning(f"Failed to update Secrets Manager cache: {e}")

            logger.info(f"Access token refreshed successfully after {attempt + 1} attempt(s)")
            return new_access_token

        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else "No error details"
            raise AsanaAuthenticationError(
                f"OAuth refresh failed after {max_retries} attempts (HTTP {e.code}): {error_body}\n"
                f"The refresh token may be invalid. Re-authenticate and update the secret."
            )

        except urllib.error.URLError as e:
            error_reason = str(e.reason)
            raise AsanaAuthenticationError(
                f"OAuth refresh failed after {max_retries} attempts: Network error: {error_reason}\n"
                f"The refresh token may be invalid. Re-authenticate and update the secret."
            )

        except Exception as e:
            raise AsanaAuthenticationError(
                f"OAuth refresh failed after {max_retries} attempts: {type(e).__name__}: {e}\n"
                f"The refresh token may be invalid. Re-authenticate and update the secret."
            )
