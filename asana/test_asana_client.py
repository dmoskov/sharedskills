#!/usr/bin/env python3
"""
Unit tests for asana_client.py

Tests cover:
- Client initialization and authentication
- Workspace operations
- Project operations
- Task CRUD operations
- Search operations
- Dependency operations
- Story/Comment operations
- Subtask operations
- Error handling and retries
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from asana_client import (
    AsanaClient,
    AsanaError,
    AsanaAPIError,
    AsanaAuthError,
)


class TestClientInitialization:
    """Tests for AsanaClient initialization."""

    def test_init_with_token(self):
        """Should initialize with provided token."""
        client = AsanaClient(token="test_token_123")
        assert client._token == "test_token_123"

    def test_init_with_env_token(self):
        """Should use ASANA_ACCESS_TOKEN env var if no token provided."""
        with patch.dict(os.environ, {"ASANA_ACCESS_TOKEN": "env_token_456"}):
            client = AsanaClient()
            assert client._token == "env_token_456"

    def test_init_no_token_raises(self):
        """Should raise AsanaAuthError if no token available."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove ASANA_ACCESS_TOKEN if present
            os.environ.pop("ASANA_ACCESS_TOKEN", None)
            with pytest.raises(AsanaAuthError) as exc_info:
                AsanaClient()
            assert "No Asana token provided" in str(exc_info.value)

    def test_init_with_workspace(self):
        """Should store workspace if provided."""
        client = AsanaClient(token="test", workspace="workspace_123")
        assert client._workspace == "workspace_123"

    def test_init_with_env_workspace(self):
        """Should use ASANA_WORKSPACE env var."""
        with patch.dict(os.environ, {
            "ASANA_ACCESS_TOKEN": "token",
            "ASANA_WORKSPACE": "env_workspace_789"
        }):
            client = AsanaClient()
            assert client._workspace == "env_workspace_789"


class TestRequestHandling:
    """Tests for _request method and error handling."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked session."""
        with patch.dict(os.environ, {"ASANA_ACCESS_TOKEN": "test_token"}):
            client = AsanaClient()
            client._session = MagicMock()
            return client

    def test_successful_request(self, client):
        """Should return data from successful response."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"gid": "123", "name": "Test"}}
        client._session.request.return_value = mock_response

        result = client._request("GET", "tasks/123")

        assert result == {"data": {"gid": "123", "name": "Test"}}
        client._session.request.assert_called_once()

    def test_auth_error_401(self, client):
        """Should raise AsanaAuthError on 401 response."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 401
        client._session.request.return_value = mock_response

        with pytest.raises(AsanaAuthError) as exc_info:
            client._request("GET", "tasks/123")
        assert "Authentication failed" in str(exc_info.value)

    def test_rate_limit_429(self, client):
        """Should raise AsanaAPIError with retry info on 429."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        client._session.request.return_value = mock_response

        with pytest.raises(AsanaAPIError) as exc_info:
            client._request("GET", "tasks/123")
        assert "Rate limited" in str(exc_info.value)
        assert exc_info.value.status_code == 429

    def test_api_error_with_details(self, client):
        """Should include error details from response."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "errors": [{"message": "Invalid request"}]
        }
        client._session.request.return_value = mock_response

        with pytest.raises(AsanaAPIError) as exc_info:
            client._request("GET", "tasks/123")
        assert "Invalid request" in str(exc_info.value)
        assert exc_info.value.status_code == 400

    def test_timeout_retry(self, client):
        """Should retry on timeout."""
        import requests

        # First call times out, second succeeds
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"gid": "123"}}

        client._session.request.side_effect = [
            requests.Timeout("Connection timed out"),
            mock_response
        ]

        result = client._request("GET", "tasks/123")

        assert result == {"data": {"gid": "123"}}
        assert client._session.request.call_count == 2

    def test_connection_error_retry(self, client):
        """Should retry on connection error."""
        import requests

        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"gid": "123"}}

        client._session.request.side_effect = [
            requests.ConnectionError("Connection refused"),
            mock_response
        ]

        result = client._request("GET", "tasks/123")

        assert result == {"data": {"gid": "123"}}
        assert client._session.request.call_count == 2

    def test_max_retries_exceeded(self, client):
        """Should raise error after max retries."""
        import requests

        client._session.request.side_effect = requests.Timeout("Timeout")

        with pytest.raises(AsanaAPIError) as exc_info:
            client._request("GET", "tasks/123")
        assert "timed out" in str(exc_info.value)


class TestWorkspaceOperations:
    """Tests for workspace operations."""

    @pytest.fixture
    def client(self):
        with patch.dict(os.environ, {"ASANA_ACCESS_TOKEN": "test_token"}):
            client = AsanaClient()
            client._session = MagicMock()
            return client

    def test_list_workspaces(self, client):
        """Should return list of workspaces."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"gid": "ws1", "name": "Workspace 1", "is_organization": True},
                {"gid": "ws2", "name": "Workspace 2", "is_organization": False}
            ]
        }
        client._session.request.return_value = mock_response

        result = client.list_workspaces()

        assert len(result) == 2
        assert result[0]["gid"] == "ws1"
        assert result[1]["name"] == "Workspace 2"

    def test_get_workspace_auto_detect(self, client):
        """Should auto-detect workspace if not provided."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"gid": "auto_ws", "name": "Auto Workspace"}]
        }
        client._session.request.return_value = mock_response

        result = client._get_workspace()

        assert result == "auto_ws"
        assert client._workspace == "auto_ws"

    def test_get_workspace_uses_cached(self, client):
        """Should use cached workspace."""
        client._workspace = "cached_ws"

        result = client._get_workspace()

        assert result == "cached_ws"
        client._session.request.assert_not_called()


class TestProjectOperations:
    """Tests for project operations."""

    @pytest.fixture
    def client(self):
        with patch.dict(os.environ, {"ASANA_ACCESS_TOKEN": "test_token"}):
            client = AsanaClient(workspace="test_ws")
            client._session = MagicMock()
            return client

    def test_get_project(self, client):
        """Should return project details."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "proj1",
                "name": "Test Project",
                "notes": "Description"
            }
        }
        client._session.request.return_value = mock_response

        result = client.get_project("proj1")

        assert result["gid"] == "proj1"
        assert result["name"] == "Test Project"

    def test_get_projects(self, client):
        """Should return list of projects."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"gid": "p1", "name": "Project 1"},
                {"gid": "p2", "name": "Project 2"}
            ]
        }
        client._session.request.return_value = mock_response

        result = client.get_projects()

        assert len(result) == 2
        assert result[0]["name"] == "Project 1"

    def test_get_project_sections(self, client):
        """Should return sections for a project."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"gid": "s1", "name": "To Do"},
                {"gid": "s2", "name": "In Progress"},
                {"gid": "s3", "name": "Done"}
            ]
        }
        client._session.request.return_value = mock_response

        result = client.get_project_sections("proj1")

        assert len(result) == 3
        assert result[0]["name"] == "To Do"


class TestTaskOperations:
    """Tests for task CRUD operations."""

    @pytest.fixture
    def client(self):
        with patch.dict(os.environ, {"ASANA_ACCESS_TOKEN": "test_token"}):
            client = AsanaClient(workspace="test_ws")
            client._session = MagicMock()
            return client

    def test_get_task(self, client):
        """Should return task details."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "task1",
                "name": "Test Task",
                "completed": False,
                "due_on": "2025-01-31"
            }
        }
        client._session.request.return_value = mock_response

        result = client.get_task("task1")

        assert result["gid"] == "task1"
        assert result["name"] == "Test Task"
        assert result["completed"] is False

    def test_get_tasks_by_project(self, client):
        """Should get tasks for a project."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"gid": "t1", "name": "Task 1"},
                {"gid": "t2", "name": "Task 2"}
            ]
        }
        client._session.request.return_value = mock_response

        result = client.get_tasks(project="proj1")

        assert len(result) == 2

    def test_get_tasks_requires_context(self, client):
        """Should raise error if no project/section/assignee provided."""
        with pytest.raises(ValueError) as exc_info:
            client.get_tasks()
        assert "Must provide project, section, or assignee" in str(exc_info.value)

    def test_create_task(self, client):
        """Should create a task."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {"gid": "new_task", "name": "New Task"}
        }
        client._session.request.return_value = mock_response

        result = client.create_task(
            name="New Task",
            project="proj1",
            due_on="2025-02-15",
            notes="Task description"
        )

        assert result["gid"] == "new_task"
        assert result["name"] == "New Task"

    def test_create_task_with_html_notes(self, client):
        """Should create task with HTML notes."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {"gid": "new_task", "name": "Task with HTML"}
        }
        client._session.request.return_value = mock_response

        result = client.create_task(
            name="Task with HTML",
            project="proj1",
            html_notes="<body><b>Bold</b> text</body>"
        )

        # Verify html_notes was passed
        call_args = client._session.request.call_args
        json_data = call_args.kwargs.get("json") or call_args[1].get("json")
        assert json_data["data"]["html_notes"] == "<body><b>Bold</b> text</body>"

    def test_create_task_with_custom_fields(self, client):
        """Should create task with custom fields."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {"gid": "new_task", "name": "Task with fields"}
        }
        client._session.request.return_value = mock_response

        result = client.create_task(
            name="Task with fields",
            project="proj1",
            custom_fields={"field1": "value1", "field2": "enum_gid"}
        )

        call_args = client._session.request.call_args
        json_data = call_args.kwargs.get("json") or call_args[1].get("json")
        assert json_data["data"]["custom_fields"] == {"field1": "value1", "field2": "enum_gid"}

    def test_create_task_with_section(self, client):
        """Should move task to section after creation."""
        # First call creates task, second moves to section
        create_response = Mock()
        create_response.ok = True
        create_response.status_code = 201
        create_response.json.return_value = {"data": {"gid": "new_task"}}

        section_response = Mock()
        section_response.ok = True
        section_response.status_code = 200
        section_response.json.return_value = {"data": {}}

        client._session.request.side_effect = [create_response, section_response]

        result = client.create_task(name="Task", project="proj1", section="section1")

        assert client._session.request.call_count == 2
        # Verify section add was called
        second_call = client._session.request.call_args_list[1]
        assert "sections/section1/addTask" in second_call.kwargs.get("url", second_call[1].get("url", ""))

    def test_update_task(self, client):
        """Should update a task."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"gid": "task1", "name": "Updated", "completed": True}
        }
        client._session.request.return_value = mock_response

        result = client.update_task("task1", completed=True, name="Updated")

        assert result["completed"] is True
        assert result["name"] == "Updated"

    def test_update_task_no_changes(self, client):
        """Should raise error if no updates provided."""
        with pytest.raises(ValueError) as exc_info:
            client.update_task("task1")
        assert "No updates provided" in str(exc_info.value)

    def test_delete_task(self, client):
        """Should delete a task."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        client._session.request.return_value = mock_response

        result = client.delete_task("task1")

        assert result is True


class TestSearchOperations:
    """Tests for task search."""

    @pytest.fixture
    def client(self):
        with patch.dict(os.environ, {"ASANA_ACCESS_TOKEN": "test_token"}):
            client = AsanaClient(workspace="test_ws")
            client._session = MagicMock()
            return client

    def test_search_tasks_by_text(self, client):
        """Should search tasks by text."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"gid": "t1", "name": "Bug fix"},
                {"gid": "t2", "name": "Bug report"}
            ]
        }
        client._session.request.return_value = mock_response

        result = client.search_tasks(text="bug")

        assert len(result) == 2
        # Verify search endpoint was called
        call_args = client._session.request.call_args
        assert "search" in call_args.kwargs.get("url", call_args[1].get("url", ""))

    def test_search_tasks_with_filters(self, client):
        """Should apply search filters."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        client._session.request.return_value = mock_response

        client.search_tasks(
            text="test",
            assignee="me",
            completed=False,
            limit=50
        )

        call_args = client._session.request.call_args
        params = call_args.kwargs.get("params", call_args[1].get("params", {}))
        assert params.get("text") == "test"
        assert params.get("assignee.any") == "me"
        assert params.get("completed") == "false"
        assert params.get("limit") == "50"


class TestDependencyOperations:
    """Tests for dependency operations."""

    @pytest.fixture
    def client(self):
        with patch.dict(os.environ, {"ASANA_ACCESS_TOKEN": "test_token"}):
            client = AsanaClient(workspace="test_ws")
            client._session = MagicMock()
            return client

    def test_get_dependencies(self, client):
        """Should get task dependencies."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"gid": "dep1", "name": "Dependency 1", "completed": True},
                {"gid": "dep2", "name": "Dependency 2", "completed": False}
            ]
        }
        client._session.request.return_value = mock_response

        result = client.get_dependencies("task1")

        assert len(result) == 2
        assert result[0]["gid"] == "dep1"

    def test_add_dependency(self, client):
        """Should add a dependency."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        client._session.request.return_value = mock_response

        result = client.add_dependency("task1", "task2")

        call_args = client._session.request.call_args
        assert "addDependencies" in call_args.kwargs.get("url", call_args[1].get("url", ""))

    def test_add_dependencies_bulk(self, client):
        """Should add multiple dependencies at once."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        client._session.request.return_value = mock_response

        result = client.add_dependencies("task1", ["task2", "task3", "task4"])

        call_args = client._session.request.call_args
        json_data = call_args.kwargs.get("json") or call_args[1].get("json")
        assert json_data["data"]["dependencies"] == ["task2", "task3", "task4"]

    def test_add_dependencies_empty_list(self, client):
        """Should handle empty dependency list."""
        result = client.add_dependencies("task1", [])

        assert result == {}
        client._session.request.assert_not_called()

    def test_remove_dependency(self, client):
        """Should remove a dependency."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        client._session.request.return_value = mock_response

        result = client.remove_dependency("task1", "task2")

        call_args = client._session.request.call_args
        assert "removeDependencies" in call_args.kwargs.get("url", call_args[1].get("url", ""))

    def test_get_dependents(self, client):
        """Should get tasks that depend on this task."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"gid": "dependent1", "name": "Blocked Task"}]
        }
        client._session.request.return_value = mock_response

        result = client.get_dependents("task1")

        assert len(result) == 1
        assert result[0]["name"] == "Blocked Task"
        call_args = client._session.request.call_args
        assert "dependents" in call_args.kwargs.get("url", call_args[1].get("url", ""))

    def test_chain_dependencies(self, client):
        """Should chain tasks sequentially."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        client._session.request.return_value = mock_response

        count = client.chain_dependencies(["task1", "task2", "task3", "task4"])

        assert count == 3  # 3 dependencies created
        assert client._session.request.call_count == 3

    def test_chain_dependencies_single_task(self, client):
        """Should handle single task (no dependencies to create)."""
        count = client.chain_dependencies(["task1"])

        assert count == 0
        client._session.request.assert_not_called()


class TestStoryOperations:
    """Tests for story/comment operations."""

    @pytest.fixture
    def client(self):
        with patch.dict(os.environ, {"ASANA_ACCESS_TOKEN": "test_token"}):
            client = AsanaClient(workspace="test_ws")
            client._session = MagicMock()
            return client

    def test_get_stories(self, client):
        """Should get all stories for a task."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"gid": "s1", "resource_subtype": "comment_added", "text": "Comment 1"},
                {"gid": "s2", "resource_subtype": "assigned", "text": "Assigned to user"},
                {"gid": "s3", "resource_subtype": "comment_added", "text": "Comment 2"}
            ]
        }
        client._session.request.return_value = mock_response

        result = client.get_stories("task1")

        assert len(result) == 3  # All stories returned

    def test_get_comments(self, client):
        """Should filter to only comments."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"gid": "s1", "resource_subtype": "comment_added", "text": "Comment 1"},
                {"gid": "s2", "resource_subtype": "assigned", "text": "Assigned"},
                {"gid": "s3", "resource_subtype": "comment_added", "text": "Comment 2"}
            ]
        }
        client._session.request.return_value = mock_response

        result = client.get_comments("task1")

        assert len(result) == 2  # Only comments
        assert all(s["resource_subtype"] == "comment_added" for s in result)

    def test_add_comment(self, client):
        """Should add a comment to a task."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {"gid": "story1", "text": "New comment"}
        }
        client._session.request.return_value = mock_response

        result = client.add_comment("task1", "New comment")

        assert result["text"] == "New comment"
        call_args = client._session.request.call_args
        json_data = call_args.kwargs.get("json") or call_args[1].get("json")
        assert json_data["data"]["text"] == "New comment"


class TestSubtaskOperations:
    """Tests for subtask operations."""

    @pytest.fixture
    def client(self):
        with patch.dict(os.environ, {"ASANA_ACCESS_TOKEN": "test_token"}):
            client = AsanaClient(workspace="test_ws")
            client._session = MagicMock()
            return client

    def test_get_subtasks(self, client):
        """Should get subtasks for a task."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"gid": "sub1", "name": "Subtask 1", "completed": False},
                {"gid": "sub2", "name": "Subtask 2", "completed": True}
            ]
        }
        client._session.request.return_value = mock_response

        result = client.get_subtasks("task1")

        assert len(result) == 2
        assert result[0]["name"] == "Subtask 1"

    def test_create_subtask(self, client):
        """Should create a subtask."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {"gid": "new_sub", "name": "New Subtask"}
        }
        client._session.request.return_value = mock_response

        result = client.create_subtask(
            "parent_task",
            name="New Subtask",
            assignee="user1",
            due_on="2025-02-01"
        )

        assert result["name"] == "New Subtask"
        call_args = client._session.request.call_args
        assert "subtasks" in call_args.kwargs.get("url", call_args[1].get("url", ""))


class TestUserOperations:
    """Tests for user operations."""

    @pytest.fixture
    def client(self):
        with patch.dict(os.environ, {"ASANA_ACCESS_TOKEN": "test_token"}):
            client = AsanaClient(workspace="test_ws")
            client._session = MagicMock()
            return client

    def test_get_me(self, client):
        """Should get current user info."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "user1",
                "name": "Test User",
                "email": "test@example.com"
            }
        }
        client._session.request.return_value = mock_response

        result = client.get_me()

        assert result["name"] == "Test User"
        assert result["email"] == "test@example.com"


class TestExceptionClasses:
    """Tests for exception classes."""

    def test_asana_error_base(self):
        """AsanaError should be base exception."""
        error = AsanaError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_asana_api_error_with_status(self):
        """AsanaAPIError should store status code."""
        error = AsanaAPIError("API error", status_code=400)
        assert error.status_code == 400
        assert "API error" in str(error)

    def test_asana_auth_error(self):
        """AsanaAuthError should inherit from AsanaError."""
        error = AsanaAuthError("Auth failed")
        assert isinstance(error, AsanaError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
