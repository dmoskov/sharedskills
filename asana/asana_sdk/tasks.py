#!/usr/bin/env python3
"""
Asana Task Operations

Core task management functions including CRUD operations, search,
dependencies, stories, and specialized queries.
"""

import logging
import re
from datetime import datetime, timedelta, timezone, date
from typing import Dict, List, Any, Optional

# Import infrastructure
from .infrastructure import (
    get_client,
    with_api_error_handling,
    ASANA_SDK_AVAILABLE,
    asana,
    check_rate_limits,
    record_rate_limit_result,
    handle_api_exception,
    ApiException,
)

# Import error classes
from .errors import AsanaClientError

# Import custom fields operations
from .custom_fields import (
    get_custom_field_gid,
    get_enum_option_gid,
)

# Configure logging
logger = logging.getLogger(__name__)


@with_api_error_handling("fetching tasks from project {project_gid}")
def get_asana_tasks(
    project_gid: str, opt_fields: Optional[List[str]] = None, limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get tasks from an Asana project.

    Args:
        project_gid: Asana project GID
        opt_fields: Optional list of fields to include (default: name, custom_fields)
        limit: Maximum number of tasks to fetch (default: 100)

    Returns:
        List of task dictionaries

    Raises:
        AsanaClientError: If the operation fails
        AsanaRateLimitError: If rate limit is exceeded
        ValueError: If inputs are invalid

    Example:
        tasks = get_asana_tasks('1234567890', opt_fields=['name', 'notes'])
    """
    if not project_gid or not isinstance(project_gid, str):
        raise ValueError(f"Invalid project_gid: {project_gid}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    if opt_fields is None:
        opt_fields = ["name", "custom_fields", "created_at", "completed", "notes"]

    client = get_client()
    tasks_api = asana.TasksApi(client)

    # Fetch tasks with pagination
    tasks = []
    opts = {
        "opt_fields": ",".join(opt_fields),
        "limit": min(limit, 100),  # Asana max is 100 per page
    }

    result = tasks_api.get_tasks_for_project(project_gid, opts)

    for task in result:
        tasks.append(task)
        if len(tasks) >= limit:
            break

    logger.info(f"Fetched {len(tasks)} tasks from project {project_gid}")
    return tasks


@with_api_error_handling("fetching task {task_gid}")
def get_asana_task(
    task_gid: str, opt_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Fetch a single task by GID with optional custom fields.

    Args:
        task_gid: Asana task GID
        opt_fields: Optional list of fields to include (e.g., ['name', 'notes', 'custom_fields'])

    Returns:
        Task dictionary with requested fields

    Raises:
        AsanaClientError: If the task is not found or API call fails
        ValueError: If task_gid is invalid

    Example:
        task = get_asana_task('1234567890', opt_fields=['name', 'custom_fields'])
    """
    if not task_gid or not isinstance(task_gid, str):
        raise ValueError(f"Invalid task_gid: {task_gid}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    client = get_client()
    tasks_api = asana.TasksApi(client)

    opts = {}
    if opt_fields:
        opts["opt_fields"] = ",".join(opt_fields)
    else:
        # Default fields for validation checks
        opts["opt_fields"] = "name,custom_fields"

    result = tasks_api.get_task(task_gid, opts)

    if hasattr(result, "to_dict"):
        return result.to_dict().get("data", result.to_dict())
    return result


@with_api_error_handling("creating task '{name}'")
def create_asana_task(
    name: str,
    project_gid: Optional[str] = None,
    notes: Optional[str] = None,
    custom_fields: Optional[Dict[str, Any]] = None,
    additional_projects: Optional[List[str]] = None,
    parent: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Create a task in Asana, optionally multi-homed to multiple projects.

    Can create either a top-level task (requires project_gid) or a subtask (requires parent).

    Args:
        name: Task name/title
        project_gid: Primary Asana project GID (required unless parent is provided)
        notes: Task description/notes (optional)
        custom_fields: Dictionary of custom field GID to value (optional)
        additional_projects: List of additional project GIDs to multi-home the task to (optional)
        parent: Parent task GID to create this as a subtask (optional, alternative to project_gid)
        **kwargs: Additional task properties (assignee, due_on, etc.)

    Returns:
        GID of the created task

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example (top-level task):
        task_gid = create_asana_task(
            name='Fix bug',
            project_gid='1234567890',
            notes='Description...',
            custom_fields={'field_gid': 'value'},
            additional_projects=['9876543210']  # Multi-home to another project
        )

    Example (subtask):
        subtask_gid = create_asana_task(
            name='Subtask for fix',
            parent='1234567890',
            notes='Description...',
            custom_fields={'field_gid': 'value'}
        )
    """
    if not name or not isinstance(name, str):
        raise ValueError(f"Invalid name: {name}")

    # Either project_gid or parent must be provided
    if not project_gid and not parent:
        raise ValueError("Either project_gid or parent must be provided")

    if project_gid and not isinstance(project_gid, str):
        raise ValueError(f"Invalid project_gid: {project_gid}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    # Defensive sanitization: remove newlines from task name
    # Asana truncates task names at the first newline character
    sanitized_name = name.replace("\n", " ").replace("\r", " ")
    sanitized_name = re.sub(r"\s+", " ", sanitized_name).strip()
    if len(sanitized_name) > 255:
        sanitized_name = sanitized_name[:252] + "..."
    if sanitized_name != name:
        logger.warning(
            f"Task name sanitized (newlines removed): '{name[:50]}...' -> '{sanitized_name[:50]}...'"
        )
        name = sanitized_name

    client = get_client()
    tasks_api = asana.TasksApi(client)

    # Build task data
    task_data = {"name": name}

    # Handle subtask vs top-level task
    if parent:
        # Creating a subtask - use parent, projects are inherited
        task_data["parent"] = parent
        if project_gid:
            # Also add to explicit project(s) if provided
            projects = [project_gid]
            if additional_projects:
                for p in additional_projects:
                    if p and p not in projects:
                        projects.append(p)
            task_data["projects"] = projects
    else:
        # Creating a top-level task - requires project
        projects = [project_gid]
        if additional_projects:
            for p in additional_projects:
                if p and p not in projects:
                    projects.append(p)
        task_data["projects"] = projects

    if notes:
        task_data["notes"] = notes

    if custom_fields:
        task_data["custom_fields"] = custom_fields

    # Add any additional fields from kwargs
    task_data.update(kwargs)

    # Create task (v5.x requires body wrapped in 'data' key)
    body = {"data": task_data}
    result = tasks_api.create_task(body, opts={})

    task_gid = result["gid"]
    if parent:
        logger.info(f"Created subtask '{name}' with GID {task_gid} (parent: {parent})")
    elif "projects" in task_data and len(task_data["projects"]) > 1:
        logger.info(
            f"Created task '{name}' with GID {task_gid} (multi-homed to {len(task_data['projects'])} projects)"
        )
    else:
        logger.info(f"Created task '{name}' with GID {task_gid}")

    return task_gid


@with_api_error_handling("updating task {task_gid}")
def update_asana_task(
    task_gid: str,
    custom_fields: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None,
    name: Optional[str] = None,
    **kwargs,
) -> bool:
    """
    Update a task in Asana.

    Args:
        task_gid: Asana task GID
        custom_fields: Dictionary of custom field GID to value (optional)
        notes: Task description/notes (optional)
        name: Task name/title (optional)
        **kwargs: Additional fields to update

    Returns:
        True if successful

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        update_asana_task(
            task_gid='1234567890',
            custom_fields={'field_gid': 'new_value'}
        )
    """
    if not task_gid or not isinstance(task_gid, str):
        raise ValueError(f"Invalid task_gid: {task_gid}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    client = get_client()
    tasks_api = asana.TasksApi(client)

    # Build update data
    update_data = {}

    if custom_fields:
        update_data["custom_fields"] = custom_fields

    if notes:
        update_data["notes"] = notes

    if name:
        # Sanitize name to remove newlines (Asana truncates at first newline)
        sanitized_name = name.replace("\n", " ").replace("\r", " ")
        sanitized_name = re.sub(r"\s+", " ", sanitized_name).strip()
        if len(sanitized_name) > 255:
            sanitized_name = sanitized_name[:252] + "..."
        if sanitized_name != name:
            logger.warning(
                f"Task name sanitized: '{name[:50]}...' -> '{sanitized_name[:50]}...'"
            )
        update_data["name"] = sanitized_name

    # Add any additional fields from kwargs
    update_data.update(kwargs)

    if not update_data:
        logger.warning(f"No updates provided for task {task_gid}")
        return True

    # Update task (v5.x requires body wrapped in 'data' key)
    # Note: SDK v5 signature is (body, task_gid, opts) - body comes FIRST
    body = {"data": update_data}
    tasks_api.update_task(body, task_gid, opts={})

    logger.info(f"Updated task {task_gid}")
    return True


@with_api_error_handling("deleting task {task_gid}")
def delete_asana_task(task_gid: str) -> bool:
    """
    Delete a task from Asana.

    Args:
        task_gid: Asana task GID to delete

    Returns:
        True if successful

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If task_gid is invalid

    Example:
        delete_asana_task('1234567890')
    """
    if not task_gid or not isinstance(task_gid, str):
        raise ValueError(f"Invalid task_gid: {task_gid}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    client = get_client()
    tasks_api = asana.TasksApi(client)

    # Delete task
    tasks_api.delete_task(task_gid)

    logger.info(f"Deleted task {task_gid}")
    return True


@with_api_error_handling("adding task {task_gid} to project {project_gid}")
def add_task_to_project(task_gid: str, project_gid: str) -> bool:
    """
    Add an existing task to a project (multi-home).

    Args:
        task_gid: Asana task GID
        project_gid: Project GID to add the task to

    Returns:
        True if successful

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        add_task_to_project('1234567890', '9876543210')
    """
    if not task_gid or not isinstance(task_gid, str):
        raise ValueError(f"Invalid task_gid: {task_gid}")
    if not project_gid or not isinstance(project_gid, str):
        raise ValueError(f"Invalid project_gid: {project_gid}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    client = get_client()
    tasks_api = asana.TasksApi(client)

    # Add task to project (body first, then task_gid per SDK signature)
    tasks_api.add_project_for_task({"data": {"project": project_gid}}, task_gid)

    logger.info(f"Added task {task_gid} to project {project_gid}")
    return True


@with_api_error_handling("getting dependencies for task {task_gid}")
def get_task_dependencies(task_gid: str) -> List[Dict[str, Any]]:
    """
    Get the tasks that this task depends on (prerequisites).

    Args:
        task_gid: Asana task GID

    Returns:
        List of dependency task dictionaries with 'gid' and 'name'

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If task_gid is invalid

    Example:
        deps = get_task_dependencies('1234567890')
        for dep in deps:
            print(f"Depends on: {dep['name']}")
    """
    if not task_gid or not isinstance(task_gid, str):
        raise ValueError(f"Invalid task_gid: {task_gid}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    logger.info(f"Getting dependencies for task {task_gid}")

    client = get_client()
    tasks_api = asana.TasksApi(client)

    # Get dependencies
    result = tasks_api.get_dependencies_for_task(task_gid, opts={})

    dependencies = list(result) if result else []
    logger.info(f"Found {len(dependencies)} dependencies for task {task_gid}")
    return dependencies


@with_api_error_handling("removing dependencies from task {task_gid}")
def remove_task_dependencies(task_gid: str, dependency_gids: List[str]) -> bool:
    """
    Remove dependencies from a task.

    Args:
        task_gid: Asana task GID to remove dependencies from
        dependency_gids: List of dependency task GIDs to remove

    Returns:
        True if successful

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        remove_task_dependencies('task_b_gid', ['task_a_gid'])
    """
    if not task_gid or not isinstance(task_gid, str):
        raise ValueError(f"Invalid task_gid: {task_gid}")

    if not dependency_gids:
        logger.warning(f"No dependencies to remove for task {task_gid}")
        return True

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    logger.info(f"Removing {len(dependency_gids)} dependencies from task {task_gid}")

    client = get_client()
    tasks_api = asana.TasksApi(client)

    # Remove dependencies
    body = {"data": {"dependencies": dependency_gids}}
    tasks_api.unlink_dependencies_for_task(body, task_gid, opts={})

    logger.info(f"Removed dependencies from task {task_gid}")
    return True


@with_api_error_handling("adding dependencies to task {task_gid}")
def add_task_dependencies(task_gid: str, dependency_gids: List[str]) -> bool:
    """
    Add dependencies to a task (tasks that must complete before this one).

    Args:
        task_gid: Asana task GID that will be blocked
        dependency_gids: List of task GIDs that must complete first

    Returns:
        True if successful

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        # Task B depends on Task A (A must complete before B can start)
        add_task_dependencies('task_b_gid', ['task_a_gid'])
    """
    if not task_gid or not isinstance(task_gid, str):
        raise ValueError(f"Invalid task_gid: {task_gid}")

    if not dependency_gids:
        logger.warning(f"No dependencies to add for task {task_gid}")
        return True

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    logger.info(f"Adding {len(dependency_gids)} dependencies to task {task_gid}")

    client = get_client()
    tasks_api = asana.TasksApi(client)

    # Add dependencies
    body = {"data": {"dependencies": dependency_gids}}
    tasks_api.add_dependencies_for_task(body, task_gid, opts={})

    logger.info(f"Added dependencies to task {task_gid}")
    return True


@with_api_error_handling("setting parent for task {task_gid}")
def set_task_parent(task_gid: str, parent_gid: str) -> bool:
    """
    Set a task's parent, making it a subtask.

    Args:
        task_gid: Asana task GID to move
        parent_gid: Parent task GID (the task will become a subtask of this)

    Returns:
        True if successful

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        set_task_parent('subtask_gid', 'parent_gid')
    """
    if not task_gid or not isinstance(task_gid, str):
        raise ValueError(f"Invalid task_gid: {task_gid}")

    if not parent_gid or not isinstance(parent_gid, str):
        raise ValueError(f"Invalid parent_gid: {parent_gid}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    logger.info(f"Setting parent of task {task_gid} to {parent_gid}")

    client = get_client()
    tasks_api = asana.TasksApi(client)

    # Set the parent
    body = {"data": {"parent": parent_gid}}
    tasks_api.set_parent_for_task(body, task_gid, opts={})

    logger.info(f"Set parent of task {task_gid} to {parent_gid}")
    return True


@with_api_error_handling("fetching subtasks for task {task_gid}")
def get_subtasks_for_task(
    task_gid: str, opt_fields: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Get all subtasks for a parent task.

    Args:
        task_gid: Parent task GID
        opt_fields: Optional list of fields to include in response

    Returns:
        List of subtask dictionaries, ordered by their position in Asana

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        subtasks = get_subtasks_for_task(
            '1234567890',
            opt_fields=['name', 'completed', 'notes', 'custom_fields']
        )
        for subtask in subtasks:
            print(f"  - {subtask['name']} (completed: {subtask.get('completed')})")
    """
    if not task_gid or not isinstance(task_gid, str):
        raise ValueError(f"Invalid task_gid: {task_gid}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    logger.info(f"Fetching subtasks for task {task_gid}")

    client = get_client()
    tasks_api = asana.TasksApi(client)

    # Build options
    opts = {}
    if opt_fields:
        opts["opt_fields"] = ",".join(opt_fields)

    # Get subtasks - returns generator
    result = tasks_api.get_subtasks_for_task(task_gid, opts)

    # Convert to list
    subtasks = list(result)
    logger.info(f"Found {len(subtasks)} subtasks for task {task_gid}")

    return subtasks


@with_api_error_handling("creating story for task {task_gid}")
def create_task_story(task_gid: str, text: str) -> Dict[str, Any]:
    """
    Add a comment/story to an Asana task.

    Args:
        task_gid: Asana task GID
        text: Comment text to add

    Returns:
        Story data dictionary

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        story = create_task_story(
            task_gid='1234567890',
            text='Task completed successfully'
        )
    """
    if not task_gid:
        raise ValueError("task_gid is required")
    if not text:
        raise ValueError("text is required")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    logger.info(f"Creating story for task {task_gid}")

    client = get_client()
    stories_api = asana.StoriesApi(client)

    # Create story (v5.x requires body wrapped in 'data' key)
    # Note: SDK v5 signature is (body, task_gid, opts) - body comes FIRST
    body = {"data": {"text": text}}
    result = stories_api.create_story_for_task(body, task_gid, opts={})

    logger.info(f"Created story for task {task_gid}")
    return result


@with_api_error_handling("creating status update for project {project_gid}")
def create_project_status_update(
    project_gid: str,
    title: str,
    text: str,
    status_type: str = "on_track",
    html_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a status update for an Asana project.

    Args:
        project_gid: Asana project GID
        title: Status update title (e.g., "Weekly Progress Update")
        text: Status update body text (plain text fallback)
        status_type: One of "on_track", "at_risk", "off_track", "on_hold", "complete"
        html_text: HTML-formatted body text (preferred, renders as rich text)

    Returns:
        Status update data dictionary

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        status = create_project_status_update(
            project_gid='1234567890',
            title='Sprint Review',
            html_text='<strong>Completed</strong> 5 tasks this week...',
            status_type='on_track'
        )
    """
    if not project_gid:
        raise ValueError("project_gid is required")
    if not title:
        raise ValueError("title is required")
    if not text and not html_text:
        raise ValueError("text or html_text is required")

    valid_status_types = ["on_track", "at_risk", "off_track", "on_hold", "complete"]
    if status_type not in valid_status_types:
        raise ValueError(f"status_type must be one of: {valid_status_types}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    logger.info(f"Creating status update for project {project_gid}: {title}")

    client = get_client()
    status_api = asana.StatusUpdatesApi(client)

    # Create status update - prefer html_text for rich formatting
    data = {
        "parent": project_gid,
        "title": title,
        "status_type": status_type,
    }

    if html_text:
        data["html_text"] = html_text
    else:
        data["text"] = text

    body = {"data": data}

    result = status_api.create_status_for_object(body, opts={})

    logger.info(f"Created status update for project {project_gid}")
    return result


@with_api_error_handling("getting stories for task {task_gid}")
def get_task_stories(
    task_gid: str, limit: int = 100, opt_fields: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get stories/comments for an Asana task.

    Args:
        task_gid: Asana task GID
        limit: Max number of stories to return (default: 100)
        opt_fields: Comma-separated list of optional fields to include

    Returns:
        List of story dictionaries with text, author, and timestamp

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        stories = get_task_stories('1234567890')
        for story in stories:
            print(f"{story['created_by']['name']}: {story['text']}")
    """
    if not task_gid:
        raise ValueError("task_gid is required")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    logger.info(f"Fetching stories for task {task_gid}")

    client = get_client()
    stories_api = asana.StoriesApi(client)

    # Default fields to include
    if opt_fields is None:
        opt_fields = "text,created_at,created_by.name,resource_subtype"

    opts = {"limit": min(limit, 100), "opt_fields": opt_fields}

    # Get stories for the task
    result = stories_api.get_stories_for_task(task_gid, opts)

    # Convert to list and filter to only comments (not system events)
    stories = []
    for story in result:
        story_dict = story.to_dict() if hasattr(story, "to_dict") else dict(story)
        # Only include user comments, not system-generated stories
        if story_dict.get("resource_subtype") == "comment_added":
            stories.append(story_dict)

    logger.info(f"Found {len(stories)} comments for task {task_gid}")
    return stories


@with_api_error_handling("deleting story {story_gid}")
def delete_story(story_gid: str) -> bool:
    """
    Delete a story/comment from Asana.

    Args:
        story_gid: Asana story GID to delete

    Returns:
        True if successful

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If story_gid is invalid

    Example:
        delete_story('1234567890')
    """
    if not story_gid or not isinstance(story_gid, str):
        raise ValueError(f"Invalid story_gid: {story_gid}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    client = get_client()
    stories_api = asana.StoriesApi(client)

    # Delete story
    stories_api.delete_story(story_gid)

    logger.info(f"Deleted story {story_gid}")
    return True


@with_api_error_handling("searching tasks in workspace {workspace_gid}")
def search_asana_tasks(
    workspace_gid: str,
    text: Optional[str] = None,
    projects_any: Optional[str] = None,
    **kwargs,
) -> List[Dict[str, Any]]:
    """
    Search for tasks in Asana.

    Args:
        workspace_gid: Asana workspace GID
        text: Text to search for in task name or description (optional)
        projects_any: Comma-separated project GIDs to filter by (optional)
        **kwargs: Additional search parameters

    Returns:
        List of matching task dictionaries

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        tasks = search_asana_tasks(
            workspace_gid='1234567890',
            text='bug fix',
            projects_any='0987654321'
        )
    """
    if not workspace_gid or not isinstance(workspace_gid, str):
        raise ValueError(f"Invalid workspace_gid: {workspace_gid}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    client = get_client()
    tasks_api = asana.TasksApi(client)

    # Build search params
    params = {"workspace": workspace_gid}

    if text:
        params["text"] = text

    if projects_any:
        params["projects.any"] = projects_any

    # Add any additional search parameters
    params.update(kwargs)

    # Search tasks
    result = tasks_api.search_tasks_for_workspace(workspace_gid, params)

    tasks = list(result)
    logger.info(f"Found {len(tasks)} tasks matching search criteria")

    return tasks


def search_tasks(
    workspace_gid: str,
    completed: Optional[bool] = None,
    completed_since: Optional[str] = None,
    opt_fields: Optional[List[str]] = None,
    **kwargs,
) -> List[Dict[str, Any]]:
    """
    Search for tasks in Asana workspace.

    This is a convenience wrapper around search_asana_tasks that provides
    common search parameters for finding completed tasks.

    Args:
        workspace_gid: Asana workspace GID
        completed: Filter for completed tasks (True/False)
        completed_since: ISO datetime string - tasks completed after this time
        opt_fields: List of fields to include in results
        **kwargs: Additional search parameters

    Returns:
        List of matching task dictionaries

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        # Find all tasks completed in the last hour
        tasks = search_tasks(
            workspace_gid='1234567890',
            completed=True,
            completed_since=(datetime.now() - timedelta(hours=1)).isoformat()
        )
    """
    search_params = {}

    if completed is not None:
        search_params["completed"] = completed

    if completed_since:
        search_params["completed_since"] = completed_since

    if opt_fields:
        search_params["opt_fields"] = ",".join(opt_fields)

    # Add any additional kwargs
    search_params.update(kwargs)

    return search_asana_tasks(workspace_gid, **search_params)


# ============================================================================
# TaskTemplate Class
# ============================================================================


class TaskTemplate:
    """
    Fluent API for building Asana task structures.

    This class provides a chainable interface for creating tasks with
    custom fields, dependencies, and other properties. It handles type
    validation for custom fields and provides sensible defaults.

    Example:
        template = (TaskTemplate()
            .with_name('[P0] Fix critical bug')
            .with_project('1234567890')
            .with_notes('Description of the bug...')
            .with_custom_field_text('Project Name', 'my-project')
            .with_custom_field_enum('Priority', 'P0 - Critical')
            .with_assignee('me'))

        task_data = template.to_dict()
        task_gid = create_asana_task(**task_data)
    """

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._custom_fields: Dict[str, Any] = {}
        self._project_gid: Optional[str] = None

    def with_name(self, name: str) -> "TaskTemplate":
        """Set task name/title"""
        if not name or not isinstance(name, str):
            raise ValueError(f"Invalid name: {name}")
        self._data["name"] = name
        return self

    def with_project(self, project_gid: str) -> "TaskTemplate":
        """Set project GID"""
        if not project_gid or not isinstance(project_gid, str):
            raise ValueError(f"Invalid project_gid: {project_gid}")
        self._data["project_gid"] = project_gid
        self._project_gid = project_gid
        return self

    def with_notes(self, notes: str) -> "TaskTemplate":
        """Set task description/notes"""
        if notes is not None and not isinstance(notes, str):
            raise ValueError(f"Invalid notes type: {type(notes)}")
        if notes:
            self._data["notes"] = notes
        return self

    def with_assignee(self, assignee: str) -> "TaskTemplate":
        """Set task assignee (email or GID)"""
        if assignee is not None and not isinstance(assignee, str):
            raise ValueError(f"Invalid assignee: {assignee}")
        if assignee:
            self._data["assignee"] = assignee
        return self

    def with_due_date(self, due_date: str) -> "TaskTemplate":
        """
        Set due date (ISO format: YYYY-MM-DD).

        Args:
            due_date: Date string in ISO format

        Example:
            template.with_due_date('2025-01-20')
        """
        if due_date is not None and not isinstance(due_date, str):
            raise ValueError(f"Invalid due_date: {due_date}")
        if due_date:
            self._data["due_on"] = due_date
        return self

    def with_custom_field_text(self, field_name: str, value: str) -> "TaskTemplate":
        """
        Set a text custom field value.

        Args:
            field_name: Name of the custom field
            value: Text value to set

        Example:
            template.with_custom_field_text('Project Name', 'my-project')
        """
        if not self._project_gid:
            raise ValueError("Must call with_project() before setting custom fields")

        field_gid = get_custom_field_gid(self._project_gid, field_name)
        if not field_gid:
            raise ValueError(
                f"Custom field '{field_name}' not found in project {self._project_gid}"
            )

        self._custom_fields[field_gid] = value
        return self

    def with_custom_field_enum(
        self, field_name: str, option_name: str
    ) -> "TaskTemplate":
        """
        Set an enum custom field value.

        Args:
            field_name: Name of the enum custom field
            option_name: Name of the option to select

        Example:
            template.with_custom_field_enum('Priority', 'P0 - Critical')
        """
        if not self._project_gid:
            raise ValueError("Must call with_project() before setting custom fields")

        field_gid = get_custom_field_gid(self._project_gid, field_name)
        if not field_gid:
            raise ValueError(
                f"Custom field '{field_name}' not found in project {self._project_gid}"
            )

        option_gid = get_enum_option_gid(self._project_gid, field_name, option_name)
        if not option_gid:
            raise ValueError(
                f"Enum option '{option_name}' not found for field '{field_name}' "
                f"in project {self._project_gid}"
            )

        self._custom_fields[field_gid] = option_gid
        return self

    def with_custom_field_multi_enum(
        self, field_name: str, option_names: List[str]
    ) -> "TaskTemplate":
        """
        Set a multi-enum custom field value.

        Args:
            field_name: Name of the multi-enum custom field
            option_names: List of option names to select

        Example:
            template.with_custom_field_multi_enum(
                'Tags',
                ['frontend', 'backend']
            )
        """
        if not self._project_gid:
            raise ValueError("Must call with_project() before setting custom fields")

        field_gid = get_custom_field_gid(self._project_gid, field_name)
        if not field_gid:
            raise ValueError(
                f"Custom field '{field_name}' not found in project {self._project_gid}"
            )

        option_gids = []
        for option_name in option_names:
            option_gid = get_enum_option_gid(self._project_gid, field_name, option_name)
            if not option_gid:
                raise ValueError(
                    f"Enum option '{option_name}' not found for field '{field_name}' "
                    f"in project {self._project_gid}"
                )
            option_gids.append(option_gid)

        self._custom_fields[field_gid] = option_gids
        return self

    def with_custom_field_date(
        self, field_name: str, date_value: str
    ) -> "TaskTemplate":
        """
        Set a date custom field value.

        Args:
            field_name: Name of the date custom field
            date_value: Date string in ISO format (YYYY-MM-DD)

        Example:
            template.with_custom_field_date('Target Date', '2025-01-17')
        """
        if not self._project_gid:
            raise ValueError("Must call with_project() before setting custom fields")

        field_gid = get_custom_field_gid(self._project_gid, field_name)
        if not field_gid:
            raise ValueError(
                f"Custom field '{field_name}' not found in project {self._project_gid}"
            )

        self._custom_fields[field_gid] = date_value
        return self

    def with_custom_field_raw(self, field_gid: str, value: Any) -> "TaskTemplate":
        """
        Set a custom field value directly by GID.

        Use this when you already have the field GID and want to skip validation.

        Args:
            field_gid: Custom field GID
            value: Value to set (type depends on field type)

        Example:
            template.with_custom_field_raw('1234567890', 'value')
        """
        self._custom_fields[field_gid] = value
        return self

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert template to dictionary ready for create_asana_task().

        Returns:
            Dictionary with task properties

        Raises:
            ValueError: If required fields are missing

        Example:
            task_data = template.to_dict()
            task_gid = create_asana_task(**task_data)
        """
        if "name" not in self._data:
            raise ValueError("Task name is required (use with_name())")

        if "project_gid" not in self._data:
            raise ValueError("Project GID is required (use with_project())")

        result = self._data.copy()

        if self._custom_fields:
            result["custom_fields"] = self._custom_fields

        return result


# ============================================================================
# Common Search Patterns
# ============================================================================


def search_tasks_by_assignee(
    assignee: str,
    workspace_gid: str,
    project_gid: Optional[str] = None,
    opt_fields: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Search for tasks assigned to a specific user.

    Args:
        assignee: Assignee email or GID
        workspace_gid: Asana workspace GID
        project_gid: Optional project GID to filter by
        opt_fields: Optional list of fields to include

    Returns:
        List of tasks assigned to the user

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        my_tasks = search_tasks_by_assignee(
            'user@example.com',
            workspace_gid='1234567890'
        )
    """
    if not assignee or not isinstance(assignee, str):
        raise ValueError(f"Invalid assignee: {assignee}")

    if not workspace_gid or not isinstance(workspace_gid, str):
        raise ValueError(f"Invalid workspace_gid: {workspace_gid}")

    if opt_fields is None:
        opt_fields = ["name", "custom_fields", "due_on", "completed"]

    # Build search parameters
    search_params = {"assignee.any": assignee, "opt_fields": ",".join(opt_fields)}

    if project_gid:
        search_params["projects.any"] = project_gid

    return search_asana_tasks(workspace_gid, **search_params)


def get_overdue_tasks(
    project_gid: str, opt_fields: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Get overdue tasks from a project.

    A task is overdue if it has a due date in the past and is not completed.

    Args:
        project_gid: Asana project GID
        opt_fields: Optional list of fields to include

    Returns:
        List of overdue tasks

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        overdue = get_overdue_tasks('1234567890')
        print(f"Found {len(overdue)} overdue tasks")
    """
    if opt_fields is None:
        opt_fields = ["name", "due_on", "completed", "assignee.name"]

    # Ensure due_on and completed are included
    if "due_on" not in opt_fields:
        opt_fields.append("due_on")
    if "completed" not in opt_fields:
        opt_fields.append("completed")

    all_tasks = get_asana_tasks(project_gid, opt_fields=opt_fields, limit=500)

    today = date.today()
    overdue = []

    for task in all_tasks:
        if task.get("completed"):
            continue

        due_on = task.get("due_on")
        if not due_on:
            continue

        try:
            due_date = date.fromisoformat(due_on)
            if due_date < today:
                overdue.append(task)
        except (ValueError, TypeError):
            # Invalid date format, skip
            continue

    return overdue


def get_recently_completed_tasks(
    project_gid: str, days: int = 7, opt_fields: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Get tasks completed within the last N days.

    Args:
        project_gid: Asana project GID
        days: Number of days to look back (default: 7)
        opt_fields: Optional list of fields to include

    Returns:
        List of recently completed tasks

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        recent = get_recently_completed_tasks('1234567890', days=14)
        print(f"Completed {len(recent)} tasks in last 2 weeks")
    """
    if not isinstance(days, int) or days <= 0:
        raise ValueError(f"Invalid days: {days}")

    if opt_fields is None:
        opt_fields = ["name", "completed", "completed_at", "assignee.name"]

    # Ensure completed fields are included
    if "completed" not in opt_fields:
        opt_fields.append("completed")
    if "completed_at" not in opt_fields:
        opt_fields.append("completed_at")

    all_tasks = get_asana_tasks(project_gid, opt_fields=opt_fields, limit=500)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = []

    for task in all_tasks:
        if not task.get("completed"):
            continue

        completed_at = task.get("completed_at")
        if not completed_at:
            continue

        try:
            completed_date = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            if completed_date >= cutoff:
                recent.append(task)
        except (ValueError, TypeError):
            # Invalid date format, skip
            continue

    return recent
