#!/usr/bin/env python3
"""
Asana REST API Client for Claude Code.

A self-contained client with 30-second timeouts and automatic retries.
No external dependencies beyond requests.

Environment Variables:
    ASANA_ACCESS_TOKEN: Personal Access Token (required)
    ASANA_WORKSPACE: Default workspace GID (optional)

Usage as CLI:
    python3 asana_client.py workspaces
    python3 asana_client.py projects
    python3 asana_client.py tasks --project <gid> --incomplete
    python3 asana_client.py task <gid>
    python3 asana_client.py search "keyword"
    python3 asana_client.py create "Task name" --project <gid>
    python3 asana_client.py update <gid> --completed true
    python3 asana_client.py comment <gid> "Comment text"
    python3 asana_client.py my-tasks
    python3 asana_client.py sections <project_gid>
    python3 asana_client.py stories <task_gid>
    python3 asana_client.py subtasks <task_gid>

Usage as library:
    from asana_client import AsanaClient
    client = AsanaClient()
    tasks = client.search_tasks(text="keyword")
"""

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    print("Error: requests package required. Install with: pip install requests")
    sys.exit(1)

from markdown_to_asana import markdown_to_asana_html

# Configure logging
logger = logging.getLogger(__name__)

# Constants
ASANA_BASE_URL = "https://app.asana.com/api/1.0"
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3


class AsanaError(Exception):
    """Base exception for Asana errors."""
    pass


class AsanaAPIError(AsanaError):
    """Raised when Asana API returns an error."""

    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        super().__init__(message)


class AsanaAuthError(AsanaError):
    """Raised when authentication fails."""
    pass


class AsanaClient:
    """
    Asana REST API client.

    All operations have 30-second timeouts and automatic retries.
    """

    def __init__(self, token: str = None, workspace: str = None):
        """
        Initialize client.

        Args:
            token: Access token. If not provided, checks ASANA_ACCESS_TOKEN env var,
                   then falls back to OAuth tokens in ~/.config/asana/tokens.json
            workspace: Default workspace GID. If not provided, uses ASANA_WORKSPACE env var.
        """
        self._token = token or os.environ.get("ASANA_ACCESS_TOKEN") or self._load_oauth_token()
        self._workspace = workspace or os.environ.get("ASANA_WORKSPACE")
        self._session = requests.Session()
        self._session.headers["Accept"] = "application/json"

        if not self._token:
            raise AsanaAuthError(
                "No Asana token provided.\n"
                "Options:\n"
                "  1. Run: python3 oauth_setup.py  (recommended)\n"
                "  2. Set ASANA_ACCESS_TOKEN environment variable\n"
                "  3. Pass token to constructor"
            )

    def _load_oauth_token(self) -> Optional[str]:
        """Load OAuth token from ~/.config/asana/tokens.json if available."""
        import time
        token_file = os.path.expanduser("~/.config/asana/tokens.json")
        if not os.path.exists(token_file):
            return None

        try:
            with open(token_file) as f:
                tokens = json.load(f)

            # Check if token is expired
            expires_at = tokens.get("expires_at", 0)
            if time.time() > expires_at - 60:  # 60 second buffer
                # Try to refresh
                refreshed = self._refresh_oauth_token(tokens)
                if refreshed:
                    return refreshed
                return None

            return tokens.get("access_token")
        except (json.JSONDecodeError, IOError, KeyError):
            return None

    def _refresh_oauth_token(self, tokens: dict) -> Optional[str]:
        """Refresh OAuth token using refresh_token."""
        import time
        import urllib.request
        import urllib.parse
        import urllib.error

        refresh_token = tokens.get("refresh_token")
        client_id = tokens.get("client_id")
        client_secret = tokens.get("client_secret")

        if not all([refresh_token, client_id, client_secret]):
            return None

        try:
            data = urllib.parse.urlencode({
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
            }).encode()

            req = urllib.request.Request(
                "https://app.asana.com/-/oauth_token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                new_tokens = json.loads(resp.read())

            # Update token file
            tokens["access_token"] = new_tokens["access_token"]
            tokens["expires_at"] = time.time() + new_tokens.get("expires_in", 3600)
            if "refresh_token" in new_tokens:
                tokens["refresh_token"] = new_tokens["refresh_token"]

            token_file = os.path.expanduser("~/.config/asana/tokens.json")
            with open(token_file, "w") as f:
                json.dump(tokens, f, indent=2)

            logger.info("OAuth token refreshed successfully")
            return new_tokens["access_token"]

        except (urllib.error.URLError, json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to refresh OAuth token: {e}")
            return None

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict = None,
        json_data: dict = None,
        retries: int = MAX_RETRIES,
    ) -> Dict[str, Any]:
        """Make authenticated request with retry logic."""
        headers = {"Authorization": f"Bearer {self._token}"}
        url = f"{ASANA_BASE_URL}/{endpoint}"

        try:
            resp = self._session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=REQUEST_TIMEOUT,
            )

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 60))
                raise AsanaAPIError(f"Rate limited. Retry after {retry_after}s", 429)

            if resp.status_code == 401:
                raise AsanaAuthError("Authentication failed. Check your access token.")

            if not resp.ok:
                error_detail = ""
                try:
                    error_json = resp.json()
                    if "errors" in error_json:
                        error_detail = "; ".join(
                            e.get("message", str(e)) for e in error_json["errors"]
                        )
                    elif "error" in error_json:
                        error_detail = error_json["error"]
                except json.JSONDecodeError:
                    # Response is not JSON - use raw text
                    error_detail = resp.text[:500] if resp.text else "No error details"

                raise AsanaAPIError(f"API error {resp.status_code}: {error_detail}", resp.status_code)

            return resp.json()

        except requests.Timeout:
            if retries > 0:
                logger.warning(f"Request timed out, retrying ({retries} left)...")
                return self._request(method, endpoint, params, json_data, retries - 1)
            raise AsanaAPIError(f"Request timed out after {REQUEST_TIMEOUT}s")

        except requests.ConnectionError as e:
            if retries > 0:
                logger.warning(f"Connection error, retrying ({retries} left)...")
                return self._request(method, endpoint, params, json_data, retries - 1)
            raise AsanaAPIError(f"Connection error: {e}")

    def _get_workspace(self, workspace: str = None) -> str:
        """Get workspace GID, resolving default if needed."""
        if workspace:
            return workspace
        if self._workspace:
            return self._workspace

        # Auto-detect: get first workspace
        workspaces = self.list_workspaces()
        if not workspaces:
            raise AsanaError("No workspaces found for this user")
        self._workspace = workspaces[0]["gid"]
        return self._workspace

    # ========== Workspace Operations ==========

    def list_workspaces(self) -> List[Dict[str, Any]]:
        """List all accessible workspaces."""
        result = self._request("GET", "workspaces", {"opt_fields": "name,is_organization"})
        return result.get("data", [])

    # ========== Project Operations ==========

    def get_project(self, project_gid: str, opt_fields: str = None) -> Dict[str, Any]:
        """Get project details."""
        params = {
            "opt_fields": opt_fields or "name,notes,owner.name,due_on,current_status.color,custom_fields"
        }
        result = self._request("GET", f"projects/{project_gid}", params)
        return result.get("data", {})

    def get_projects(
        self,
        workspace: str = None,
        archived: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List projects in workspace."""
        params = {
            "workspace": self._get_workspace(workspace),
            "archived": str(archived).lower(),
            "opt_fields": "name,owner.name,due_on,current_status.color",
            "limit": str(limit),
        }
        result = self._request("GET", "projects", params)
        return result.get("data", [])

    def get_project_sections(self, project_gid: str) -> List[Dict[str, Any]]:
        """Get sections in a project."""
        result = self._request("GET", f"projects/{project_gid}/sections", {"opt_fields": "name"})
        return result.get("data", [])

    def get_custom_field_settings(self, project_gid: str) -> List[Dict[str, Any]]:
        """Get custom field settings for a project, including enum options."""
        result = self._request(
            "GET",
            f"projects/{project_gid}/custom_field_settings",
            {"opt_fields": "custom_field.name,custom_field.type,custom_field.enum_options,custom_field.enum_options.name,custom_field.enum_options.enabled"},
        )
        return [item.get("custom_field", {}) for item in result.get("data", [])]

    # ========== Task Operations ==========

    def get_task(self, task_gid: str) -> Dict[str, Any]:
        """Get task details."""
        params = {
            "opt_fields": "name,notes,due_on,completed,assignee.name,projects.name,"
                          "custom_fields.name,custom_fields.display_value,tags.name,"
                          "memberships.section.name,dependencies,dependents"
        }
        result = self._request("GET", f"tasks/{task_gid}", params)
        return result.get("data", {})

    def get_tasks(
        self,
        project: str = None,
        section: str = None,
        assignee: str = None,
        workspace: str = None,
        completed: bool = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get tasks from project, section, or by assignee."""
        params = {
            "opt_fields": "name,due_on,completed,assignee.name,projects.name",
            "limit": str(limit),
        }

        if project:
            endpoint = f"projects/{project}/tasks"
        elif section:
            endpoint = f"sections/{section}/tasks"
        elif assignee:
            endpoint = "tasks"
            params["assignee"] = assignee
            params["workspace"] = self._get_workspace(workspace)
        else:
            raise ValueError("Must provide project, section, or assignee")

        if completed is not None:
            params["completed_since"] = "now" if not completed else None

        result = self._request("GET", endpoint, params)
        return result.get("data", [])

    def get_tasks_paginated(
        self,
        project: str = None,
        section: str = None,
        completed: bool = None,
    ) -> List[Dict[str, Any]]:
        """Get ALL tasks from project/section with automatic pagination."""
        params = {
            "opt_fields": "name,due_on,completed,assignee.name,projects.name",
            "limit": "100",
        }

        if project:
            endpoint = f"projects/{project}/tasks"
        elif section:
            endpoint = f"sections/{section}/tasks"
        else:
            raise ValueError("Must provide project or section")

        if completed is not None:
            params["completed_since"] = "now" if not completed else None

        all_tasks = []
        while True:
            result = self._request("GET", endpoint, params)
            all_tasks.extend(result.get("data", []))
            next_page = result.get("next_page")
            if not next_page or not next_page.get("offset"):
                break
            params["offset"] = next_page["offset"]

        return all_tasks

    def search_tasks(
        self,
        text: str = None,
        workspace: str = None,
        assignee: str = None,
        projects: str = None,
        completed: bool = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Search tasks with filters."""
        params = {
            "opt_fields": "name,due_on,completed,assignee.name,projects.name",
            "limit": str(min(limit, 100)),
            "sort_by": "modified_at",
            "sort_ascending": "false",
        }

        if text:
            params["text"] = text
        if assignee:
            params["assignee.any"] = assignee
        if projects:
            params["projects.any"] = projects
        if completed is not None:
            params["completed"] = str(completed).lower()

        ws = self._get_workspace(workspace)
        result = self._request("GET", f"workspaces/{ws}/tasks/search", params)
        return result.get("data", [])

    def create_task(
        self,
        name: str,
        project: Optional[str] = None,
        section: Optional[str] = None,
        assignee: Optional[str] = None,
        due_on: Optional[str] = None,
        notes: Optional[str] = None,
        html_notes: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        workspace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new task.

        Args:
            name: Task name (required)
            project: Project GID to add task to
            section: Section GID to place task in (requires project)
            assignee: User GID or 'me' to assign the task
            due_on: Due date in YYYY-MM-DD format
            notes: Plain text description
            html_notes: HTML description (use instead of notes, not both)
            custom_fields: Dict mapping custom field GIDs to values
            workspace: Workspace GID (auto-detected if not provided)

        Returns:
            Created task data including 'gid' and 'name'

        Raises:
            AsanaAPIError: If the API request fails
        """
        data = {"name": name}

        if project:
            data["projects"] = [project]
        if assignee:
            data["assignee"] = assignee
        if due_on:
            data["due_on"] = due_on
        if notes:
            data["notes"] = notes
        if html_notes:
            data["html_notes"] = html_notes
        if custom_fields:
            data["custom_fields"] = custom_fields
        if workspace and not project:
            data["workspace"] = self._get_workspace(workspace)
        elif not project:
            data["workspace"] = self._get_workspace()

        result = self._request("POST", "tasks", json_data={"data": data})
        task = result.get("data", {})

        # Move to section if specified
        if section and task.get("gid"):
            self._request(
                "POST",
                f"sections/{section}/addTask",
                json_data={"data": {"task": task["gid"]}},
            )

        return task

    def update_task(
        self,
        task_gid: str,
        name: Optional[str] = None,
        completed: Optional[bool] = None,
        assignee: Optional[str] = None,
        due_on: Optional[str] = None,
        notes: Optional[str] = None,
        html_notes: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update a task."""
        data = {}

        if name is not None:
            data["name"] = name
        if completed is not None:
            data["completed"] = completed
        if assignee is not None:
            data["assignee"] = assignee
        if due_on is not None:
            data["due_on"] = due_on
        if notes is not None:
            data["notes"] = notes
        if html_notes is not None:
            data["html_notes"] = html_notes
        if custom_fields is not None:
            data["custom_fields"] = custom_fields

        if not data:
            raise ValueError("No updates provided")

        result = self._request("PUT", f"tasks/{task_gid}", json_data={"data": data})
        return result.get("data", {})

    def delete_task(self, task_gid: str) -> bool:
        """Delete a task."""
        self._request("DELETE", f"tasks/{task_gid}")
        return True

    # ========== Subtask Operations ==========

    def get_subtasks(self, task_gid: str) -> List[Dict[str, Any]]:
        """Get subtasks of a task."""
        params = {"opt_fields": "name,completed,due_on,assignee.name"}
        result = self._request("GET", f"tasks/{task_gid}/subtasks", params)
        return result.get("data", [])

    def create_subtask(
        self,
        parent_gid: str,
        name: str,
        assignee: str = None,
        due_on: str = None,
        notes: str = None,
    ) -> Dict[str, Any]:
        """Create a subtask."""
        data = {"name": name}
        if assignee:
            data["assignee"] = assignee
        if due_on:
            data["due_on"] = due_on
        if notes:
            data["notes"] = notes

        result = self._request("POST", f"tasks/{parent_gid}/subtasks", json_data={"data": data})
        return result.get("data", {})

    def set_parent(
        self,
        task_gid: str,
        parent_gid: str = None,
        insert_before: str = None,
        insert_after: str = None,
    ) -> Dict[str, Any]:
        """
        Set or remove the parent of a task (reparenting).

        Args:
            task_gid: The task to reparent.
            parent_gid: New parent task GID, or None to remove parent.
            insert_before: Position before this sibling subtask (optional).
            insert_after: Position after this sibling subtask (optional).

        Returns:
            The updated task record.

        Note:
            - Only one of insert_before/insert_after can be specified.
            - Subtasks do NOT inherit parent's projects.
            - Maximum 5 levels of subtask nesting.
        """
        data = {"parent": parent_gid}
        if insert_before:
            data["insert_before"] = insert_before
        elif insert_after:
            data["insert_after"] = insert_after

        result = self._request(
            "POST",
            f"tasks/{task_gid}/setParent",
            json_data={"data": data},
        )
        return result.get("data", {})

    # ========== Story/Comment Operations ==========

    def get_stories(self, task_gid: str, limit: int = 50, opt_fields: str = None) -> List[Dict[str, Any]]:
        """Get all stories (comments, activity) for a task."""
        params = {
            "opt_fields": opt_fields or "created_at,created_by.name,text,type,resource_subtype",
            "limit": str(limit),
        }
        result = self._request("GET", f"tasks/{task_gid}/stories", params)
        return result.get("data", [])

    def get_comments(self, task_gid: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get comments on a task (filtered from stories)."""
        stories = self.get_stories(task_gid, limit)
        return [s for s in stories if s.get("resource_subtype") == "comment_added"]

    def add_comment(
        self, task_gid: str, text: str = None, html_text: str = None
    ) -> Dict[str, Any]:
        """Add a comment to a task.

        Args:
            task_gid: The task GID to comment on
            text: Plain text comment
            html_text: Rich text comment in Asana HTML format (takes precedence over text)
        """
        data = {}
        if html_text:
            data["html_text"] = html_text
        elif text:
            data["text"] = text
        else:
            raise ValueError("Either text or html_text must be provided")

        result = self._request(
            "POST", f"tasks/{task_gid}/stories", json_data={"data": data}
        )
        return result.get("data", {})

    # ========== Dependency Operations ==========

    def get_dependencies(self, task_gid: str) -> List[Dict[str, Any]]:
        """Get tasks that this task depends on."""
        result = self._request(
            "GET", f"tasks/{task_gid}/dependencies", {"opt_fields": "name,completed"}
        )
        return result.get("data", [])

    def add_dependency(self, task_gid: str, depends_on_gid: str) -> Dict[str, Any]:
        """Make task depend on another task."""
        result = self._request(
            "POST",
            f"tasks/{task_gid}/addDependencies",
            json_data={"data": {"dependencies": [depends_on_gid]}},
        )
        return result.get("data", {})

    def add_dependencies(self, task_gid: str, depends_on_gids: List[str]) -> Dict[str, Any]:
        """Add multiple dependencies to a task."""
        if not depends_on_gids:
            return {}
        result = self._request(
            "POST",
            f"tasks/{task_gid}/addDependencies",
            json_data={"data": {"dependencies": depends_on_gids}},
        )
        return result.get("data", {})

    def remove_dependency(self, task_gid: str, depends_on_gid: str) -> Dict[str, Any]:
        """Remove a dependency from a task."""
        result = self._request(
            "POST",
            f"tasks/{task_gid}/removeDependencies",
            json_data={"data": {"dependencies": [depends_on_gid]}},
        )
        return result.get("data", {})

    def get_dependents(self, task_gid: str) -> List[Dict[str, Any]]:
        """Get tasks that depend on this task."""
        result = self._request(
            "GET",
            f"tasks/{task_gid}/dependents",
            params={"opt_fields": "name,completed,gid"},
        )
        return result.get("data", [])

    def chain_dependencies(self, task_gids: List[str]) -> int:
        """
        Chain tasks sequentially so each depends on the previous.
        Given [A, B, C, D], creates: B depends on A, C depends on B, D depends on C.
        Returns number of dependencies created.
        """
        if len(task_gids) < 2:
            return 0

        count = 0
        for i in range(1, len(task_gids)):
            self.add_dependency(task_gids[i], task_gids[i - 1])
            count += 1

        return count

    # ========== User Operations ==========

    def get_me(self) -> Dict[str, Any]:
        """Get current user info."""
        result = self._request("GET", "users/me", {"opt_fields": "name,email,workspaces.name"})
        return result.get("data", {})

    # ========== Portfolio Operations ==========

    def get_portfolio(self, portfolio_gid: str, opt_fields: str = None) -> Dict[str, Any]:
        """Get portfolio details."""
        params = {
            "opt_fields": opt_fields or "name,owner.name,color,created_at,current_status_update.status,members.name"
        }
        result = self._request("GET", f"portfolios/{portfolio_gid}", params)
        return result.get("data", {})

    def get_portfolios(
        self,
        workspace: str = None,
        owner: str = "me",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List portfolios in workspace."""
        params = {
            "workspace": self._get_workspace(workspace),
            "owner": owner,
            "opt_fields": "name,owner.name,color",
            "limit": str(limit),
        }
        result = self._request("GET", "portfolios", params)
        return result.get("data", [])

    def get_portfolio_items(self, portfolio_gid: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get items (projects) in a portfolio."""
        params = {
            "opt_fields": "name,resource_type,owner.name,current_status.color,due_on",
            "limit": str(limit),
        }
        result = self._request("GET", f"portfolios/{portfolio_gid}/items", params)
        return result.get("data", [])

    # ========== Team Operations ==========

    def get_teams(self, organization: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List teams in an organization/workspace."""
        ws = self._get_workspace(organization)
        params = {
            "opt_fields": "name,description,organization.name",
            "limit": str(limit),
        }
        result = self._request("GET", f"organizations/{ws}/teams", params)
        return result.get("data", [])

    def get_team(self, team_gid: str, opt_fields: str = None) -> Dict[str, Any]:
        """Get team details."""
        params = {
            "opt_fields": opt_fields or "name,description,organization.name,html_description"
        }
        result = self._request("GET", f"teams/{team_gid}", params)
        return result.get("data", {})

    def get_team_members(self, team_gid: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get members of a team."""
        params = {
            "opt_fields": "name,email",
            "limit": str(limit),
        }
        result = self._request("GET", f"teams/{team_gid}/users", params)
        return result.get("data", [])

    # ========== Tag Operations ==========

    def get_tags(self, workspace: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List tags in workspace."""
        params = {
            "workspace": self._get_workspace(workspace),
            "opt_fields": "name,color,notes",
            "limit": str(limit),
        }
        result = self._request("GET", "tags", params)
        return result.get("data", [])

    def get_tag(self, tag_gid: str) -> Dict[str, Any]:
        """Get tag details."""
        params = {"opt_fields": "name,color,notes,followers.name"}
        result = self._request("GET", f"tags/{tag_gid}", params)
        return result.get("data", {})

    def create_tag(
        self,
        name: str,
        workspace: str = None,
        color: str = None,
        notes: str = None,
    ) -> Dict[str, Any]:
        """Create a new tag."""
        data = {
            "name": name,
            "workspace": self._get_workspace(workspace),
        }
        if color:
            data["color"] = color
        if notes:
            data["notes"] = notes

        result = self._request("POST", "tags", json_data={"data": data})
        return result.get("data", {})

    def update_tag(
        self,
        tag_gid: str,
        name: str = None,
        color: str = None,
        notes: str = None,
    ) -> Dict[str, Any]:
        """Update a tag."""
        data = {}
        if name is not None:
            data["name"] = name
        if color is not None:
            data["color"] = color
        if notes is not None:
            data["notes"] = notes

        if not data:
            raise ValueError("No updates provided")

        result = self._request("PUT", f"tags/{tag_gid}", json_data={"data": data})
        return result.get("data", {})

    def delete_tag(self, tag_gid: str) -> bool:
        """Delete a tag."""
        self._request("DELETE", f"tags/{tag_gid}")
        return True

    def add_tag_to_task(self, task_gid: str, tag_gid: str) -> Dict[str, Any]:
        """Add a tag to a task."""
        result = self._request(
            "POST",
            f"tasks/{task_gid}/addTag",
            json_data={"data": {"tag": tag_gid}},
        )
        return result.get("data", {})

    def remove_tag_from_task(self, task_gid: str, tag_gid: str) -> Dict[str, Any]:
        """Remove a tag from a task."""
        result = self._request(
            "POST",
            f"tasks/{task_gid}/removeTag",
            json_data={"data": {"tag": tag_gid}},
        )
        return result.get("data", {})

    # ========== Section Operations (CRUD) ==========

    def create_section(self, project_gid: str, name: str, insert_before: str = None, insert_after: str = None) -> Dict[str, Any]:
        """Create a section in a project."""
        data = {"name": name}
        if insert_before:
            data["insert_before"] = insert_before
        if insert_after:
            data["insert_after"] = insert_after

        result = self._request(
            "POST",
            f"projects/{project_gid}/sections",
            json_data={"data": data},
        )
        return result.get("data", {})

    def update_section(self, section_gid: str, name: str) -> Dict[str, Any]:
        """Update a section's name."""
        result = self._request(
            "PUT",
            f"sections/{section_gid}",
            json_data={"data": {"name": name}},
        )
        return result.get("data", {})

    def delete_section(self, section_gid: str) -> bool:
        """Delete a section."""
        self._request("DELETE", f"sections/{section_gid}")
        return True

    def move_section(self, project_gid: str, section_gid: str, before_section: str = None, after_section: str = None) -> Dict[str, Any]:
        """Move/reorder a section within a project."""
        data = {"section": section_gid}
        if before_section:
            data["before_section"] = before_section
        if after_section:
            data["after_section"] = after_section

        result = self._request(
            "POST",
            f"projects/{project_gid}/sections/insert",
            json_data={"data": data},
        )
        return result.get("data", {})

    def move_task_to_section(
        self,
        task_gid: str,
        section_gid: str,
        insert_before: str = None,
        insert_after: str = None,
    ) -> Dict[str, Any]:
        """
        Move a task to a section (removes from other sections in the project).

        Args:
            task_gid: The task to move.
            section_gid: The destination section.
            insert_before: Position before this task in section (optional).
            insert_after: Position after this task in section (optional).

        Returns:
            Empty data dict on success.
        """
        data = {"task": task_gid}
        if insert_before:
            data["insert_before"] = insert_before
        elif insert_after:
            data["insert_after"] = insert_after

        result = self._request(
            "POST",
            f"sections/{section_gid}/addTask",
            json_data={"data": data},
        )
        return result.get("data", {})


# ========== CLI ==========

def format_count(count: int, limit: int, label: str = "tasks", total: int = None) -> str:
    """Format result count with limit-reached indicator."""
    if total is not None and count < total:
        return f"\n({count} {label} shown, {total} total)"
    if count >= limit:
        return f"\n({count} {label}, limit reached - use -l to show more)"
    return f"\n({count} {label})"


def format_task(task: dict, verbose: bool = False) -> str:
    """Format task for display."""
    status = "✓" if task.get("completed") else " "
    due = task.get("due_on") or "-"
    name = task.get("name", "Untitled")
    assignee = (task.get("assignee") or {}).get("name", "-")

    line = f"[{status}] {due:<12} {assignee:<15} {name}"

    if verbose:
        gid = task.get("gid", "")
        line = f"{gid:<20} {line}"

    return line


def cmd_workspaces(client: AsanaClient, args):
    """List workspaces."""
    workspaces = client.list_workspaces()
    if args.json:
        print(json.dumps(workspaces, indent=2))
        return

    if args.verbose:
        print(f"{'GID':<20} {'Name':<40} {'Organization'}")
        print("-" * 70)
        for ws in workspaces:
            org = "Yes" if ws.get("is_organization") else "No"
            print(f"{ws['gid']:<20} {ws['name']:<40} {org}")
    else:
        for ws in workspaces:
            print(ws["name"])


def cmd_projects(client: AsanaClient, args):
    """List projects."""
    projects = client.get_projects(archived=args.archived, limit=args.limit)
    if args.json:
        print(json.dumps(projects, indent=2))
        return

    if args.verbose:
        print(f"{'GID':<20} {'Due':<12} {'Project Name'}")
        print("-" * 60)
        for p in projects:
            due = p.get("due_on") or "-"
            print(f"{p['gid']:<20} {due:<12} {p['name']}")
    else:
        for p in projects:
            due = p.get("due_on") or "-"
            print(f"{due:<12} {p['name']}")


def cmd_task(client: AsanaClient, args):
    """Get task details."""
    task = client.get_task(args.task_gid)
    if args.json:
        print(json.dumps(task, indent=2))
        return

    print(f"Task: {task.get('name')}")
    print(f"GID: {args.task_gid}")
    print(f"URL: https://app.asana.com/0/0/{args.task_gid}")
    print(f"Completed: {'Yes' if task.get('completed') else 'No'}")
    print(f"Due: {task.get('due_on') or 'None'}")
    print(f"Assignee: {(task.get('assignee') or {}).get('name', 'Unassigned')}")

    projects = task.get("projects", [])
    if projects:
        print(f"Projects: {', '.join(p['name'] for p in projects)}")

    notes = task.get("notes")
    if notes:
        print(f"\nDescription:\n{notes}")


def cmd_tasks(client: AsanaClient, args):
    """List tasks."""
    total_count = None

    # If assignee is provided without project/section, use it as the primary filter
    if args.assignee and not args.project and not args.section:
        tasks = client.get_tasks(
            assignee=args.assignee,
            completed=False if args.incomplete else None,
            limit=args.limit,
        )
    elif args.assignee:
        # Post-filter by assignee: must paginate to get all tasks first
        all_tasks = client.get_tasks_paginated(
            project=args.project,
            section=args.section,
            completed=False if args.incomplete else None,
        )
        total_count = len(all_tasks)
        assignee_gid = args.assignee
        if assignee_gid == "me":
            assignee_gid = client._request("GET", "users/me", {}).get("data", {}).get("gid")
        tasks = [t for t in all_tasks if t.get("assignee") and t["assignee"].get("gid") == assignee_gid]
    else:
        tasks = client.get_tasks(
            project=args.project,
            section=args.section,
            completed=False if args.incomplete else None,
            limit=args.limit,
        )

    if args.json:
        print(json.dumps(tasks, indent=2))
        return

    for task in tasks:
        print(format_task(task, verbose=args.verbose))

    if args.assignee and total_count is not None:
        print(f"\n({len(tasks)} tasks matching assignee, {total_count} total in project)")
    elif len(tasks) >= args.limit and (args.project or args.section):
        # Limit reached — count total via pagination
        all_tasks = client.get_tasks_paginated(
            project=args.project,
            section=args.section,
            completed=False if args.incomplete else None,
        )
        print(format_count(len(tasks), args.limit, total=len(all_tasks)))
    else:
        print(format_count(len(tasks), args.limit))


def cmd_search(client: AsanaClient, args):
    """Search tasks."""
    # Support both positional query and -t/--text flag
    text = args.text or args.query

    tasks = client.search_tasks(
        text=text,
        workspace=args.workspace,
        assignee=args.assignee,
        projects=args.projects,
        completed=False if args.incomplete else None,
        limit=args.limit,
    )
    if args.json:
        print(json.dumps(tasks, indent=2))
        return

    for task in tasks:
        print(format_task(task, verbose=args.verbose))
    print(format_count(len(tasks), args.limit))


def cmd_my_tasks(client: AsanaClient, args):
    """Get my tasks."""
    tasks = client.get_tasks(
        assignee="me",
        completed=False if args.incomplete else None,
        limit=args.limit,
    )
    if args.json:
        print(json.dumps(tasks, indent=2))
        return

    for task in tasks:
        print(format_task(task, verbose=args.verbose))
    print(format_count(len(tasks), args.limit))


def cmd_create(client: AsanaClient, args):
    """Create task."""
    notes = args.notes
    html_notes = None

    # Support -m "text" as shorthand for -n "text" -m
    if isinstance(args.markdown, str):
        notes = args.markdown
        args.markdown = True

    if args.markdown and notes:
        html_notes = markdown_to_asana_html(notes)
        notes = None

    custom_fields = None
    if args.custom_fields:
        custom_fields = json.loads(args.custom_fields)

    task = client.create_task(
        name=args.name,
        project=args.project,
        assignee=args.assignee,
        due_on=args.due,
        notes=notes,
        html_notes=html_notes,
        custom_fields=custom_fields,
    )
    if args.json:
        print(json.dumps(task, indent=2))
        return

    print(f"Created: {task.get('name')}")
    print(f"GID: {task.get('gid')}")
    print(f"URL: https://app.asana.com/0/0/{task.get('gid')}")


def cmd_update(client: AsanaClient, args):
    """Update task."""
    # Support -m "text" as shorthand for -n "text" -m
    if isinstance(args.markdown, str):
        args.notes = args.markdown
        args.markdown = True

    updates = {}
    if args.name:
        updates["name"] = args.name
    if args.completed is not None:
        updates["completed"] = args.completed.lower() == "true"
    if args.assignee:
        updates["assignee"] = args.assignee
    if args.due:
        updates["due_on"] = args.due
    if args.notes:
        if args.markdown:
            updates["html_notes"] = markdown_to_asana_html(args.notes)
        else:
            updates["notes"] = args.notes
    if args.custom_fields:
        updates["custom_fields"] = json.loads(args.custom_fields)

    task = client.update_task(args.task_gid, **updates)
    if args.json:
        print(json.dumps(task, indent=2))
        return

    print(f"Updated: {task.get('name')}")
    print(f"Completed: {'Yes' if task.get('completed') else 'No'}")


def cmd_comment(client: AsanaClient, args):
    """Add comment."""
    text = args.text
    html_text = None

    if args.markdown:
        html_text = markdown_to_asana_html(text)
        text = None

    story = client.add_comment(args.task_gid, text=text, html_text=html_text)
    if args.json:
        print(json.dumps(story, indent=2))
        return

    print(f"Added comment to task {args.task_gid}")


def cmd_subtasks(client: AsanaClient, args):
    """Get subtasks."""
    subtasks = client.get_subtasks(args.task_gid)
    if args.json:
        print(json.dumps(subtasks, indent=2))
        return

    if not subtasks:
        print("No subtasks")
        return

    for task in subtasks:
        print(format_task(task))


def cmd_sections(client: AsanaClient, args):
    """List project sections."""
    sections = client.get_project_sections(args.project_gid)
    if args.json:
        print(json.dumps(sections, indent=2))
        return

    if args.verbose:
        print(f"{'GID':<20} {'Section Name'}")
        print("-" * 50)
        for s in sections:
            print(f"{s.get('gid', 'N/A'):<20} {s.get('name', 'N/A')}")
    else:
        for s in sections:
            print(s.get("name", "N/A"))


def cmd_custom_fields(client: AsanaClient, args):
    """List custom fields for a project."""
    fields = client.get_custom_field_settings(args.project_gid)
    if args.json:
        print(json.dumps(fields, indent=2))
        return

    for f in fields:
        name = f.get("name", "N/A")
        gid = f.get("gid", "N/A")
        ftype = f.get("type", "unknown")
        print(f"\n{name} ({gid}) [{ftype}]")
        if ftype == "enum":
            for opt in f.get("enum_options", []):
                if opt.get("enabled", True):
                    print(f"  {opt.get('name', 'N/A'):<30} {opt.get('gid', 'N/A')}")


def cmd_stories(client: AsanaClient, args):
    """Get task stories (activity history)."""
    stories = client.get_stories(args.task_gid, limit=args.limit)
    if args.json:
        print(json.dumps(stories, indent=2))
        return

    print(f"Stories for task {args.task_gid}:\n")
    for s in stories:
        stype = s.get("resource_subtype", s.get("type", "unknown"))
        author = (s.get("created_by") or {}).get("name", "System")
        created = s.get("created_at", "")[:10]
        text = s.get("text", "")[:100]

        if stype == "comment_added":
            print(f"[{created}] {author}: {text}")
        elif text:
            print(f"[{created}] ({stype}) {text}")


def cmd_move(client: AsanaClient, args):
    """Move task to section."""
    client.move_task_to_section(
        task_gid=args.task_gid,
        section_gid=args.section,
        insert_before=args.before,
        insert_after=args.after,
    )
    if args.json:
        print(json.dumps({"success": True, "task": args.task_gid, "section": args.section}, indent=2))
        return

    print(f"Moved task {args.task_gid} to section {args.section}")


def cmd_set_parent(client: AsanaClient, args):
    """Set parent of a task (make it a subtask)."""
    task = client.set_parent(
        task_gid=args.task_gid,
        parent_gid=args.parent if args.parent != "none" else None,
        insert_before=args.before,
        insert_after=args.after,
    )
    if args.json:
        print(json.dumps(task, indent=2))
        return

    if args.parent and args.parent != "none":
        print(f"Task {args.task_gid} is now a subtask of {args.parent}")
    else:
        print(f"Task {args.task_gid} is now a standalone task (parent removed)")


def cmd_markdown(client: AsanaClient, args):
    """Preview markdown to Asana HTML conversion."""
    # Get input from argument or stdin
    if args.text:
        text = args.text
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        print("Error: provide markdown text as argument or via stdin", file=sys.stderr)
        sys.exit(1)

    result = markdown_to_asana_html(text)

    if args.unwrap:
        # Remove <body> wrapper
        result = result[6:-7]

    print(result)


# =============================================================================
# Goals Commands (uses asana_sdk)
# =============================================================================


def _get_workspace_gid():
    """Get workspace GID from env or first available."""
    ws = os.environ.get("ASANA_WORKSPACE")
    if ws:
        return ws
    # Fall back to first workspace
    from asana_sdk import get_workspaces
    workspaces = get_workspaces()
    if not workspaces:
        raise AsanaError("No workspaces found")
    return workspaces[0]["gid"]


def cmd_goals(client: AsanaClient, args):
    """List goals in workspace."""
    from asana_sdk import get_goals

    workspace_gid = _get_workspace_gid()
    goals = get_goals(
        workspace_gid=workspace_gid,
        team_gid=args.team,
        time_period_gid=getattr(args, 'time_period', None),
        limit=args.limit,
    )

    if args.json:
        print(json.dumps(goals, indent=2))
        return

    if not goals:
        print("No goals found")
        return

    print(f"{'GID':<20} {'Status':<12} {'Goal Name'}")
    print("-" * 70)
    for g in goals:
        status = g.get("status") or "-"
        name = g.get("name", "Untitled")[:45]
        print(f"{g['gid']:<20} {status:<12} {name}")
    print(format_count(len(goals), args.limit, "goals"))


def cmd_goal(client: AsanaClient, args):
    """Get goal details."""
    from asana_sdk import get_goal

    goal = get_goal(
        args.goal_gid,
        opt_fields=["name", "owner", "status", "due_on", "start_on", "notes",
                    "metric", "workspace", "team", "time_period"]
    )

    if args.json:
        print(json.dumps(goal, indent=2))
        return

    print(f"Goal: {goal.get('name')}")
    print(f"GID: {args.goal_gid}")
    print(f"URL: https://app.asana.com/0/{args.goal_gid}")
    print(f"Status: {goal.get('status') or 'Not set'}")
    print(f"Due: {goal.get('due_on') or 'None'}")
    print(f"Start: {goal.get('start_on') or 'None'}")

    owner = goal.get("owner")
    if owner:
        print(f"Owner: {owner.get('name', owner.get('gid'))}")

    metric = goal.get("metric")
    if metric:
        current = metric.get("current_number_value", 0)
        target = metric.get("target_number_value", 0)
        unit = metric.get("unit", "")
        print(f"Progress: {current}/{target} {unit}")

    notes = goal.get("notes")
    if notes:
        print(f"\nDescription:\n{notes}")


def cmd_create_goal(client: AsanaClient, args):
    """Create a goal."""
    from asana_sdk import create_goal

    workspace_gid = _get_workspace_gid()
    goal_gid = create_goal(
        name=args.name,
        workspace_gid=workspace_gid,
        owner_gid=args.owner,
        due_on=args.due,
        start_on=args.start,
        status=args.status,
        notes=args.notes,
    )

    if args.json:
        print(json.dumps({"gid": goal_gid}, indent=2))
        return

    print(f"Created goal: {args.name}")
    print(f"GID: {goal_gid}")
    print(f"URL: https://app.asana.com/0/{goal_gid}")


def cmd_update_goal(client: AsanaClient, args):
    """Update a goal."""
    from asana_sdk import update_goal

    kwargs = {}
    if args.name:
        kwargs["name"] = args.name
    if args.owner:
        kwargs["owner_gid"] = args.owner
    if args.due:
        kwargs["due_on"] = args.due
    if args.start:
        kwargs["start_on"] = args.start
    if args.status:
        kwargs["status"] = args.status
    if args.notes:
        kwargs["notes"] = args.notes

    if not kwargs:
        print("No updates specified", file=sys.stderr)
        sys.exit(1)

    update_goal(args.goal_gid, **kwargs)

    if args.json:
        print(json.dumps({"updated": True, "gid": args.goal_gid}, indent=2))
        return

    print(f"Updated goal {args.goal_gid}")


def cmd_goal_metric(client: AsanaClient, args):
    """Update goal metric progress."""
    from asana_sdk import update_goal_metric

    result = update_goal_metric(args.goal_gid, current_number_value=args.value)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"Updated goal {args.goal_gid} metric to {args.value}")


def main():
    epilog = """\
Examples:
  asana workspaces              List workspaces
  asana projects                List projects in workspace
  asana sections <project>      List sections in project
  asana tasks -p <project>      List tasks in project
  asana tasks -s <section> -i   Incomplete tasks in section
  asana task <gid>              Get task details
  asana search "query"          Search tasks
  asana my-tasks -i             My incomplete tasks
  asana create "Name" -p <gid>  Create task in project
  asana update <gid> -c true    Mark task complete
  asana comment <gid> "text"    Add comment to task
  asana move <gid> -s <section> Move task to section
  asana set-parent <gid> -p <parent>  Make task a subtask

Environment:
  ASANA_ACCESS_TOKEN   Required. Personal access token.
  ASANA_WORKSPACE      Optional. Default workspace GID.
"""

    parser = argparse.ArgumentParser(
        prog="asana",
        description="Asana CLI - Direct REST API client",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show GIDs in output")

    subparsers = parser.add_subparsers(dest="command", metavar="command")

    # workspaces
    ws = subparsers.add_parser("workspaces", help="List workspaces")
    ws.set_defaults(func=cmd_workspaces)

    # projects
    proj = subparsers.add_parser("projects", help="List projects")
    proj.add_argument("--archived", action="store_true")
    proj.add_argument("-l", "--limit", type=int, default=50)
    proj.set_defaults(func=cmd_projects)

    # task
    task = subparsers.add_parser("task", help="Get task details")
    task.add_argument("task_gid", help="Task GID")
    task.set_defaults(func=cmd_task)

    # tasks
    tasks = subparsers.add_parser("tasks", help="List tasks in project/section")
    tasks.add_argument("-p", "--project", help="Project GID")
    tasks.add_argument("-s", "--section", help="Section GID")
    tasks.add_argument("-a", "--assignee", help="Filter by assignee (GID or 'me')")
    tasks.add_argument("-i", "--incomplete", action="store_true")
    tasks.add_argument("-l", "--limit", type=int, default=100)
    tasks.set_defaults(func=cmd_tasks)

    # search
    search = subparsers.add_parser("search", help="Search tasks")
    search.add_argument("query", nargs="?", help="Search text (or use -t)")
    search.add_argument("-t", "--text", help="Search text")
    search.add_argument("-a", "--assignee", help="Assignee filter (GID or 'me')")
    search.add_argument("-p", "--projects", help="Project GIDs (comma-separated)")
    search.add_argument("-w", "--workspace", help="Workspace GID")
    search.add_argument("-i", "--incomplete", action="store_true")
    search.add_argument("-l", "--limit", type=int, default=50)
    search.set_defaults(func=cmd_search)

    # my-tasks
    my = subparsers.add_parser("my-tasks", help="Get my tasks")
    my.add_argument("-i", "--incomplete", action="store_true")
    my.add_argument("-l", "--limit", type=int, default=50)
    my.set_defaults(func=cmd_my_tasks)

    # create
    create = subparsers.add_parser("create", help="Create task")
    create.add_argument("name", help="Task name")
    create.add_argument("-p", "--project", help="Project GID")
    create.add_argument("-a", "--assignee", help="Assignee (GID or 'me')")
    create.add_argument("-d", "--due", help="Due date (YYYY-MM-DD)")
    create.add_argument("-n", "--notes", help="Description")
    create.add_argument("-m", "--markdown", nargs="?", const=True, default=False,
                        help="Convert notes from markdown to rich text. Optionally pass text: -m \"## body\"")
    create.add_argument("--custom-fields", help='JSON object mapping field GIDs to values, e.g. \'{"12345": "value"}\'')
    create.set_defaults(func=cmd_create)

    # update
    update = subparsers.add_parser("update", help="Update task")
    update.add_argument("task_gid", help="Task GID")
    update.add_argument("--name", help="New name")
    update.add_argument("-c", "--completed", help="true/false")
    update.add_argument("-a", "--assignee", help="Assignee")
    update.add_argument("-d", "--due", help="Due date")
    update.add_argument("-n", "--notes", help="Description/notes")
    update.add_argument("-m", "--markdown", nargs="?", const=True, default=False,
                        help="Convert notes from markdown to rich text. Optionally pass text: -m \"## body\"")
    update.add_argument("--custom-fields", help='JSON object mapping field GIDs to values, e.g. \'{"12345": "value"}\'')
    update.set_defaults(func=cmd_update)

    # comment
    comment = subparsers.add_parser("comment", help="Add comment")
    comment.add_argument("task_gid", help="Task GID")
    comment.add_argument("text", help="Comment text")
    comment.add_argument("-m", "--markdown", action="store_true",
                         help="Interpret text as markdown and convert to rich text")
    comment.set_defaults(func=cmd_comment)

    # subtasks
    subtasks = subparsers.add_parser("subtasks", help="Get subtasks")
    subtasks.add_argument("task_gid", help="Task GID")
    subtasks.set_defaults(func=cmd_subtasks)

    # sections
    sections = subparsers.add_parser("sections", help="List project sections")
    sections.add_argument("project_gid", help="Project GID")
    sections.set_defaults(func=cmd_sections)

    # custom-fields
    cfields = subparsers.add_parser("custom-fields", help="List custom fields for a project")
    cfields.add_argument("project_gid", help="Project GID")
    cfields.set_defaults(func=cmd_custom_fields)

    # stories
    stories = subparsers.add_parser("stories", help="Get task stories (activity)")
    stories.add_argument("task_gid", help="Task GID")
    stories.add_argument("-l", "--limit", type=int, default=50)
    stories.set_defaults(func=cmd_stories)

    # move
    move = subparsers.add_parser("move", help="Move task to section")
    move.add_argument("task_gid", help="Task GID")
    move.add_argument("-s", "--section", required=True, help="Destination section GID")
    move.add_argument("--before", help="Insert before this task GID")
    move.add_argument("--after", help="Insert after this task GID")
    move.set_defaults(func=cmd_move)

    # set-parent
    setparent = subparsers.add_parser("set-parent", help="Set parent of task (make subtask)")
    setparent.add_argument("task_gid", help="Task GID to reparent")
    setparent.add_argument("-p", "--parent", required=True, help="Parent task GID (or 'none' to remove)")
    setparent.add_argument("--before", help="Insert before this sibling subtask GID")
    setparent.add_argument("--after", help="Insert after this sibling subtask GID")
    setparent.set_defaults(func=cmd_set_parent)

    # markdown (preview converter - no client needed)
    markdown = subparsers.add_parser("markdown", help="Preview markdown to Asana HTML conversion")
    markdown.add_argument("text", nargs="?", help="Markdown text (or pipe via stdin)")
    markdown.add_argument("--unwrap", action="store_true", help="Output without <body> wrapper")
    markdown.set_defaults(func=cmd_markdown, no_client=True)

    # goals (uses asana_sdk, not the REST client)
    goals = subparsers.add_parser("goals", help="List goals in workspace")
    goals.add_argument("-t", "--team", help="Filter by team GID")
    goals.add_argument("-p", "--time-period", dest="time_period", help="Filter by time period GID (e.g., Q1 FY26)")
    goals.add_argument("-l", "--limit", type=int, default=50)
    goals.set_defaults(func=cmd_goals, no_client=True)

    # goal
    goal = subparsers.add_parser("goal", help="Get goal details")
    goal.add_argument("goal_gid", help="Goal GID")
    goal.set_defaults(func=cmd_goal, no_client=True)

    # create-goal
    create_goal = subparsers.add_parser("create-goal", help="Create a goal")
    create_goal.add_argument("name", help="Goal name")
    create_goal.add_argument("-o", "--owner", help="Owner user GID")
    create_goal.add_argument("-d", "--due", help="Due date (YYYY-MM-DD)")
    create_goal.add_argument("-s", "--start", help="Start date (YYYY-MM-DD)")
    create_goal.add_argument("--status", choices=["green", "yellow", "red", "achieved", "partial", "missed", "dropped"],
                             help="Goal status (requires metric to be set first)")
    create_goal.add_argument("-n", "--notes", help="Description")
    create_goal.set_defaults(func=cmd_create_goal, no_client=True)

    # update-goal
    update_goal = subparsers.add_parser("update-goal", help="Update a goal")
    update_goal.add_argument("goal_gid", help="Goal GID")
    update_goal.add_argument("--name", help="New name")
    update_goal.add_argument("-o", "--owner", help="Owner user GID")
    update_goal.add_argument("-d", "--due", help="Due date (YYYY-MM-DD)")
    update_goal.add_argument("-s", "--start", help="Start date (YYYY-MM-DD)")
    update_goal.add_argument("--status", choices=["green", "yellow", "red", "achieved", "partial", "missed", "dropped"],
                             help="Goal status (requires metric to be set first)")
    update_goal.add_argument("-n", "--notes", help="Description")
    update_goal.set_defaults(func=cmd_update_goal, no_client=True)

    # goal-metric
    goal_metric = subparsers.add_parser("goal-metric", help="Update goal metric progress")
    goal_metric.add_argument("goal_gid", help="Goal GID")
    goal_metric.add_argument("value", type=float, help="Current metric value")
    goal_metric.set_defaults(func=cmd_goal_metric, no_client=True)

    # help
    help_parser = subparsers.add_parser("help", help="Show help for a command")
    help_parser.add_argument("help_command", nargs="?", help="Command to get help for")

    # Normalize argv: move --json and -v to before the subcommand so they
    # work in any position (e.g. "asana tasks -p X --json" works like
    # "asana --json tasks -p X")
    raw_args = sys.argv[1:]
    global_flags = {"--json", "-v", "--verbose"}
    hoisted = [a for a in raw_args if a in global_flags]
    rest = [a for a in raw_args if a not in global_flags]
    args = parser.parse_args(hoisted + rest)

    # Show help if no command
    if args.command is None:
        parser.print_help()
        sys.exit(0)

    # Handle 'help <command>' by delegating to that command's -h
    if args.command == "help":
        if args.help_command and args.help_command in subparsers.choices:
            subparsers.choices[args.help_command].print_help()
        else:
            parser.print_help()
        sys.exit(0)

    try:
        # Some commands don't need the Asana client
        if getattr(args, "no_client", False):
            args.func(None, args)
        else:
            client = AsanaClient()
            args.func(client, args)
    except AsanaError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
