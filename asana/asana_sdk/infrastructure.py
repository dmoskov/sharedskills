#!/usr/bin/env python3
"""
Asana SDK Infrastructure

Shared utilities for Asana API client:
- Client singleton management
- Token lifecycle and refresh logic
- Rate limiting hooks (pluggable)
- Error handling decorator
- Alert hooks (pluggable)
"""

import inspect
import json
import os
import logging
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Dict, Optional, Any, Callable, Tuple

# Configure logging
logger = logging.getLogger(__name__)

# Import error classes
from .errors import (
    AsanaClientError,
    AsanaAuthenticationError,
    AsanaRateLimitError,
    AsanaNotFoundError,
    AsanaValidationError,
    AsanaServerError,
)

# Import TokenManager
from .token_manager import TokenManager, DEFAULT_TOKEN_FILE

# Load environment variables from .env file (optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import Asana SDK
try:
    import asana
    from asana.rest import ApiException

    ASANA_SDK_AVAILABLE = True
except ImportError:
    asana = None  # type: ignore
    ApiException = Exception  # Fallback to base Exception class
    ASANA_SDK_AVAILABLE = False
    logger.debug("Asana SDK not available. Install with: pip install asana")


# ============================================================================
# Configuration
# ============================================================================

class AsanaSDKConfig:
    """
    Global configuration for the Asana SDK.

    Provides hooks for:
    - Alert callbacks (for algedonic channel or other notification systems)
    - Rate limit callbacks (for circuit breakers, distributed tracking)
    - Token file path
    - Help command for authentication errors
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_defaults()
        return cls._instance

    def _init_defaults(self):
        self.token_file = Path(os.environ.get("ASANA_TOKEN_FILE", str(DEFAULT_TOKEN_FILE)))
        self.refresh_help_command = os.environ.get(
            "ASANA_REFRESH_HELP_CMD",
            "re-authenticate with Asana OAuth"
        )

        # Alert callback: (severity, category, message, context) -> None
        self._alert_callback: Optional[Callable[[str, str, str, Optional[Dict]], None]] = None

        # Rate limit check callback: () -> Tuple[can_proceed: bool, reason: str]
        self._rate_limit_check: Optional[Callable[[], Tuple[bool, str]]] = None

        # Rate limit record callback: (success: bool, error: Optional[Exception]) -> None
        self._rate_limit_record: Optional[Callable[[bool, Optional[Exception]], None]] = None

        # Token manager instance
        self._token_manager: Optional[TokenManager] = None

    @property
    def token_manager(self) -> TokenManager:
        if self._token_manager is None:
            self._token_manager = TokenManager(
                token_file=self.token_file,
                refresh_help_command=self.refresh_help_command
            )
        return self._token_manager

    def set_alert_callback(self, callback: Callable[[str, str, str, Optional[Dict]], None]):
        """
        Set a callback for raising alerts.

        Args:
            callback: Function that accepts (severity, category, message, context)
                     severity: 'critical', 'urgent', or 'warning'
                     category: Alert category string (e.g., 'auth_expired', 'rate_limit_hit')
                     message: Human-readable alert message
                     context: Optional dict with additional context
        """
        self._alert_callback = callback

    def set_rate_limit_hooks(
        self,
        check_callback: Callable[[], Tuple[bool, str]],
        record_callback: Callable[[bool, Optional[Exception]], None]
    ):
        """
        Set callbacks for rate limit management.

        Args:
            check_callback: Function that returns (can_proceed, reason)
            record_callback: Function that accepts (success, error)
        """
        self._rate_limit_check = check_callback
        self._rate_limit_record = record_callback


def get_config() -> AsanaSDKConfig:
    """Get the global SDK configuration."""
    return AsanaSDKConfig()


# ============================================================================
# Alert System
# ============================================================================

def raise_alert(
    severity: str,
    category: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Raise an alert for Asana client issues.

    Uses configured alert callback if available, otherwise logs.

    Args:
        severity: Alert severity - 'critical', 'urgent', or 'warning'
        category: Alert category (e.g., 'auth_expired', 'rate_limit_hit')
        message: Human-readable alert message
        context: Additional context as key-value pairs
    """
    config = get_config()

    if config._alert_callback:
        try:
            config._alert_callback(severity, category, message, context)
            logger.debug(f"Alert dispatched: [{severity}] {category}: {message}")
            return
        except Exception as e:
            logger.warning(f"Alert callback failed: {e}")

    # Fall back to logging
    log_level = {
        "critical": logging.CRITICAL,
        "urgent": logging.ERROR,
        "warning": logging.WARNING,
    }.get(severity, logging.WARNING)

    logger.log(log_level, f"[ALERT-{severity.upper()}] {category}: {message}")


# ============================================================================
# Rate Limiting
# ============================================================================

def check_rate_limits() -> Tuple[bool, str]:
    """
    Check rate limits before making API call.

    Returns:
        Tuple of (can_proceed, reason)
    """
    config = get_config()

    if config._rate_limit_check:
        try:
            return config._rate_limit_check()
        except Exception as e:
            logger.warning(f"Rate limit check failed: {e}")

    # No rate limiting configured - allow request
    return True, ""


def record_rate_limit_result(success: bool, error: Optional[Exception] = None):
    """
    Record the result of an API call for rate limit tracking.

    Args:
        success: Whether the API call succeeded
        error: Optional error if call failed
    """
    config = get_config()

    if config._rate_limit_record:
        try:
            config._rate_limit_record(success, error)
        except Exception as e:
            logger.warning(f"Failed to record rate limit result: {e}")


# ============================================================================
# Error Handling Decorator
# ============================================================================

def with_api_error_handling(operation_fmt: str) -> Callable:
    """
    Decorator to handle API exceptions consistently across all operations.

    Args:
        operation_fmt: Description format string for the operation.
                      Can use {arg_name} placeholders filled from function arguments.

    Example:
        @with_api_error_handling("fetching task {task_gid}")
        def get_asana_task(task_gid: str) -> Dict:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build operation string from function arguments
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            try:
                operation = operation_fmt.format(**bound_args.arguments)
            except (KeyError, ValueError):
                operation = operation_fmt

            # Check rate limits
            can_proceed, reason = check_rate_limits()
            if not can_proceed:
                raise AsanaRateLimitError(f"Rate limit check failed: {reason}")

            try:
                result = func(*args, **kwargs)
                record_rate_limit_result(success=True)
                return result
            except (ValueError, TypeError):
                # Re-raise validation errors without wrapping
                raise
            except ApiException as e:
                record_rate_limit_result(success=False, error=e)
                handle_api_exception(e, operation)

        return wrapper
    return decorator


# ============================================================================
# Asana Client Singleton
# ============================================================================

class AsanaClientSingleton:
    """Singleton to manage Asana API client instance."""

    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_client(self) -> "asana.ApiClient":
        """
        Get Asana API client with valid token.

        Returns:
            Configured asana.ApiClient instance (v5.x)
        """
        if not ASANA_SDK_AVAILABLE:
            raise AsanaClientError(
                "Asana SDK not available. Install with: pip install asana"
            )

        config = get_config()
        access_token = config.token_manager.get_valid_token()

        # Create configuration with token (v5.x API)
        configuration = asana.Configuration()
        configuration.access_token = access_token

        return asana.ApiClient(configuration)


def get_client() -> "asana.ApiClient":
    """Get configured Asana API client (v5.x)."""
    return AsanaClientSingleton().get_client()


# ============================================================================
# API Exception Handling
# ============================================================================

def handle_api_exception(e: "ApiException", operation: str) -> None:
    """
    Convert Asana ApiException to appropriate custom exception.

    Also raises alerts for critical issues.

    Args:
        e: ApiException from Asana SDK
        operation: Description of operation that failed

    Raises:
        Appropriate AsanaClientError subclass
    """
    status = e.status

    # Try to parse error body
    try:
        error_data = json.loads(e.body) if e.body else {}
        error_msg = error_data.get("errors", [{}])[0].get("message", str(e))
    except (json.JSONDecodeError, KeyError, IndexError):
        error_msg = str(e)

    config = get_config()

    if status == 401:
        # Try to refresh token
        logger.warning(f"Got 401 during {operation}, attempting token refresh...")
        try:
            config.token_manager.get_valid_token()  # Will refresh if needed
            raise AsanaAuthenticationError(
                f"Authentication failed during {operation}. "
                f"Token has been refreshed, please retry the operation."
            )
        except Exception as refresh_error:
            raise_alert(
                severity="critical",
                category="auth_expired",
                message="Asana authentication token has expired and refresh failed",
                context={
                    "endpoint": operation,
                    "error": str(refresh_error),
                    "http_status": 401,
                    "remediation": config.refresh_help_command,
                },
            )
            raise AsanaAuthenticationError(
                f"Authentication failed during {operation}: {error_msg}\n"
                f"Token refresh also failed: {refresh_error}"
            )

    elif status == 403:
        raise AsanaAuthenticationError(
            f"Permission denied during {operation}: {error_msg}\n"
            f"Check that your Asana account has access to this resource."
        )

    elif status == 404:
        raise AsanaNotFoundError(
            f"Resource not found during {operation}: {error_msg}\n"
            f"Verify the GID is correct and the resource exists."
        )

    elif status == 400:
        raise AsanaValidationError(
            f"Invalid request during {operation}: {error_msg}\n"
            f"Check the parameters and try again."
        )

    elif status == 429:
        retry_after = None
        if hasattr(e, "headers") and "Retry-After" in e.headers:
            try:
                retry_after = int(e.headers["Retry-After"])
            except ValueError:
                pass

        raise_alert(
            severity="urgent",
            category="rate_limit_hit",
            message=f"Asana API rate limit exceeded during {operation}",
            context={
                "endpoint": operation,
                "retry_after_seconds": retry_after,
                "error": error_msg,
                "http_status": 429,
            },
        )

        raise AsanaRateLimitError(
            f"Rate limit exceeded during {operation}: {error_msg}",
            retry_after=retry_after,
        )

    elif status >= 500:
        raise_alert(
            severity="warning",
            category="api_server_error",
            message=f"Asana server error (HTTP {status}) during {operation}",
            context={
                "endpoint": operation,
                "status_code": status,
                "error": error_msg,
            },
        )

        raise AsanaServerError(
            f"Server error during {operation} (HTTP {status}): {error_msg}\n"
            f"This is an Asana server issue. Try again in a few minutes."
        )

    else:
        raise AsanaClientError(
            f"Unexpected error during {operation} (HTTP {status}): {error_msg}"
        )
