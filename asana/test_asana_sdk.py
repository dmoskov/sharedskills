#!/usr/bin/env python3
"""
Unit Tests for Asana SDK Package

Tests the decoupled asana_sdk package without making real API calls.
Uses mocking to simulate Asana API responses.
"""

import json
import sys
import unittest
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from asana_sdk import (
    # Errors
    AsanaClientError,
    AsanaAuthenticationError,
    AsanaRateLimitError,
    AsanaNotFoundError,
    AsanaValidationError,
    AsanaServerError,
    # Infrastructure
    get_config,
    AsanaSDKConfig,
    ASANA_SDK_AVAILABLE,
    raise_alert,
    # Token management
    TokenManager,
    # Custom fields
    CustomFieldCache,
    get_custom_field_cache,
    filter_tasks_by_custom_field,
    get_task_custom_field_value,
    # Tasks
    TaskTemplate,
)


class TestErrors(unittest.TestCase):
    """Test exception classes."""

    def test_base_exception(self):
        """Test AsanaClientError is base for all exceptions."""
        self.assertTrue(issubclass(AsanaAuthenticationError, AsanaClientError))
        self.assertTrue(issubclass(AsanaRateLimitError, AsanaClientError))
        self.assertTrue(issubclass(AsanaNotFoundError, AsanaClientError))
        self.assertTrue(issubclass(AsanaValidationError, AsanaClientError))
        self.assertTrue(issubclass(AsanaServerError, AsanaClientError))

    def test_rate_limit_error_retry_after(self):
        """Test AsanaRateLimitError stores retry_after."""
        error = AsanaRateLimitError("Rate limited", retry_after=60)
        self.assertEqual(error.retry_after, 60)
        self.assertIn("Rate limited", str(error))

    def test_rate_limit_error_no_retry_after(self):
        """Test AsanaRateLimitError without retry_after."""
        error = AsanaRateLimitError("Rate limited")
        self.assertIsNone(error.retry_after)


class TestConfig(unittest.TestCase):
    """Test SDK configuration."""

    def test_config_singleton(self):
        """Test config is singleton."""
        config1 = get_config()
        config2 = get_config()
        self.assertIs(config1, config2)

    def test_config_is_asana_sdk_config(self):
        """Test config is AsanaSDKConfig instance."""
        config = get_config()
        self.assertIsInstance(config, AsanaSDKConfig)

    def test_set_alert_callback(self):
        """Test setting alert callback."""
        config = get_config()
        callback = Mock()
        config.set_alert_callback(callback)
        self.assertEqual(config._alert_callback, callback)
        # Reset
        config._alert_callback = None

    def test_set_rate_limit_hooks(self):
        """Test setting rate limit hooks."""
        config = get_config()
        check_fn = Mock(return_value=(True, ""))
        record_fn = Mock()
        config.set_rate_limit_hooks(check_fn, record_fn)
        self.assertEqual(config._rate_limit_check, check_fn)
        self.assertEqual(config._rate_limit_record, record_fn)
        # Reset
        config._rate_limit_check = None
        config._rate_limit_record = None


class TestRaiseAlert(unittest.TestCase):
    """Test alert system."""

    def test_raise_alert_with_callback(self):
        """Test alert dispatches to callback."""
        config = get_config()
        callback = Mock()
        config.set_alert_callback(callback)

        raise_alert("critical", "test_category", "Test message", {"key": "value"})

        callback.assert_called_once_with(
            "critical", "test_category", "Test message", {"key": "value"}
        )
        # Reset
        config._alert_callback = None

    def test_raise_alert_without_callback(self):
        """Test alert logs when no callback set."""
        config = get_config()
        config._alert_callback = None

        # Should not raise, just log
        raise_alert("warning", "test", "Test message")


class TestCustomFieldCache(unittest.TestCase):
    """Test custom field caching."""

    def test_cache_set_and_get(self):
        """Test basic cache operations."""
        cache = CustomFieldCache()
        cache.set("project1", "Priority", "gid123")

        result = cache.get("project1", "Priority")
        self.assertEqual(result, "gid123")

    def test_cache_get_missing(self):
        """Test cache returns None for missing keys."""
        cache = CustomFieldCache()

        self.assertIsNone(cache.get("missing", "field"))
        self.assertIsNone(cache.get("project1", "missing"))

    def test_cache_clear_project(self):
        """Test clearing cache for specific project."""
        cache = CustomFieldCache()
        cache.set("project1", "field1", "gid1")
        cache.set("project2", "field2", "gid2")

        cache.clear("project1")

        self.assertIsNone(cache.get("project1", "field1"))
        self.assertEqual(cache.get("project2", "field2"), "gid2")

    def test_cache_clear_all(self):
        """Test clearing entire cache."""
        cache = CustomFieldCache()
        cache.set("project1", "field1", "gid1")
        cache.set("project2", "field2", "gid2")

        cache.clear()

        self.assertIsNone(cache.get("project1", "field1"))
        self.assertIsNone(cache.get("project2", "field2"))

    def test_global_cache(self):
        """Test global cache instance."""
        cache = get_custom_field_cache()
        self.assertIsInstance(cache, CustomFieldCache)


class TestFilterTasksByCustomField(unittest.TestCase):
    """Test task filtering by custom field."""

    def test_filter_by_display_value(self):
        """Test filtering by display_value."""
        tasks = [
            {
                "gid": "1",
                "name": "Task 1",
                "custom_fields": [
                    {"name": "Project", "display_value": "my-project"}
                ],
            },
            {
                "gid": "2",
                "name": "Task 2",
                "custom_fields": [
                    {"name": "Project", "display_value": "other-project"}
                ],
            },
        ]

        result = filter_tasks_by_custom_field(tasks, "Project", "my-project")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["gid"], "1")

    def test_filter_by_text_value(self):
        """Test filtering by text_value."""
        tasks = [
            {
                "gid": "1",
                "name": "Task 1",
                "custom_fields": [
                    {"name": "Notes", "text_value": "important"}
                ],
            },
        ]

        result = filter_tasks_by_custom_field(tasks, "Notes", "important")

        self.assertEqual(len(result), 1)

    def test_filter_no_matches(self):
        """Test filtering returns empty when no matches."""
        tasks = [
            {
                "gid": "1",
                "custom_fields": [{"name": "Project", "display_value": "other"}],
            }
        ]

        result = filter_tasks_by_custom_field(tasks, "Project", "my-project")

        self.assertEqual(len(result), 0)

    def test_filter_invalid_tasks(self):
        """Test filter handles invalid task structures."""
        tasks = [
            None,
            "not a dict",
            {"gid": "1"},  # missing custom_fields
            {"gid": "2", "custom_fields": "not a list"},
        ]

        result = filter_tasks_by_custom_field(tasks, "Project", "value")
        self.assertEqual(len(result), 0)

    def test_filter_validates_inputs(self):
        """Test filter validates inputs."""
        with self.assertRaises(ValueError):
            filter_tasks_by_custom_field("not a list", "field", "value")

        with self.assertRaises(ValueError):
            filter_tasks_by_custom_field([], "", "value")

        with self.assertRaises(ValueError):
            filter_tasks_by_custom_field([], "field", "")


class TestGetTaskCustomFieldValue(unittest.TestCase):
    """Test getting custom field values from tasks."""

    def test_get_display_value(self):
        """Test getting display_value."""
        task = {
            "custom_fields": [
                {"name": "Priority", "display_value": "P0"}
            ]
        }

        result = get_task_custom_field_value(task, "Priority")
        self.assertEqual(result, "P0")

    def test_get_text_value(self):
        """Test getting text_value when no display_value."""
        task = {
            "custom_fields": [
                {"name": "Notes", "text_value": "Some notes"}
            ]
        }

        result = get_task_custom_field_value(task, "Notes")
        self.assertEqual(result, "Some notes")

    def test_get_missing_field(self):
        """Test returns None for missing field."""
        task = {"custom_fields": []}

        result = get_task_custom_field_value(task, "Missing")
        self.assertIsNone(result)

    def test_invalid_task(self):
        """Test returns None for invalid task."""
        self.assertIsNone(get_task_custom_field_value(None, "field"))
        self.assertIsNone(get_task_custom_field_value("string", "field"))
        self.assertIsNone(get_task_custom_field_value({}, "field"))


class TestTaskTemplate(unittest.TestCase):
    """Test TaskTemplate fluent API."""

    def test_basic_template(self):
        """Test basic template creation."""
        template = TaskTemplate()
        template.with_name("Test Task")
        template._data["project_gid"] = "123"  # Skip validation

        data = template.to_dict()

        self.assertEqual(data["name"], "Test Task")
        self.assertEqual(data["project_gid"], "123")

    def test_template_chaining(self):
        """Test method chaining."""
        template = (
            TaskTemplate()
            .with_name("Task")
            .with_notes("Description")
            .with_assignee("user@example.com")
            .with_due_date("2025-01-20")
        )
        template._data["project_gid"] = "123"

        data = template.to_dict()

        self.assertEqual(data["name"], "Task")
        self.assertEqual(data["notes"], "Description")
        self.assertEqual(data["assignee"], "user@example.com")
        self.assertEqual(data["due_on"], "2025-01-20")

    def test_template_validates_name(self):
        """Test template requires name."""
        template = TaskTemplate()
        template._data["project_gid"] = "123"

        with self.assertRaises(ValueError) as ctx:
            template.to_dict()
        self.assertIn("name", str(ctx.exception).lower())

    def test_template_validates_project(self):
        """Test template requires project."""
        template = TaskTemplate().with_name("Task")

        with self.assertRaises(ValueError) as ctx:
            template.to_dict()
        self.assertIn("project", str(ctx.exception).lower())

    def test_with_custom_field_raw(self):
        """Test setting raw custom field."""
        template = TaskTemplate().with_name("Task")
        template._data["project_gid"] = "123"

        template.with_custom_field_raw("field_gid", "value")
        data = template.to_dict()

        self.assertEqual(data["custom_fields"]["field_gid"], "value")

    def test_invalid_name(self):
        """Test validation of invalid name."""
        template = TaskTemplate()

        with self.assertRaises(ValueError):
            template.with_name("")

        with self.assertRaises(ValueError):
            template.with_name(None)


class TestTokenManager(unittest.TestCase):
    """Test token manager."""

    def test_token_manager_init(self):
        """Test TokenManager initialization."""
        manager = TokenManager(
            token_file=Path("/tmp/test_tokens.json"),
            refresh_help_command="test command"
        )
        self.assertEqual(manager.token_file, Path("/tmp/test_tokens.json"))
        self.assertEqual(manager.refresh_help_command, "test command")

    @patch("asana_sdk.token_manager.Path.exists")
    @patch("builtins.open", mock_open(read_data='{"access_token": "test_token", "expires_at": 9999999999}'))
    def test_load_token_from_file(self, mock_exists):
        """Test loading token from file."""
        mock_exists.return_value = True
        manager = TokenManager(token_file=Path("/tmp/test.json"))

        # Load tokens via the public method
        tokens = manager.load_tokens()

        self.assertEqual(tokens.get("access_token"), "test_token")

    @patch.dict("os.environ", {"ASANA_ACCESS_TOKEN": "env_token"})
    def test_get_token_from_env(self):
        """Test getting token from environment."""
        manager = TokenManager(token_file=Path("/nonexistent/path.json"))
        manager._token_data = None

        # Should fall back to env var
        token = manager.get_valid_token()
        self.assertEqual(token, "env_token")


class TestSDKAvailability(unittest.TestCase):
    """Test SDK availability flag."""

    def test_sdk_available(self):
        """Test ASANA_SDK_AVAILABLE is set correctly."""
        # Should be True since we have asana installed
        self.assertIsInstance(ASANA_SDK_AVAILABLE, bool)


# =============================================================================
# Integration-style tests (with mocks)
# =============================================================================


class TestTaskOperationsWithMocks(unittest.TestCase):
    """Test task operations with mocked Asana client."""

    @patch("asana_sdk.tasks.get_client")
    @patch("asana_sdk.tasks.ASANA_SDK_AVAILABLE", True)
    def test_get_asana_tasks(self, mock_get_client):
        """Test getting tasks from project."""
        from asana_sdk.tasks import get_asana_tasks

        # Mock the client and API
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_tasks_api = MagicMock()
        mock_tasks_api.get_tasks_for_project.return_value = [
            {"gid": "1", "name": "Task 1"},
            {"gid": "2", "name": "Task 2"},
        ]

        with patch("asana_sdk.tasks.asana") as mock_asana:
            mock_asana.TasksApi.return_value = mock_tasks_api

            result = get_asana_tasks("project123", limit=10)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "Task 1")

    @patch("asana_sdk.tasks.get_client")
    @patch("asana_sdk.tasks.ASANA_SDK_AVAILABLE", True)
    def test_create_asana_task(self, mock_get_client):
        """Test creating a task."""
        from asana_sdk.tasks import create_asana_task

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_tasks_api = MagicMock()
        mock_tasks_api.create_task.return_value = {"gid": "new_task_123"}

        with patch("asana_sdk.tasks.asana") as mock_asana:
            mock_asana.TasksApi.return_value = mock_tasks_api

            result = create_asana_task(
                name="New Task",
                project_gid="project123",
                notes="Task notes"
            )

        self.assertEqual(result, "new_task_123")
        mock_tasks_api.create_task.assert_called_once()

    def test_create_task_validates_inputs(self):
        """Test create_asana_task validates inputs."""
        from asana_sdk.tasks import create_asana_task

        with self.assertRaises(ValueError):
            create_asana_task(name="", project_gid="123")

        with self.assertRaises(ValueError):
            create_asana_task(name="Task")  # No project or parent

    @patch("asana_sdk.tasks.get_client")
    @patch("asana_sdk.tasks.ASANA_SDK_AVAILABLE", True)
    def test_update_asana_task(self, mock_get_client):
        """Test updating a task."""
        from asana_sdk.tasks import update_asana_task

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_tasks_api = MagicMock()

        with patch("asana_sdk.tasks.asana") as mock_asana:
            mock_asana.TasksApi.return_value = mock_tasks_api

            result = update_asana_task(
                task_gid="task123",
                name="Updated Name",
                notes="New notes"
            )

        self.assertTrue(result)
        mock_tasks_api.update_task.assert_called_once()

    @patch("asana_sdk.tasks.get_client")
    @patch("asana_sdk.tasks.ASANA_SDK_AVAILABLE", True)
    def test_delete_asana_task(self, mock_get_client):
        """Test deleting a task."""
        from asana_sdk.tasks import delete_asana_task

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_tasks_api = MagicMock()

        with patch("asana_sdk.tasks.asana") as mock_asana:
            mock_asana.TasksApi.return_value = mock_tasks_api

            result = delete_asana_task("task123")

        self.assertTrue(result)
        mock_tasks_api.delete_task.assert_called_once_with("task123")


class TestUserOperationsWithMocks(unittest.TestCase):
    """Test user/workspace operations with mocks."""

    @patch("asana_sdk.users.get_client")
    @patch("asana_sdk.users.ASANA_SDK_AVAILABLE", True)
    def test_get_workspaces(self, mock_get_client):
        """Test getting workspaces."""
        from asana_sdk.users import get_workspaces

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_workspaces_api = MagicMock()
        mock_workspaces_api.get_workspaces.return_value = [
            {"gid": "ws1", "name": "Workspace 1"},
            {"gid": "ws2", "name": "Workspace 2"},
        ]

        with patch("asana_sdk.users.asana") as mock_asana:
            mock_asana.WorkspacesApi.return_value = mock_workspaces_api

            result = get_workspaces()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "Workspace 1")

    @patch("asana_sdk.users.get_workspaces")
    def test_get_workspace_by_name(self, mock_get_workspaces):
        """Test getting workspace by name."""
        from asana_sdk.users import get_workspace_by_name

        mock_get_workspaces.return_value = [
            {"gid": "ws1", "name": "My Workspace"},
            {"gid": "ws2", "name": "Other Workspace"},
        ]

        result = get_workspace_by_name("My Workspace")
        self.assertEqual(result, "ws1")

    @patch("asana_sdk.users.get_workspaces")
    def test_get_workspace_by_name_not_found(self, mock_get_workspaces):
        """Test workspace not found raises error."""
        from asana_sdk.users import get_workspace_by_name

        mock_get_workspaces.return_value = [
            {"gid": "ws1", "name": "My Workspace"},
        ]

        with self.assertRaises(AsanaClientError) as ctx:
            get_workspace_by_name("Nonexistent")

        self.assertIn("not found", str(ctx.exception).lower())

    @patch("asana_sdk.users.get_workspaces")
    def test_get_first_workspace(self, mock_get_workspaces):
        """Test getting first workspace when no name specified."""
        from asana_sdk.users import get_workspace_by_name

        mock_get_workspaces.return_value = [
            {"gid": "ws1", "name": "First Workspace"},
            {"gid": "ws2", "name": "Second Workspace"},
        ]

        result = get_workspace_by_name()  # No name
        self.assertEqual(result, "ws1")


class TestProjectOperationsWithMocks(unittest.TestCase):
    """Test project operations with mocks."""

    @patch("asana_sdk.projects.get_client")
    @patch("asana_sdk.projects.ASANA_SDK_AVAILABLE", True)
    def test_get_project(self, mock_get_client):
        """Test getting a project."""
        from asana_sdk.projects import get_project

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_projects_api = MagicMock()
        mock_projects_api.get_project.return_value = {
            "gid": "proj123",
            "name": "Test Project",
        }

        with patch("asana_sdk.projects.asana") as mock_asana:
            mock_asana.ProjectsApi.return_value = mock_projects_api

            result = get_project("proj123")

        self.assertEqual(result["name"], "Test Project")

    def test_get_project_validates_input(self):
        """Test get_project validates input."""
        from asana_sdk.projects import get_project

        with self.assertRaises(ValueError):
            get_project("")

        with self.assertRaises(ValueError):
            get_project(None)


class TestAttachmentOperationsWithMocks(unittest.TestCase):
    """Test attachment operations with mocks."""

    @patch("asana_sdk.attachments.get_client")
    @patch("asana_sdk.attachments.ASANA_SDK_AVAILABLE", True)
    def test_get_task_attachments(self, mock_get_client):
        """Test getting task attachments."""
        from asana_sdk.attachments import get_task_attachments

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_att = MagicMock()
        mock_att.to_dict.return_value = {"gid": "att1", "name": "file.png"}

        mock_attachments_api = MagicMock()
        mock_attachments_api.get_attachments_for_object.return_value = [mock_att]

        with patch("asana_sdk.attachments.asana") as mock_asana:
            mock_asana.AttachmentsApi.return_value = mock_attachments_api

            result = get_task_attachments("task123")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "file.png")

    def test_upload_validates_inputs(self):
        """Test upload_attachment_to_task validates inputs."""
        from asana_sdk.attachments import upload_attachment_to_task

        with self.assertRaises(ValueError):
            upload_attachment_to_task("")  # No task_gid

        with self.assertRaises(ValueError):
            upload_attachment_to_task("task123")  # No file

        with self.assertRaises(ValueError):
            upload_attachment_to_task(
                "task123",
                file_path="/path",
                file_content=b"bytes"  # Both provided
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
