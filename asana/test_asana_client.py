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
    cmd_workspaces,
    cmd_projects,
    cmd_task,
    cmd_tasks,
    cmd_search,
    cmd_my_tasks,
    format_task,
)
from io import StringIO


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


class TestPortfolioOperations:
    """Tests for portfolio operations."""

    @pytest.fixture
    def client(self):
        with patch.dict(os.environ, {"ASANA_ACCESS_TOKEN": "test_token"}):
            client = AsanaClient(workspace="test_ws")
            client._session = MagicMock()
            return client

    def test_get_portfolio(self, client):
        """Should return portfolio details."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "portfolio1",
                "name": "Q1 Projects",
                "owner": {"name": "Test User"},
                "color": "light-blue"
            }
        }
        client._session.request.return_value = mock_response

        result = client.get_portfolio("portfolio1")

        assert result["gid"] == "portfolio1"
        assert result["name"] == "Q1 Projects"
        call_args = client._session.request.call_args
        assert "portfolios/portfolio1" in call_args.kwargs.get("url", call_args[1].get("url", ""))

    def test_get_portfolios(self, client):
        """Should return list of portfolios."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"gid": "p1", "name": "Portfolio 1"},
                {"gid": "p2", "name": "Portfolio 2"}
            ]
        }
        client._session.request.return_value = mock_response

        result = client.get_portfolios()

        assert len(result) == 2
        assert result[0]["name"] == "Portfolio 1"

    def test_get_portfolios_with_owner(self, client):
        """Should filter portfolios by owner."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        client._session.request.return_value = mock_response

        client.get_portfolios(owner="user123")

        call_args = client._session.request.call_args
        params = call_args.kwargs.get("params", call_args[1].get("params", {}))
        assert params.get("owner") == "user123"

    def test_get_portfolio_items(self, client):
        """Should return items in a portfolio."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"gid": "proj1", "name": "Project 1", "resource_type": "project"},
                {"gid": "proj2", "name": "Project 2", "resource_type": "project"}
            ]
        }
        client._session.request.return_value = mock_response

        result = client.get_portfolio_items("portfolio1")

        assert len(result) == 2
        assert result[0]["resource_type"] == "project"
        call_args = client._session.request.call_args
        assert "portfolios/portfolio1/items" in call_args.kwargs.get("url", call_args[1].get("url", ""))


class TestTeamOperations:
    """Tests for team operations."""

    @pytest.fixture
    def client(self):
        with patch.dict(os.environ, {"ASANA_ACCESS_TOKEN": "test_token"}):
            client = AsanaClient(workspace="test_ws")
            client._session = MagicMock()
            return client

    def test_get_teams(self, client):
        """Should return list of teams."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"gid": "team1", "name": "Engineering"},
                {"gid": "team2", "name": "Design"}
            ]
        }
        client._session.request.return_value = mock_response

        result = client.get_teams()

        assert len(result) == 2
        assert result[0]["name"] == "Engineering"
        call_args = client._session.request.call_args
        assert "organizations/test_ws/teams" in call_args.kwargs.get("url", call_args[1].get("url", ""))

    def test_get_team(self, client):
        """Should return team details."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "team1",
                "name": "Engineering",
                "description": "The engineering team"
            }
        }
        client._session.request.return_value = mock_response

        result = client.get_team("team1")

        assert result["gid"] == "team1"
        assert result["name"] == "Engineering"

    def test_get_team_members(self, client):
        """Should return team members."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"gid": "user1", "name": "Alice", "email": "alice@example.com"},
                {"gid": "user2", "name": "Bob", "email": "bob@example.com"}
            ]
        }
        client._session.request.return_value = mock_response

        result = client.get_team_members("team1")

        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        call_args = client._session.request.call_args
        assert "teams/team1/users" in call_args.kwargs.get("url", call_args[1].get("url", ""))


class TestTagOperations:
    """Tests for tag operations."""

    @pytest.fixture
    def client(self):
        with patch.dict(os.environ, {"ASANA_ACCESS_TOKEN": "test_token"}):
            client = AsanaClient(workspace="test_ws")
            client._session = MagicMock()
            return client

    def test_get_tags(self, client):
        """Should return list of tags."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"gid": "tag1", "name": "urgent", "color": "red"},
                {"gid": "tag2", "name": "blocked", "color": "yellow"}
            ]
        }
        client._session.request.return_value = mock_response

        result = client.get_tags()

        assert len(result) == 2
        assert result[0]["name"] == "urgent"

    def test_get_tag(self, client):
        """Should return tag details."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"gid": "tag1", "name": "urgent", "color": "red", "notes": "High priority"}
        }
        client._session.request.return_value = mock_response

        result = client.get_tag("tag1")

        assert result["name"] == "urgent"
        assert result["color"] == "red"

    def test_create_tag(self, client):
        """Should create a new tag."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {"gid": "new_tag", "name": "feature", "color": "green"}
        }
        client._session.request.return_value = mock_response

        result = client.create_tag(name="feature", color="green")

        assert result["name"] == "feature"
        call_args = client._session.request.call_args
        json_data = call_args.kwargs.get("json") or call_args[1].get("json")
        assert json_data["data"]["name"] == "feature"
        assert json_data["data"]["color"] == "green"

    def test_update_tag(self, client):
        """Should update a tag."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"gid": "tag1", "name": "critical", "color": "red"}
        }
        client._session.request.return_value = mock_response

        result = client.update_tag("tag1", name="critical")

        assert result["name"] == "critical"

    def test_update_tag_no_changes(self, client):
        """Should raise error if no updates provided."""
        with pytest.raises(ValueError) as exc_info:
            client.update_tag("tag1")
        assert "No updates provided" in str(exc_info.value)

    def test_delete_tag(self, client):
        """Should delete a tag."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        client._session.request.return_value = mock_response

        result = client.delete_tag("tag1")

        assert result is True
        call_args = client._session.request.call_args
        assert call_args.kwargs.get("method") == "DELETE" or call_args[0][0] == "DELETE"

    def test_add_tag_to_task(self, client):
        """Should add a tag to a task."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        client._session.request.return_value = mock_response

        result = client.add_tag_to_task("task1", "tag1")

        call_args = client._session.request.call_args
        assert "tasks/task1/addTag" in call_args.kwargs.get("url", call_args[1].get("url", ""))
        json_data = call_args.kwargs.get("json") or call_args[1].get("json")
        assert json_data["data"]["tag"] == "tag1"

    def test_remove_tag_from_task(self, client):
        """Should remove a tag from a task."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        client._session.request.return_value = mock_response

        result = client.remove_tag_from_task("task1", "tag1")

        call_args = client._session.request.call_args
        assert "tasks/task1/removeTag" in call_args.kwargs.get("url", call_args[1].get("url", ""))


class TestSectionCRUDOperations:
    """Tests for section CRUD operations."""

    @pytest.fixture
    def client(self):
        with patch.dict(os.environ, {"ASANA_ACCESS_TOKEN": "test_token"}):
            client = AsanaClient(workspace="test_ws")
            client._session = MagicMock()
            return client

    def test_create_section(self, client):
        """Should create a section in a project."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {"gid": "new_section", "name": "In Review"}
        }
        client._session.request.return_value = mock_response

        result = client.create_section("proj1", "In Review")

        assert result["name"] == "In Review"
        call_args = client._session.request.call_args
        assert "projects/proj1/sections" in call_args.kwargs.get("url", call_args[1].get("url", ""))

    def test_create_section_with_position(self, client):
        """Should create section with insert position."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {"gid": "new_section", "name": "New Section"}
        }
        client._session.request.return_value = mock_response

        result = client.create_section("proj1", "New Section", insert_after="section1")

        call_args = client._session.request.call_args
        json_data = call_args.kwargs.get("json") or call_args[1].get("json")
        assert json_data["data"]["insert_after"] == "section1"

    def test_update_section(self, client):
        """Should update a section's name."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"gid": "section1", "name": "Done"}
        }
        client._session.request.return_value = mock_response

        result = client.update_section("section1", "Done")

        assert result["name"] == "Done"
        call_args = client._session.request.call_args
        assert "sections/section1" in call_args.kwargs.get("url", call_args[1].get("url", ""))

    def test_delete_section(self, client):
        """Should delete a section."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        client._session.request.return_value = mock_response

        result = client.delete_section("section1")

        assert result is True
        call_args = client._session.request.call_args
        assert call_args.kwargs.get("method") == "DELETE" or call_args[0][0] == "DELETE"

    def test_move_section(self, client):
        """Should move/reorder a section."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        client._session.request.return_value = mock_response

        result = client.move_section("proj1", "section1", after_section="section2")

        call_args = client._session.request.call_args
        assert "projects/proj1/sections/insert" in call_args.kwargs.get("url", call_args[1].get("url", ""))
        json_data = call_args.kwargs.get("json") or call_args[1].get("json")
        assert json_data["data"]["section"] == "section1"
        assert json_data["data"]["after_section"] == "section2"


class TestTaskMovementOperations:
    """Tests for task movement and reparenting operations."""

    @pytest.fixture
    def client(self):
        with patch.dict(os.environ, {"ASANA_ACCESS_TOKEN": "test_token"}):
            client = AsanaClient(workspace="test_ws")
            client._session = MagicMock()
            return client

    def test_move_task_to_section(self, client):
        """Should move a task to a section."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        client._session.request.return_value = mock_response

        result = client.move_task_to_section("task1", "section1")

        call_args = client._session.request.call_args
        assert "sections/section1/addTask" in call_args.kwargs.get("url", call_args[1].get("url", ""))
        json_data = call_args.kwargs.get("json") or call_args[1].get("json")
        assert json_data["data"]["task"] == "task1"

    def test_move_task_to_section_with_position(self, client):
        """Should move task with insert position."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        client._session.request.return_value = mock_response

        client.move_task_to_section("task1", "section1", insert_after="task2")

        call_args = client._session.request.call_args
        json_data = call_args.kwargs.get("json") or call_args[1].get("json")
        assert json_data["data"]["task"] == "task1"
        assert json_data["data"]["insert_after"] == "task2"

    def test_set_parent(self, client):
        """Should set parent of a task (make it a subtask)."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"gid": "task1", "name": "Subtask", "parent": {"gid": "parent1"}}
        }
        client._session.request.return_value = mock_response

        result = client.set_parent("task1", "parent1")

        call_args = client._session.request.call_args
        assert "tasks/task1/setParent" in call_args.kwargs.get("url", call_args[1].get("url", ""))
        json_data = call_args.kwargs.get("json") or call_args[1].get("json")
        assert json_data["data"]["parent"] == "parent1"

    def test_set_parent_remove(self, client):
        """Should remove parent (make task standalone)."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"gid": "task1", "name": "Task", "parent": None}
        }
        client._session.request.return_value = mock_response

        result = client.set_parent("task1", None)

        call_args = client._session.request.call_args
        json_data = call_args.kwargs.get("json") or call_args[1].get("json")
        assert json_data["data"]["parent"] is None

    def test_set_parent_with_position(self, client):
        """Should set parent with sibling position."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"gid": "task1", "name": "Subtask"}
        }
        client._session.request.return_value = mock_response

        client.set_parent("task1", "parent1", insert_before="sibling1")

        call_args = client._session.request.call_args
        json_data = call_args.kwargs.get("json") or call_args[1].get("json")
        assert json_data["data"]["parent"] == "parent1"
        assert json_data["data"]["insert_before"] == "sibling1"


class TestCLIIntegration:
    """Tests for CLI command functions."""

    @pytest.fixture
    def client(self):
        with patch.dict(os.environ, {"ASANA_ACCESS_TOKEN": "test_token"}):
            client = AsanaClient(workspace="test_ws")
            client._session = MagicMock()
            return client

    @pytest.fixture
    def mock_args(self):
        """Create a mock args object."""
        args = Mock()
        args.json = False
        args.verbose = False
        return args

    def test_format_task_incomplete(self):
        """Should format incomplete task correctly."""
        task = {"name": "Test Task", "due_on": "2025-01-31", "completed": False, "assignee": {"name": "Alice"}}
        result = format_task(task)
        assert "[ ]" in result
        assert "Test Task" in result
        assert "2025-01-31" in result
        assert "Alice" in result

    def test_format_task_completed(self):
        """Should format completed task with checkmark."""
        task = {"name": "Done Task", "due_on": None, "completed": True, "assignee": None}
        result = format_task(task)
        assert "[✓]" in result
        assert "Done Task" in result

    def test_format_task_verbose(self):
        """Should include GID in verbose mode."""
        task = {"gid": "123456", "name": "Task", "due_on": None, "completed": False, "assignee": None}
        result = format_task(task, verbose=True)
        assert "123456" in result

    def test_cmd_workspaces(self, client, mock_args, capsys):
        """Should print workspace list."""
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

        cmd_workspaces(client, mock_args)
        captured = capsys.readouterr()

        assert "Workspace 1" in captured.out
        assert "Workspace 2" in captured.out
        assert "ws1" in captured.out

    def test_cmd_workspaces_json(self, client, mock_args, capsys):
        """Should output JSON when --json flag is set."""
        mock_args.json = True
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"gid": "ws1", "name": "Test Workspace"}]
        }
        client._session.request.return_value = mock_response

        cmd_workspaces(client, mock_args)
        captured = capsys.readouterr()

        output = json.loads(captured.out)
        assert output[0]["gid"] == "ws1"

    def test_cmd_projects(self, client, mock_args, capsys):
        """Should print project list."""
        mock_args.archived = False
        mock_args.limit = 50
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"gid": "p1", "name": "Project 1", "due_on": "2025-02-01"},
                {"gid": "p2", "name": "Project 2", "due_on": None}
            ]
        }
        client._session.request.return_value = mock_response

        cmd_projects(client, mock_args)
        captured = capsys.readouterr()

        assert "Project 1" in captured.out
        assert "Project 2" in captured.out

    def test_cmd_task(self, client, mock_args, capsys):
        """Should print task details."""
        mock_args.task_gid = "task123"
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "task123",
                "name": "Important Task",
                "completed": False,
                "due_on": "2025-03-15",
                "assignee": {"name": "Bob"},
                "projects": [{"name": "Project X"}],
                "notes": "Task description here"
            }
        }
        client._session.request.return_value = mock_response

        cmd_task(client, mock_args)
        captured = capsys.readouterr()

        assert "Important Task" in captured.out
        assert "task123" in captured.out
        assert "Bob" in captured.out
        assert "Project X" in captured.out

    def test_cmd_search(self, client, mock_args, capsys):
        """Should print search results."""
        mock_args.query = "bug"
        mock_args.incomplete = True
        mock_args.limit = 50
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"gid": "t1", "name": "Fix bug #1", "due_on": None, "completed": False, "assignee": None},
                {"gid": "t2", "name": "Bug report", "due_on": "2025-01-20", "completed": False, "assignee": {"name": "Dev"}}
            ]
        }
        client._session.request.return_value = mock_response

        cmd_search(client, mock_args)
        captured = capsys.readouterr()

        assert "Fix bug #1" in captured.out
        assert "Bug report" in captured.out
        assert "(2 tasks)" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
