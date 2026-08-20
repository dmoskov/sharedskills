#!/usr/bin/env python3
"""
Asana Configuration Loader

Loads and validates user-provided Asana configuration from YAML files.
Separates shareable code from workspace-specific config: all GIDs (workspace,
projects, custom fields, enum options) live in your YAML file, never in code.

See asana_config.example.yaml in this directory for a full annotated example,
or run `python3 asana_config_loader.py template` to print a starter config.

Environment Variables:
    ASANA_CONFIG_PATH: Path to YAML config file
        (default: ~/.config/ai-dev-tools/asana_config.yaml)

Example config structure:
    custom_fields:
      project: "120000000000001"
      priority: "120000000000002"
      task_type: "120000000000003"
      validation_status: "120000000000004"
      execution_status: "120000000000005"
      # ... more field GIDs

    enum_options:
      project:
        my-backend: "120000000000010"
        my-frontend: "120000000000011"
      priority:
        P0: "120000000000020"
        P1: "120000000000021"
        P2: "120000000000022"
        P3: "120000000000023"
      task_type:
        "🔒 Security": "120000000000030"
        "🏗️ Architecture": "120000000000031"
        # ... more task types
      validation_status:
        "✅ Approved": "120000000000040"
        "📋  Proposed / Needs Review": "120000000000041"
        # ... more validation statuses
      execution_status:
        "Pending": "120000000000050"
        "In Progress": "120000000000051"
        "Completed": "120000000000052"
        "Failed": "120000000000053"
      # ... more enum mappings

    projects:
      main_task_queue_gid: "120000000000060"
      default_workspace_gid: "120000000000061"
      vsm_project_gids:
        my-backend: "120000000000070"
        my-frontend: "120000000000071"
        # ... more per-project boards (optional)

    mappings:
      priority:
        Critical: P0
        High: P1
        Medium: P2
        Low: P3
      task_type:
        security: "🔒 Security"
        architecture: "🏗️ Architecture"
        # ... more mappings
      effort:
        S: "S - Small (< 4h)"
        M: "M - Medium (1-2d)"
        L: "L - Large (3-5d)"
        XL: "XL - Extra Large (1w+)"
"""

import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    import yaml
except ImportError:
    yaml = None

# Configure logging
logger = logging.getLogger(__name__)

# Default config path
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "ai-dev-tools" / "asana_config.yaml"

# Older installs kept the config here; still honored if the default is absent
LEGACY_CONFIG_PATHS = [
    Path.home() / ".config" / "claude-code-scaffold" / "asana_config.yaml",
]


class AsanaConfigError(Exception):
    """Raised when configuration is invalid or missing."""

    pass


class AsanaConfig:
    """
    Validated Asana configuration loaded from YAML.

    Provides validated access to custom fields, enum options, projects, and mappings.
    Compatible with asana_custom_fields_config.py interface.
    """

    def __init__(self, config_data: Dict[str, Any], config_path: Optional[Path] = None):
        """
        Initialize with validated config data.

        Args:
            config_data: Validated YAML config dictionary
            config_path: Optional path to config file (for error messages)
        """
        self._data = config_data
        self.config_path = config_path

        # Extract sections with defaults
        self.CUSTOM_FIELDS = config_data.get("custom_fields", {})
        self.ENUM_OPTIONS = config_data.get("enum_options", {})

        # Handle multiple schema versions:
        # 1. New nested structure: workspace.gid, workspace.default_project_gid
        # 2. Old nested structure: projects.main_task_queue_gid, projects.default_workspace_gid
        # 3. Flat structure: main_task_queue_gid, default_workspace_gid

        workspace = config_data.get("workspace", {})
        projects_section = config_data.get("projects", {})
        vsm_projects = config_data.get("vsm_projects", {})

        # Workspace GID resolution (priority order)
        if isinstance(workspace, dict) and workspace.get("gid"):
            # New structure: workspace.gid
            self.DEFAULT_WORKSPACE_GID = workspace.get("gid", "")
        elif isinstance(projects_section, dict) and projects_section.get(
            "default_workspace_gid"
        ):
            # Old nested: projects.default_workspace_gid
            self.DEFAULT_WORKSPACE_GID = projects_section.get(
                "default_workspace_gid", ""
            )
        else:
            # Flat structure: default_workspace_gid
            self.DEFAULT_WORKSPACE_GID = config_data.get("default_workspace_gid", "")

        # Main task queue GID resolution (priority order)
        if isinstance(workspace, dict) and workspace.get("default_project_gid"):
            # New structure: workspace.default_project_gid
            self.MAIN_TASK_QUEUE_GID = workspace.get("default_project_gid", "")
        elif isinstance(projects_section, dict) and projects_section.get(
            "main_task_queue_gid"
        ):
            # Old nested: projects.main_task_queue_gid
            self.MAIN_TASK_QUEUE_GID = projects_section.get("main_task_queue_gid", "")
        else:
            # Flat structure: main_task_queue_gid
            self.MAIN_TASK_QUEUE_GID = config_data.get("main_task_queue_gid", "")

        # VSM project GIDs (priority order)
        if vsm_projects:
            # New structure: vsm_projects
            self.VSM_PROJECT_GIDS = vsm_projects
        elif isinstance(projects_section, dict) and projects_section.get(
            "vsm_project_gids"
        ):
            # Old nested: projects.vsm_project_gids
            self.VSM_PROJECT_GIDS = projects_section.get("vsm_project_gids", {})
        else:
            # Flat structure: vsm_project_gids
            self.VSM_PROJECT_GIDS = config_data.get("vsm_project_gids", {})

        # Project mapping - support multiple locations
        # Priority: top-level projects > project_mapping > enum_options.project
        if isinstance(projects_section, dict) and not isinstance(
            projects_section.get("main_task_queue_gid"), str
        ):
            # New structure: projects section contains project name -> enum GID mappings
            # (not workspace/queue config which are strings)
            self.PROJECT_MAPPING = {
                k: v
                for k, v in projects_section.items()
                if not k.startswith("main_")
                and not k.startswith("default_")
                and not k == "vsm_project_gids"
            }
        else:
            self.PROJECT_MAPPING = config_data.get("project_mapping", {})

        # Fallback to enum_options.project if no explicit mapping
        if not self.PROJECT_MAPPING and "enum_options" in config_data:
            self.PROJECT_MAPPING = config_data["enum_options"].get("project", {})

        # Mappings section
        self._mappings = config_data.get("mappings", {})

    def get_custom_field_gid(self, field_name: str) -> Optional[str]:
        """
        Get custom field GID by field name.

        Args:
            field_name: Field name (e.g., "priority", "task_type")

        Returns:
            Custom field GID or None if not found
        """
        return self.CUSTOM_FIELDS.get(field_name)

    def get_enum_option_gid(self, field_name: str, option_name: str) -> Optional[str]:
        """
        Get enum option GID for a custom field.

        Args:
            field_name: Field name (e.g., "priority", "task_type")
            option_name: Option name (e.g., "P0", "security")

        Returns:
            Enum option GID or None if not found
        """
        field_options = self.ENUM_OPTIONS.get(field_name, {})
        return field_options.get(option_name)

    def get_vsm_project_gid(self, project_name: str) -> Optional[str]:
        """
        Get the VSM project GID for a given project name.

        Returns None if no VSM project exists for this project.
        Case-insensitive lookup.

        Args:
            project_name: Name of the project

        Returns:
            VSM project GID or None
        """
        # Try exact match first
        if project_name in self.VSM_PROJECT_GIDS:
            return self.VSM_PROJECT_GIDS[project_name]

        # Try lowercase
        lower_name = project_name.lower()
        for key, gid in self.VSM_PROJECT_GIDS.items():
            if key.lower() == lower_name:
                return gid

        return None

    def map_value(self, mapping_type: str, value: str) -> Optional[str]:
        """
        Map a value using configured mappings.

        Args:
            mapping_type: Mapping type (e.g., "priority", "task_type", "effort")
            value: Value to map (e.g., "Critical", "security", "S")

        Returns:
            Mapped value or None if not found
        """
        mapping = self._mappings.get(mapping_type, {})
        return mapping.get(value) or mapping.get(value.lower())

    def get_mapping_keys(self, mapping_type: str) -> List[str]:
        """
        Get all valid keys for a mapping type.

        Args:
            mapping_type: Mapping type (e.g., "priority", "task_type")

        Returns:
            List of valid keys
        """
        mapping = self._mappings.get(mapping_type, {})
        return list(mapping.keys())

    def validate(self) -> None:
        """
        Validate configuration structure and required fields.

        Raises:
            AsanaConfigError: If configuration is invalid with detailed error messages
        """
        errors = []

        # Check required top-level sections
        required_sections = ["custom_fields", "enum_options"]
        for section in required_sections:
            if section not in self._data:
                errors.append(
                    f"Missing required section: '{section}'\n"
                    f"  Add this section to your config file with the appropriate GIDs."
                )

        # Check required custom fields (minimum set for core functionality)
        if self.CUSTOM_FIELDS:
            required_fields = [
                "project",
                "priority",
                "task_type",
                "validation_status",
                "execution_status",
            ]
            missing_fields = [f for f in required_fields if f not in self.CUSTOM_FIELDS]
            if missing_fields:
                errors.append(
                    f"Missing required custom fields: {', '.join(missing_fields)}\n"
                    f"  These fields are required for core task management functionality.\n"
                    f"  Add them to the 'custom_fields' section with your Asana field GIDs."
                )

        # Check required enum options
        if self.ENUM_OPTIONS:
            required_enums = [
                "priority",
                "task_type",
                "validation_status",
                "execution_status",
            ]
            for enum in required_enums:
                if enum not in self.ENUM_OPTIONS:
                    errors.append(
                        f"Missing required enum options: '{enum}'\n"
                        f"  Add this to the 'enum_options' section with option names mapped to GIDs."
                    )
                elif not isinstance(self.ENUM_OPTIONS[enum], dict):
                    errors.append(
                        f"enum_options.{enum} must be a dictionary of option_name: gid"
                    )
                elif not self.ENUM_OPTIONS[enum]:
                    errors.append(
                        f"enum_options.{enum} is empty - add at least one option"
                    )

        # Check project configuration
        if not self.MAIN_TASK_QUEUE_GID:
            errors.append(
                "Missing required field: main_task_queue_gid / workspace.default_project_gid\n"
                "  This is the Asana project GID where tasks will be created.\n"
                "  Add it to the 'workspace' section (recommended) or as a top-level field."
            )

        if not self.DEFAULT_WORKSPACE_GID:
            errors.append(
                "Missing required field: default_workspace_gid / workspace.gid\n"
                "  This is your Asana workspace GID.\n"
                "  Add it to the 'workspace' section (recommended) or as a top-level field."
            )

        # Validate GID format (should be numeric strings)
        def validate_gid(gid: str, path: str) -> None:
            if not isinstance(gid, str):
                errors.append(
                    f"{path}: GID must be a string, got {type(gid).__name__}\n"
                    f'  Wrap the value in quotes: "{gid}"'
                )
            elif not gid.strip():
                errors.append(f"{path}: GID cannot be empty")
            elif not gid.isdigit():
                errors.append(
                    f"{path}: GID should be numeric (got '{gid}')\n"
                    f"  Asana GIDs are numeric strings. Check if this is the correct GID."
                )

        # Validate custom field GIDs
        for field_name, gid in self.CUSTOM_FIELDS.items():
            validate_gid(gid, f"custom_fields.{field_name}")

        # Validate enum option GIDs
        for field_name, options in self.ENUM_OPTIONS.items():
            if isinstance(options, dict):
                for option_name, gid in options.items():
                    validate_gid(gid, f"enum_options.{field_name}.{option_name}")

        # Validate project GIDs
        if self.MAIN_TASK_QUEUE_GID:
            validate_gid(self.MAIN_TASK_QUEUE_GID, "projects.main_task_queue_gid")
        if self.DEFAULT_WORKSPACE_GID:
            validate_gid(self.DEFAULT_WORKSPACE_GID, "projects.default_workspace_gid")

        # Validate VSM project GIDs
        for project_name, gid in self.VSM_PROJECT_GIDS.items():
            validate_gid(gid, f"projects.vsm_project_gids.{project_name}")

        if errors:
            error_msg = (
                "Configuration validation failed:\n\n"
                + "\n\n".join(f"❌ {err}" for err in errors)
                + f"\n\nConfiguration file: {self.config_path or 'unknown'}\n"
            )
            raise AsanaConfigError(error_msg)

    @property
    def CF(self) -> Dict[str, str]:
        """Alias for CUSTOM_FIELDS (backwards compatibility)."""
        return self.CUSTOM_FIELDS


def _get_config_path() -> Path:
    """
    Get configuration file path from environment or default.

    Resolution order:
        1. ASANA_CONFIG_PATH environment variable
        2. ~/.config/ai-dev-tools/asana_config.yaml
        3. Legacy locations (only if the default does not exist)

    Returns:
        Path to configuration file
    """
    env_path = os.environ.get("ASANA_CONFIG_PATH")
    if env_path:
        return Path(env_path).expanduser()
    if DEFAULT_CONFIG_PATH.exists():
        return DEFAULT_CONFIG_PATH
    for legacy_path in LEGACY_CONFIG_PATHS:
        if legacy_path.exists():
            logger.info(f"Using legacy config location: {legacy_path}")
            return legacy_path
    return DEFAULT_CONFIG_PATH


def _load_yaml_file(config_path: Path) -> Dict[str, Any]:
    """
    Load YAML configuration file.

    Args:
        config_path: Path to YAML file

    Returns:
        Parsed YAML data

    Raises:
        AsanaConfigError: If file cannot be read or parsed
    """
    if yaml is None:
        raise AsanaConfigError(
            "PyYAML not installed. Install with: pip install pyyaml\n"
            "  Or: pip install -r requirements.txt"
        )

    if not config_path.exists():
        raise AsanaConfigError(
            f"Configuration file not found: {config_path}\n\n"
            f"Please create {config_path} with your Asana configuration.\n"
            f"See the project documentation for the required structure:\n"
            f"  - custom_fields: Custom field GIDs from your Asana project\n"
            f"  - enum_options: Enum option GIDs for dropdown fields\n"
            f"  - projects: Project and workspace GIDs\n"
            f"  - mappings: Value mappings (optional)\n\n"
            f"You can set ASANA_CONFIG_PATH environment variable to use a different location.\n"
            f"Run 'python3 asana_config_loader.py template' to see an example config."
        )

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise AsanaConfigError(
            f"Failed to parse YAML configuration: {config_path}\n"
            f"Error: {e}\n\n"
            f"Please check your YAML syntax. Common issues:\n"
            f"  - Incorrect indentation (use spaces, not tabs)\n"
            f"  - Missing colons after keys\n"
            f"  - Unquoted strings containing special characters\n"
            f"  - Inconsistent indentation levels"
        ) from e
    except Exception as e:
        raise AsanaConfigError(
            f"Failed to read configuration file: {config_path}\nError: {e}"
        ) from e

    if not isinstance(data, dict):
        raise AsanaConfigError(
            f"Configuration file must contain a YAML dictionary, got {type(data).__name__}\n"
            f"File: {config_path}"
        )

    return data


def load_config(
    config_path: Optional[str] = None, validate: bool = True
) -> AsanaConfig:
    """
    Load and validate Asana configuration from YAML file.

    Args:
        config_path: Optional path to config file (defaults to ASANA_CONFIG_PATH env or ~/.config/...)
        validate: Whether to validate configuration (default: True)

    Returns:
        Validated AsanaConfig instance

    Raises:
        AsanaConfigError: If configuration is missing, invalid, or fails validation

    Example:
        >>> config = load_config()
        >>> priority_gid = config.get_custom_field_gid("priority")
        >>> p0_gid = config.get_enum_option_gid("priority", "P0")
    """
    if config_path is None:
        resolved_path = _get_config_path()
    else:
        resolved_path = Path(config_path).expanduser()

    logger.info(f"Loading Asana configuration from: {resolved_path}")

    data = _load_yaml_file(resolved_path)
    config = AsanaConfig(data, config_path=resolved_path)

    if validate:
        try:
            config.validate()
            logger.info("Configuration validation passed")
        except AsanaConfigError as e:
            # Add helpful context to validation errors
            raise AsanaConfigError(
                f"{e}\n\n"
                f"To fix this:\n"
                f"  1. Check the configuration file structure against the documentation\n"
                f"  2. Verify all GIDs are correct (should be numeric strings)\n"
                f"  3. Ensure all required sections and fields are present\n"
                f"  4. Run with --debug flag to see detailed validation output\n"
                f"  5. Run 'python3 asana_config_loader.py template' to see an example config"
            ) from e

    return config


def print_config_template() -> None:
    """
    Print a configuration file template to stdout.

    This template can be saved as asana_config.yaml and filled in with actual GIDs.
    """
    template = """# Asana Configuration Template
# Fill in with your actual Asana GIDs
#
# Save as: ~/.config/ai-dev-tools/asana_config.yaml
# (or set ASANA_CONFIG_PATH to a custom location)
#
# See asana_config.example.yaml for a fully annotated example.
#
# To find GIDs:
# 1. Workspace GID: Asana API or workspace settings
# 2. Project GID: From Asana URL (https://app.asana.com/0/PROJECT_GID/...)
# 3. Custom fields: Use Asana API or inspect project settings
# 4. Enum options: GET https://app.asana.com/api/1.0/custom_fields/{field_gid}

---
# Authentication (optional - can use environment variables instead)
auth:
  token:
    env_var: ASANA_ACCESS_TOKEN
    # aws_secret: your-org/asana/oauth-token  # optional
    # file_path: ~/.config/asana/tokens.json  # optional

# Workspace Configuration (required)
workspace:
  gid: "YOUR_WORKSPACE_GID"
  default_project_gid: "YOUR_DEFAULT_PROJECT_GID"

# Custom Field GIDs (required - at least the core fields)
custom_fields:
  # Core fields (required)
  project: "YOUR_PROJECT_FIELD_GID"
  priority: "YOUR_PRIORITY_FIELD_GID"
  task_type: "YOUR_TASK_TYPE_FIELD_GID"
  validation_status: "YOUR_VALIDATION_STATUS_FIELD_GID"
  execution_status: "YOUR_EXECUTION_STATUS_FIELD_GID"

  # Recommended fields
  effort_estimate: "YOUR_EFFORT_FIELD_GID"
  date_generated: "YOUR_DATE_GENERATED_FIELD_GID"
  last_seen: "YOUR_LAST_SEEN_FIELD_GID"

  # Optional fields
  source_agent: "YOUR_SOURCE_AGENT_FIELD_GID"
  orchestration_id: "YOUR_ORCHESTRATION_ID_FIELD_GID"
  execution_duration: "YOUR_EXECUTION_DURATION_FIELD_GID"
  execution_location: "YOUR_EXECUTION_LOCATION_FIELD_GID"

# Enum Option GIDs (required)
enum_options:
  priority:
    P0: "YOUR_P0_OPTION_GID"
    P1: "YOUR_P1_OPTION_GID"
    P2: "YOUR_P2_OPTION_GID"
    P3: "YOUR_P3_OPTION_GID"

  task_type:
    "🔒 Security": "YOUR_SECURITY_OPTION_GID"
    "🏗️ Architecture": "YOUR_ARCHITECTURE_OPTION_GID"
    "🐛 Bug": "YOUR_BUG_OPTION_GID"
    "✨ Feature": "YOUR_FEATURE_OPTION_GID"
    "📝 Documentation": "YOUR_DOCUMENTATION_OPTION_GID"

  validation_status:
    "✅ Approved": "YOUR_APPROVED_OPTION_GID"
    "🤖 Auto-Approved": "YOUR_AUTO_APPROVED_OPTION_GID"
    "📋  Proposed / Needs Review": "YOUR_PROPOSED_OPTION_GID"

  execution_status:
    Pending: "YOUR_PENDING_OPTION_GID"
    In Progress: "YOUR_IN_PROGRESS_OPTION_GID"
    Completed: "YOUR_COMPLETED_OPTION_GID"
    Failed: "YOUR_FAILED_OPTION_GID"

  effort_estimate:
    "S - Small (< 4h)": "YOUR_SMALL_OPTION_GID"
    "M - Medium (1-2d)": "YOUR_MEDIUM_OPTION_GID"
    "L - Large (3-5d)": "YOUR_LARGE_OPTION_GID"
    "XL - Extra Large (1w+)": "YOUR_XL_OPTION_GID"

# Project Mappings (required if using project custom field)
projects:
  my-project: "YOUR_MY_PROJECT_ENUM_GID"
  another-project: "YOUR_ANOTHER_PROJECT_ENUM_GID"

# VSM Projects (optional - for multi-homing to project-specific views)
vsm_projects:
  my-project: "YOUR_PROJECT_VSM_GID"
  another-project: "YOUR_OTHER_PROJECT_VSM_GID"

# Value Mappings (optional - convenient aliases)
mappings:
  priority:
    Critical: P0
    High: P1
    Medium: P2
    Low: P3

  task_type:
    security: "🔒 Security"
    architecture: "🏗️ Architecture"
    bug: "🐛 Bug"
    feature: "✨ Feature"

  effort:
    S: "S - Small (< 4h)"
    M: "M - Medium (1-2d)"
    L: "L - Large (3-5d)"
    XL: "XL - Extra Large (1w+)"
"""
    print(template)


def print_config_dump(config: AsanaConfig) -> None:
    """
    Print the loaded configuration as markdown tables.

    Intended for agents and skills (e.g. task-decomposition) that need the
    workspace's field and enum GIDs at runtime without hardcoding them.
    """
    print(f"# Asana Configuration ({config.config_path})\n")
    print(f"Workspace GID:       `{config.DEFAULT_WORKSPACE_GID}`")
    print(f"Main task queue GID: `{config.MAIN_TASK_QUEUE_GID}`\n")

    print("## Custom Field GIDs\n")
    print("| Field | GID |")
    print("|-------|-----|")
    for name, gid in config.CUSTOM_FIELDS.items():
        print(f"| {name} | {gid} |")

    for field_name, options in config.ENUM_OPTIONS.items():
        if not isinstance(options, dict):
            continue
        print(f"\n## Enum Options: {field_name}\n")
        print("| Option | GID |")
        print("|--------|-----|")
        for option_name, gid in options.items():
            print(f"| {option_name} | {gid} |")

    if config.VSM_PROJECT_GIDS:
        print("\n## Per-Project Board GIDs\n")
        print("| Project | GID |")
        print("|---------|-----|")
        for name, gid in config.VSM_PROJECT_GIDS.items():
            print(f"| {name} | {gid} |")

    if config._mappings:
        print("\n## Friendly Name Mappings\n")
        for mapping_type, mapping in config._mappings.items():
            if not isinstance(mapping, dict):
                continue
            print(f"### {mapping_type}\n")
            print("| Alias | Maps To |")
            print("|-------|---------|")
            for alias, target in mapping.items():
                print(f"| {alias} | {target} |")
            print()


def main():
    """CLI for testing and generating configuration."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Asana Configuration Loader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s validate                        # Validate default config
  %(prog)s validate --config custom.yaml  # Validate custom config
  %(prog)s template                        # Print config template
  %(prog)s info                            # Show loaded config info
  %(prog)s dump                            # Dump full config as markdown tables
        """,
    )

    parser.add_argument(
        "command",
        choices=["validate", "template", "info", "dump"],
        help="Command to execute",
    )
    parser.add_argument("--config", type=Path, help="Path to config file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        if args.command == "template":
            print_config_template()

        elif args.command == "validate":
            config = load_config(
                config_path=str(args.config) if args.config else None, validate=True
            )
            print("✓ Configuration is valid")
            print(f"  Main task queue: {config.MAIN_TASK_QUEUE_GID}")
            print(f"  Workspace: {config.DEFAULT_WORKSPACE_GID}")
            if config.VSM_PROJECT_GIDS:
                print(f"  VSM projects: {len(config.VSM_PROJECT_GIDS)}")

        elif args.command == "info":
            config = load_config(
                config_path=str(args.config) if args.config else None, validate=True
            )
            print(f"Configuration loaded from: {config.config_path}")
            print(f"\nCustom fields: {len(config.CUSTOM_FIELDS)}")
            print(f"Enum options: {len(config.ENUM_OPTIONS)}")
            print(f"VSM projects: {len(config.VSM_PROJECT_GIDS)}")
            print(f"Mappings: {len(config._mappings)}")

        elif args.command == "dump":
            config = load_config(
                config_path=str(args.config) if args.config else None, validate=True
            )
            print_config_dump(config)

    except AsanaConfigError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
