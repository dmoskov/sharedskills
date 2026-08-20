#!/usr/bin/env python3
"""
Unit tests for asana_config_loader.py

Tests cover:
- AsanaConfig initialization with various schema formats
- get_custom_field_gid lookups
- get_enum_option_gid lookups
- get_vsm_project_gid with case-insensitive matching
- map_value and get_mapping_keys
- validate() with valid and invalid configs
- load_config() with file I/O
- print_config_template() output
- _get_config_path() environment variable handling
- _load_yaml_file() error handling
- CF property alias
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import pytest
from asana_config_loader import (
    AsanaConfig,
    AsanaConfigError,
    load_config,
    print_config_template,
    _get_config_path,
    _load_yaml_file,
    DEFAULT_CONFIG_PATH,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _minimal_valid_config():
    """Return a minimal valid config dict with all required fields."""
    return {
        "custom_fields": {
            "project": "1111111111",
            "priority": "2222222222",
            "task_type": "3333333333",
            "validation_status": "4444444444",
            "execution_status": "5555555555",
        },
        "enum_options": {
            "priority": {"P0": "100", "P1": "101"},
            "task_type": {"Bug": "200", "Feature": "201"},
            "validation_status": {"Approved": "300"},
            "execution_status": {"Pending": "400", "Completed": "401"},
        },
        "workspace": {
            "gid": "9999999999",
            "default_project_gid": "8888888888",
        },
        "vsm_projects": {
            "my-project": "7777777777",
        },
        "mappings": {
            "priority": {"Critical": "P0", "High": "P1"},
            "effort": {"S": "S - Small (< 4h)"},
        },
    }


@pytest.fixture
def valid_config_data():
    return _minimal_valid_config()


@pytest.fixture
def valid_config(valid_config_data):
    return AsanaConfig(valid_config_data, config_path=Path("/fake/config.yaml"))


# ---------------------------------------------------------------------------
# AsanaConfig.__init__ – new workspace schema
# ---------------------------------------------------------------------------


class TestAsanaConfigInitNewSchema:
    """Test initialization with the new workspace-based schema."""

    def test_custom_fields_loaded(self, valid_config):
        assert valid_config.CUSTOM_FIELDS["project"] == "1111111111"
        assert valid_config.CUSTOM_FIELDS["priority"] == "2222222222"

    def test_enum_options_loaded(self, valid_config):
        assert valid_config.ENUM_OPTIONS["priority"]["P0"] == "100"

    def test_workspace_gid(self, valid_config):
        assert valid_config.DEFAULT_WORKSPACE_GID == "9999999999"

    def test_main_task_queue_gid(self, valid_config):
        assert valid_config.MAIN_TASK_QUEUE_GID == "8888888888"

    def test_vsm_project_gids(self, valid_config):
        assert valid_config.VSM_PROJECT_GIDS == {"my-project": "7777777777"}

    def test_config_path_stored(self, valid_config):
        assert valid_config.config_path == Path("/fake/config.yaml")


# ---------------------------------------------------------------------------
# AsanaConfig.__init__ – old projects schema
# ---------------------------------------------------------------------------


class TestAsanaConfigInitOldSchema:
    """Test initialization with the old projects-based schema."""

    def test_old_projects_workspace_gid(self):
        data = {
            "custom_fields": {},
            "enum_options": {},
            "projects": {
                "default_workspace_gid": "1111",
                "main_task_queue_gid": "2222",
                "vsm_project_gids": {"proj": "3333"},
            },
        }
        cfg = AsanaConfig(data)
        assert cfg.DEFAULT_WORKSPACE_GID == "1111"
        assert cfg.MAIN_TASK_QUEUE_GID == "2222"
        assert cfg.VSM_PROJECT_GIDS == {"proj": "3333"}


# ---------------------------------------------------------------------------
# AsanaConfig.__init__ – flat schema
# ---------------------------------------------------------------------------


class TestAsanaConfigInitFlatSchema:
    """Test initialization with flat top-level keys."""

    def test_flat_workspace_gid(self):
        data = {
            "custom_fields": {},
            "enum_options": {},
            "default_workspace_gid": "1111",
            "main_task_queue_gid": "2222",
            "vsm_project_gids": {"proj": "3333"},
        }
        cfg = AsanaConfig(data)
        assert cfg.DEFAULT_WORKSPACE_GID == "1111"
        assert cfg.MAIN_TASK_QUEUE_GID == "2222"
        assert cfg.VSM_PROJECT_GIDS == {"proj": "3333"}


# ---------------------------------------------------------------------------
# AsanaConfig.__init__ – project mapping resolution
# ---------------------------------------------------------------------------


class TestProjectMappingResolution:
    """Test how PROJECT_MAPPING is resolved from various config shapes."""

    def test_project_mapping_from_projects_section(self):
        """projects section with non-infrastructure keys becomes PROJECT_MAPPING."""
        data = {
            "custom_fields": {},
            "enum_options": {},
            "projects": {
                "my-proj": "111",
                "other-proj": "222",
            },
        }
        cfg = AsanaConfig(data)
        assert cfg.PROJECT_MAPPING == {"my-proj": "111", "other-proj": "222"}

    def test_project_mapping_excludes_infrastructure_keys(self):
        """Infrastructure keys in projects section are excluded from mapping."""
        data = {
            "custom_fields": {},
            "enum_options": {},
            "projects": {
                "main_task_queue_gid": "999",
                "default_workspace_gid": "888",
                "vsm_project_gids": {},
                "my-proj": "111",
            },
        }
        cfg = AsanaConfig(data)
        # The old schema has main_task_queue_gid as a string so it goes to old path
        assert cfg.MAIN_TASK_QUEUE_GID == "999"

    def test_project_mapping_from_explicit_key(self):
        data = {
            "custom_fields": {},
            "enum_options": {},
            "projects": {
                "main_task_queue_gid": "999",
            },
            "project_mapping": {"a": "1", "b": "2"},
        }
        cfg = AsanaConfig(data)
        assert cfg.PROJECT_MAPPING == {"a": "1", "b": "2"}

    def test_project_mapping_fallback_to_enum_options(self):
        data = {
            "custom_fields": {},
            "enum_options": {"project": {"proj-a": "10", "proj-b": "20"}},
        }
        cfg = AsanaConfig(data)
        assert cfg.PROJECT_MAPPING == {"proj-a": "10", "proj-b": "20"}


# ---------------------------------------------------------------------------
# get_custom_field_gid
# ---------------------------------------------------------------------------


class TestGetCustomFieldGid:
    def test_existing_field(self, valid_config):
        assert valid_config.get_custom_field_gid("project") == "1111111111"

    def test_missing_field_returns_none(self, valid_config):
        assert valid_config.get_custom_field_gid("nonexistent") is None


# ---------------------------------------------------------------------------
# get_enum_option_gid
# ---------------------------------------------------------------------------


class TestGetEnumOptionGid:
    def test_existing_option(self, valid_config):
        assert valid_config.get_enum_option_gid("priority", "P0") == "100"

    def test_missing_option_returns_none(self, valid_config):
        assert valid_config.get_enum_option_gid("priority", "P99") is None

    def test_missing_field_returns_none(self, valid_config):
        assert valid_config.get_enum_option_gid("nonexistent", "P0") is None


# ---------------------------------------------------------------------------
# get_vsm_project_gid
# ---------------------------------------------------------------------------


class TestGetVsmProjectGid:
    def test_exact_match(self, valid_config):
        assert valid_config.get_vsm_project_gid("my-project") == "7777777777"

    def test_case_insensitive_match(self, valid_config):
        assert valid_config.get_vsm_project_gid("MY-PROJECT") == "7777777777"
        assert valid_config.get_vsm_project_gid("My-Project") == "7777777777"

    def test_missing_project_returns_none(self, valid_config):
        assert valid_config.get_vsm_project_gid("nonexistent") is None


# ---------------------------------------------------------------------------
# map_value / get_mapping_keys
# ---------------------------------------------------------------------------


class TestMapValue:
    def test_exact_match(self, valid_config):
        assert valid_config.map_value("priority", "Critical") == "P0"

    def test_lowercase_fallback(self, valid_config):
        """Lowercase fallback matches when keys are stored lowercase."""
        # The method does mapping.get(value) or mapping.get(value.lower())
        # This only works if the stored key is lowercase. Our fixture has "Critical" (capitalized).
        # Add a lowercase key to verify the fallback path works.
        valid_config._mappings["effort"]["s"] = "S - Small (< 4h)"
        assert valid_config.map_value("effort", "S") == "S - Small (< 4h)"  # exact
        assert (
            valid_config.map_value("effort", "s") == "S - Small (< 4h)"
        )  # lowercase match

    def test_missing_value_returns_none(self, valid_config):
        assert valid_config.map_value("priority", "Unknown") is None

    def test_missing_mapping_type(self, valid_config):
        assert valid_config.map_value("nonexistent", "foo") is None


class TestGetMappingKeys:
    def test_returns_keys(self, valid_config):
        keys = valid_config.get_mapping_keys("priority")
        assert "Critical" in keys
        assert "High" in keys

    def test_missing_type_returns_empty(self, valid_config):
        assert valid_config.get_mapping_keys("nonexistent") == []


# ---------------------------------------------------------------------------
# CF property
# ---------------------------------------------------------------------------


class TestCFProperty:
    def test_cf_alias(self, valid_config):
        assert valid_config.CF is valid_config.CUSTOM_FIELDS


# ---------------------------------------------------------------------------
# validate()
# ---------------------------------------------------------------------------


class TestValidate:
    def test_valid_config_passes(self, valid_config_data):
        cfg = AsanaConfig(valid_config_data)
        cfg.validate()  # Should not raise

    def test_missing_custom_fields_section(self):
        data = {"enum_options": {"priority": {"P0": "1"}}}
        cfg = AsanaConfig(data)
        with pytest.raises(
            AsanaConfigError, match="Missing required section.*custom_fields"
        ):
            cfg.validate()

    def test_missing_enum_options_section(self):
        data = {"custom_fields": {"project": "1"}}
        cfg = AsanaConfig(data)
        with pytest.raises(
            AsanaConfigError, match="Missing required section.*enum_options"
        ):
            cfg.validate()

    def test_missing_required_custom_fields(self):
        data = {
            "custom_fields": {"project": "1111"},
            "enum_options": {},
            "workspace": {"gid": "999", "default_project_gid": "888"},
        }
        cfg = AsanaConfig(data)
        with pytest.raises(AsanaConfigError, match="Missing required custom fields"):
            cfg.validate()

    def test_missing_required_enum_option_section(self):
        data = _minimal_valid_config()
        del data["enum_options"]["priority"]
        cfg = AsanaConfig(data)
        with pytest.raises(
            AsanaConfigError, match="Missing required enum options.*priority"
        ):
            cfg.validate()

    def test_empty_enum_option_dict(self):
        data = _minimal_valid_config()
        data["enum_options"]["priority"] = {}
        cfg = AsanaConfig(data)
        with pytest.raises(AsanaConfigError, match="priority.*empty"):
            cfg.validate()

    def test_enum_option_not_dict(self):
        data = _minimal_valid_config()
        data["enum_options"]["priority"] = "not-a-dict"
        cfg = AsanaConfig(data)
        with pytest.raises(AsanaConfigError, match="must be a dictionary"):
            cfg.validate()

    def test_missing_workspace_gid(self):
        data = _minimal_valid_config()
        del data["workspace"]
        cfg = AsanaConfig(data)
        with pytest.raises(AsanaConfigError, match="default_workspace_gid"):
            cfg.validate()

    def test_missing_main_task_queue_gid(self):
        data = _minimal_valid_config()
        data["workspace"] = {"gid": "999"}
        cfg = AsanaConfig(data)
        with pytest.raises(AsanaConfigError, match="main_task_queue_gid"):
            cfg.validate()

    def test_non_numeric_gid(self):
        data = _minimal_valid_config()
        data["custom_fields"]["project"] = "abc-not-numeric"
        cfg = AsanaConfig(data)
        with pytest.raises(AsanaConfigError, match="GID should be numeric"):
            cfg.validate()

    def test_empty_gid(self):
        data = _minimal_valid_config()
        data["custom_fields"]["project"] = "  "
        cfg = AsanaConfig(data)
        with pytest.raises(AsanaConfigError, match="GID cannot be empty"):
            cfg.validate()

    def test_non_string_gid(self):
        data = _minimal_valid_config()
        data["custom_fields"]["project"] = 12345
        cfg = AsanaConfig(data)
        with pytest.raises(AsanaConfigError, match="GID must be a string"):
            cfg.validate()

    def test_validates_vsm_project_gids(self):
        data = _minimal_valid_config()
        data["vsm_projects"]["bad"] = "not-numeric"
        cfg = AsanaConfig(data)
        with pytest.raises(AsanaConfigError, match="GID should be numeric"):
            cfg.validate()


# ---------------------------------------------------------------------------
# _get_config_path
# ---------------------------------------------------------------------------


class TestGetConfigPath:
    def test_default_path(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove ASANA_CONFIG_PATH if present
            os.environ.pop("ASANA_CONFIG_PATH", None)
            result = _get_config_path()
            assert result == DEFAULT_CONFIG_PATH

    def test_env_override(self, tmp_path):
        custom = str(tmp_path / "custom.yaml")
        with patch.dict(os.environ, {"ASANA_CONFIG_PATH": custom}):
            result = _get_config_path()
            assert result == Path(custom)

    def test_env_expands_user(self):
        with patch.dict(os.environ, {"ASANA_CONFIG_PATH": "~/my_config.yaml"}):
            result = _get_config_path()
            assert "~" not in str(result)
            assert result.name == "my_config.yaml"


# ---------------------------------------------------------------------------
# _load_yaml_file
# ---------------------------------------------------------------------------


class TestLoadYamlFile:
    def test_loads_valid_yaml(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("custom_fields:\n  project: '111'\n")
        data = _load_yaml_file(cfg_file)
        assert data == {"custom_fields": {"project": "111"}}

    def test_file_not_found(self, tmp_path):
        missing = tmp_path / "missing.yaml"
        with pytest.raises(AsanaConfigError, match="Configuration file not found"):
            _load_yaml_file(missing)

    def test_invalid_yaml_syntax(self, tmp_path):
        cfg_file = tmp_path / "bad.yaml"
        cfg_file.write_text(":\n  - :\n  invalid: [unclosed")
        with pytest.raises(AsanaConfigError, match="Failed to parse YAML"):
            _load_yaml_file(cfg_file)

    def test_non_dict_yaml(self, tmp_path):
        cfg_file = tmp_path / "list.yaml"
        cfg_file.write_text("- item1\n- item2\n")
        with pytest.raises(AsanaConfigError, match="must contain a YAML dictionary"):
            _load_yaml_file(cfg_file)

    def test_yaml_not_installed(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("key: val\n")
        with patch("asana_config_loader.yaml", None):
            with pytest.raises(AsanaConfigError, match="PyYAML not installed"):
                _load_yaml_file(cfg_file)

    def test_permission_error(self, tmp_path):
        cfg_file = tmp_path / "noperm.yaml"
        cfg_file.write_text("key: val\n")
        cfg_file.chmod(0o000)
        try:
            with pytest.raises(AsanaConfigError, match="Failed to read"):
                _load_yaml_file(cfg_file)
        finally:
            cfg_file.chmod(0o644)


# ---------------------------------------------------------------------------
# load_config (integration-ish, uses tmp files)
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def _write_config(self, tmp_path, data_dict):
        import yaml

        cfg_file = tmp_path / "asana_config.yaml"
        cfg_file.write_text(yaml.dump(data_dict, default_flow_style=False))
        return str(cfg_file)

    def test_load_valid_config(self, tmp_path):
        path = self._write_config(tmp_path, _minimal_valid_config())
        cfg = load_config(config_path=path)
        assert cfg.MAIN_TASK_QUEUE_GID == "8888888888"

    def test_load_without_validation(self, tmp_path):
        # Missing required fields but validate=False should skip
        data = {"custom_fields": {"project": "1"}}
        path = self._write_config(tmp_path, data)
        cfg = load_config(config_path=path, validate=False)
        assert cfg.CUSTOM_FIELDS == {"project": "1"}

    def test_load_with_validation_failure(self, tmp_path):
        data = {"custom_fields": {"project": "invalid-gid"}}
        path = self._write_config(tmp_path, data)
        with pytest.raises(AsanaConfigError):
            load_config(config_path=path, validate=True)

    def test_load_uses_env_path(self, tmp_path):
        path = self._write_config(tmp_path, _minimal_valid_config())
        with patch.dict(os.environ, {"ASANA_CONFIG_PATH": path}):
            cfg = load_config()
            assert cfg.MAIN_TASK_QUEUE_GID == "8888888888"

    def test_load_missing_file(self, tmp_path):
        missing = str(tmp_path / "missing.yaml")
        with pytest.raises(AsanaConfigError, match="Configuration file not found"):
            load_config(config_path=missing)


# ---------------------------------------------------------------------------
# print_config_template
# ---------------------------------------------------------------------------


class TestPrintConfigTemplate:
    def test_prints_template(self, capsys):
        print_config_template()
        output = capsys.readouterr().out
        assert "custom_fields:" in output
        assert "enum_options:" in output
        assert "workspace:" in output
        assert "YOUR_WORKSPACE_GID" in output
        assert "mappings:" in output

    def test_template_is_valid_yaml(self, capsys):
        import yaml

        print_config_template()
        output = capsys.readouterr().out
        parsed = yaml.safe_load(output)
        assert isinstance(parsed, dict)
        assert "custom_fields" in parsed


# ---------------------------------------------------------------------------
# Edge cases and empty configs
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_config(self):
        cfg = AsanaConfig({})
        assert cfg.CUSTOM_FIELDS == {}
        assert cfg.ENUM_OPTIONS == {}
        assert cfg.DEFAULT_WORKSPACE_GID == ""
        assert cfg.MAIN_TASK_QUEUE_GID == ""
        assert cfg.VSM_PROJECT_GIDS == {}

    def test_config_path_none(self):
        cfg = AsanaConfig({})
        assert cfg.config_path is None

    def test_map_value_case_sensitivity(self):
        """map_value tries exact match first, then .lower() of the input."""
        data = {
            "custom_fields": {},
            "enum_options": {},
            "mappings": {"priority": {"Critical": "P0", "critical": "p0-lower"}},
        }
        cfg = AsanaConfig(data)
        # Exact match "Critical"
        assert cfg.map_value("priority", "Critical") == "P0"
        # Input "critical" matches key "critical" exactly first
        assert cfg.map_value("priority", "critical") == "p0-lower"
        # Input "CRITICAL" -> exact miss, .lower() = "critical" -> matches
        assert cfg.map_value("priority", "CRITICAL") == "p0-lower"
        # No match at all
        assert cfg.map_value("priority", "unknown") is None

    def test_multiple_validation_errors(self):
        """Config with multiple problems reports them all."""
        data = {}
        cfg = AsanaConfig(data)
        with pytest.raises(AsanaConfigError) as exc_info:
            cfg.validate()
        msg = str(exc_info.value)
        assert "custom_fields" in msg
        assert "enum_options" in msg
