#!/usr/bin/env python3
"""
Configuration loader and validator for Discord bots.

Provides clear error messages when configuration is invalid or incomplete.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    def __init__(self, errors: List[str]):
        self.errors = errors
        message = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        super().__init__(message)


class ConfigValidator:
    """Validates bot configuration files."""

    # Discord token format: base64.base64.base64
    DISCORD_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")

    # Letta agent ID format: agent-uuid
    AGENT_ID_PATTERN = re.compile(r"^agent-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$")

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.errors: List[str] = []

    def validate(self) -> bool:
        """
        Validate the entire configuration.

        Returns True if valid, raises ConfigValidationError if invalid.
        """
        self.errors = []

        # Check top-level structure
        if not isinstance(self.config, dict):
            self.errors.append("Config must be a JSON object")
            raise ConfigValidationError(self.errors)

        # Validate letta_url if present
        self._validate_letta_url()

        # Validate bots section
        self._validate_bots_section()

        if self.errors:
            raise ConfigValidationError(self.errors)

        return True

    def _validate_letta_url(self) -> None:
        """Validate the letta_url field."""
        letta_url = self.config.get("letta_url")

        if letta_url is not None:
            if not isinstance(letta_url, str):
                self.errors.append(f"'letta_url' must be a string, got {type(letta_url).__name__}")
            elif not letta_url.startswith(("http://", "https://")):
                self.errors.append(f"'letta_url' must be a valid HTTP(S) URL, got: {letta_url}")

    def _validate_bots_section(self) -> None:
        """Validate the bots section."""
        if "bots" not in self.config:
            self.errors.append("Missing required field 'bots'")
            return

        bots = self.config["bots"]

        if not isinstance(bots, dict):
            self.errors.append(f"'bots' must be an object, got {type(bots).__name__}")
            return

        if not bots:
            self.errors.append("'bots' must contain at least one bot configuration")
            return

        for bot_name, bot_config in bots.items():
            self._validate_bot_config(bot_name, bot_config)

    def _validate_bot_config(self, bot_name: str, bot_config: Any) -> None:
        """Validate a single bot configuration."""
        prefix = f"bots.{bot_name}"

        if not isinstance(bot_config, dict):
            self.errors.append(f"'{prefix}' must be an object, got {type(bot_config).__name__}")
            return

        # Required fields
        self._validate_discord_token(prefix, bot_config)
        self._validate_agent_id(prefix, bot_config)

        # Optional fields
        self._validate_enable_attachments(prefix, bot_config)

    def _validate_discord_token(self, prefix: str, bot_config: Dict) -> None:
        """Validate the discord_token field."""
        field = "discord_token"

        if field not in bot_config:
            self.errors.append(f"'{prefix}' missing required field '{field}'")
            return

        token = bot_config[field]

        if not isinstance(token, str):
            self.errors.append(f"'{prefix}.{field}' must be a string, got {type(token).__name__}")
            return

        if not token:
            self.errors.append(f"'{prefix}.{field}' cannot be empty")
            return

        if not self.DISCORD_TOKEN_PATTERN.match(token):
            self.errors.append(
                f"'{prefix}.{field}' has invalid format. "
                "Expected format: XXX.XXX.XXX (three base64 segments separated by dots)"
            )

    def _validate_agent_id(self, prefix: str, bot_config: Dict) -> None:
        """Validate the agent_id field."""
        field = "agent_id"

        if field not in bot_config:
            self.errors.append(f"'{prefix}' missing required field '{field}'")
            return

        agent_id = bot_config[field]

        if not isinstance(agent_id, str):
            self.errors.append(f"'{prefix}.{field}' must be a string, got {type(agent_id).__name__}")
            return

        if not agent_id:
            self.errors.append(f"'{prefix}.{field}' cannot be empty")
            return

        if not self.AGENT_ID_PATTERN.match(agent_id):
            self.errors.append(
                f"'{prefix}.{field}' has invalid format. "
                "Expected format: agent-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )

    def _validate_enable_attachments(self, prefix: str, bot_config: Dict) -> None:
        """Validate the optional enable_attachments field."""
        field = "enable_attachments"

        if field not in bot_config:
            return  # Optional field

        value = bot_config[field]

        if not isinstance(value, bool):
            self.errors.append(
                f"'{prefix}.{field}' must be a boolean (true/false), got {type(value).__name__}"
            )


def load_config(validate: bool = True) -> Dict[str, Any]:
    """
    Load configuration from AWS Secrets Manager or local file.

    Args:
        validate: Whether to validate the config (default: True)

    Returns:
        The configuration dictionary

    Raises:
        ConfigValidationError: If validation is enabled and config is invalid
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file contains invalid JSON
    """
    secret_name = os.environ.get("AWS_SECRET_NAME")

    if secret_name:
        import boto3

        client = boto3.client(
            "secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1")
        )
        try:
            response = client.get_secret_value(SecretId=secret_name)
            config = json.loads(response["SecretString"])
        except json.JSONDecodeError as e:
            raise ConfigValidationError([f"AWS secret contains invalid JSON: {e}"])
        except Exception as e:
            raise ConfigValidationError([f"Failed to load AWS secret '{secret_name}': {e}"])
    else:
        config_path = os.environ.get("CONFIG_FILE", "bots.json")

        if not os.path.exists(config_path):
            raise FileNotFoundError(
                f"Config file not found: {config_path}\n"
                "Create a bots.json file or set CONFIG_FILE environment variable."
            )

        try:
            with open(config_path) as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigValidationError([f"Config file contains invalid JSON: {e}"])

    if validate:
        validator = ConfigValidator(config)
        validator.validate()

    return config


def get_bot_config(bot_name: str, config: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Get configuration for a specific bot.

    Args:
        bot_name: Name of the bot
        config: Optional pre-loaded config (loads if not provided)

    Returns:
        The bot's configuration dictionary

    Raises:
        ConfigValidationError: If bot doesn't exist in config
    """
    if config is None:
        config = load_config()

    if bot_name not in config.get("bots", {}):
        available = ", ".join(config.get("bots", {}).keys()) or "(none)"
        raise ConfigValidationError([
            f"Bot '{bot_name}' not found in configuration.",
            f"Available bots: {available}"
        ])

    return config["bots"][bot_name]


if __name__ == "__main__":
    # CLI tool for validating config files
    import sys

    try:
        config = load_config()
        print("✓ Configuration is valid")
        print(f"  Letta URL: {config.get('letta_url', '(default)')}")
        print(f"  Bots configured: {', '.join(config['bots'].keys())}")
        sys.exit(0)
    except ConfigValidationError as e:
        print(f"✗ {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"✗ {e}")
        sys.exit(1)
