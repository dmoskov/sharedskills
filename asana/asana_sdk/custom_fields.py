#!/usr/bin/env python3
"""
Asana Custom Field Operations

Functions for managing Asana custom fields, including caching,
enum options, and field value operations.
"""

import logging
from typing import Dict, List, Any, Optional

# Import infrastructure
from .infrastructure import with_api_error_handling

# Import project functions
from .projects import get_project_custom_fields

# Configure logging
logger = logging.getLogger(__name__)


class CustomFieldCache:
    """Cache for custom field GIDs to minimize API calls."""

    def __init__(self):
        self._cache: Dict[
            str, Dict[str, str]
        ] = {}  # project_gid -> {field_name -> gid}

    def get(self, project_gid: str, field_name: str) -> Optional[str]:
        """Get cached custom field GID"""
        return self._cache.get(project_gid, {}).get(field_name)

    def set(self, project_gid: str, field_name: str, gid: str):
        """Set cached custom field GID"""
        if project_gid not in self._cache:
            self._cache[project_gid] = {}
        self._cache[project_gid][field_name] = gid

    def clear(self, project_gid: Optional[str] = None):
        """Clear cache for a project, or entire cache if no project specified"""
        if project_gid:
            self._cache.pop(project_gid, None)
        else:
            self._cache.clear()


# Global cache instance
_custom_field_cache = CustomFieldCache()


def get_custom_field_cache() -> CustomFieldCache:
    """Get the global custom field cache instance."""
    return _custom_field_cache


def preload_custom_fields_cache(project_gid: str) -> Dict[str, Dict[str, str]]:
    """
    Preload all custom field GIDs for a project into the cache.

    This function fetches all custom fields and their enum options in a single
    API call, populating the cache for subsequent use. Call this at the start
    of a task creation phase to avoid repeated API lookups.

    Args:
        project_gid: Asana project GID

    Returns:
        Dictionary with two keys:
        - 'fields': Dict mapping field_name -> field_gid
        - 'enum_options': Dict mapping 'field_name:option_name' -> option_gid

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        # At start of task creation loop
        cache_data = preload_custom_fields_cache('1211710875848660')
        print(f"Cached {len(cache_data['fields'])} fields")

        # Subsequent calls to get_custom_field_gid() will use the cache
        for task in tasks_to_create:
            field_gid = get_custom_field_gid(project_gid, 'Priority')  # Uses cache
    """
    if not project_gid or not isinstance(project_gid, str):
        raise ValueError(f"Invalid project_gid: {project_gid}")

    logger.info(f"Preloading custom fields cache for project {project_gid}")

    # Clear any existing cache for this project to ensure fresh data
    _custom_field_cache.clear(project_gid)

    # Fetch all custom fields with enum options
    fields = get_project_custom_fields(project_gid)

    cached_fields = {}
    cached_enum_options = {}

    for field in fields:
        field_name = field.get("name")
        field_gid = field.get("gid")

        if field_name and field_gid:
            # Cache the field itself
            _custom_field_cache.set(project_gid, field_name, field_gid)
            cached_fields[field_name] = field_gid

            # Cache all enum options for this field
            enum_options = field.get("enum_options", [])
            for option in enum_options:
                option_name = option.get("name")
                option_gid = option.get("gid")

                if option_name and option_gid:
                    cache_key = f"{field_name}:{option_name}"
                    _custom_field_cache.set(project_gid, cache_key, option_gid)
                    cached_enum_options[cache_key] = option_gid

    logger.info(
        f"Preloaded cache: {len(cached_fields)} fields, "
        f"{len(cached_enum_options)} enum options for project {project_gid}"
    )

    return {"fields": cached_fields, "enum_options": cached_enum_options}


@with_api_error_handling("getting custom field GID for {field_name}")
def get_custom_field_gid(
    project_gid: str, field_name: str, use_cache: bool = True
) -> Optional[str]:
    """
    Get the GID of a custom field by name for a project.

    This function caches results per-project to minimize API calls.

    Args:
        project_gid: Asana project GID
        field_name: Name of the custom field (e.g., "Priority", "Project Name")
        use_cache: Whether to use cached values (default: True)

    Returns:
        Custom field GID or None if not found

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        priority_gid = get_custom_field_gid('1234567890', 'Priority')
        if priority_gid:
            print(f"Priority field GID: {priority_gid}")
    """
    if not project_gid or not isinstance(project_gid, str):
        raise ValueError(f"Invalid project_gid: {project_gid}")

    if not field_name or not isinstance(field_name, str):
        raise ValueError(f"Invalid field_name: {field_name}")

    # Check cache first
    if use_cache:
        cached_gid = _custom_field_cache.get(project_gid, field_name)
        if cached_gid:
            return cached_gid

    # Fetch from API
    fields = get_project_custom_fields(project_gid)

    # Find matching field
    for field in fields:
        if field.get("name") == field_name:
            gid = field.get("gid")
            if gid and use_cache:
                _custom_field_cache.set(project_gid, field_name, gid)
            return gid

    return None


def get_enum_option_gid(
    project_gid: str, field_name: str, option_name: str, use_cache: bool = True
) -> Optional[str]:
    """
    Get the GID of an enum option within a custom field.

    Enum custom fields (like Priority, Task Type) have predefined options.
    This function finds the GID of a specific option value.

    Args:
        project_gid: Asana project GID
        field_name: Name of the enum custom field (e.g., "Priority")
        option_name: Name of the option (e.g., "🔴 P0 - Critical")
        use_cache: Whether to use cached values (default: True)

    Returns:
        Enum option GID or None if not found

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        p0_gid = get_enum_option_gid('1234567890', 'Priority', '🔴 P0 - Critical')
        task_fields = {priority_field_gid: p0_gid}
    """
    if not project_gid or not isinstance(project_gid, str):
        raise ValueError(f"Invalid project_gid: {project_gid}")

    if not field_name or not isinstance(field_name, str):
        raise ValueError(f"Invalid field_name: {field_name}")

    if not option_name or not isinstance(option_name, str):
        raise ValueError(f"Invalid option_name: {option_name}")

    # Check cache for the full key
    cache_key = f"{field_name}:{option_name}"
    if use_cache:
        cached_gid = _custom_field_cache.get(project_gid, cache_key)
        if cached_gid:
            return cached_gid

    # Fetch custom fields
    fields = get_project_custom_fields(project_gid)

    # Find matching field and option
    for field in fields:
        if field.get("name") == field_name:
            enum_options = field.get("enum_options", [])
            for option in enum_options:
                if option.get("name") == option_name:
                    gid = option.get("gid")
                    if gid and use_cache:
                        _custom_field_cache.set(project_gid, cache_key, gid)
                    return gid

    return None


def filter_tasks_by_custom_field(
    tasks: List[Dict[str, Any]], field_name: str, value: str
) -> List[Dict[str, Any]]:
    """
    Filter tasks by custom field value.

    This is a client-side filter that matches tasks where the specified
    custom field has the given value.

    Args:
        tasks: List of task dictionaries from Asana
        field_name: Name of the custom field to filter by
        value: Expected value (compared via display_value or text_value)

    Returns:
        List of tasks matching the filter

    Raises:
        ValueError: If inputs are invalid

    Example:
        all_tasks = get_asana_tasks('1234567890')
        scaffold_tasks = filter_tasks_by_custom_field(
            all_tasks,
            'Project Name',
            'claude-code-scaffold'
        )
    """
    if not isinstance(tasks, list):
        raise ValueError(f"tasks must be a list, got {type(tasks)}")

    if not field_name or not isinstance(field_name, str):
        raise ValueError(f"Invalid field_name: {field_name}")

    if not value or not isinstance(value, str):
        raise ValueError(f"Invalid value: {value}")

    filtered = []
    for task in tasks:
        if not isinstance(task, dict):
            continue

        custom_fields = task.get("custom_fields", [])
        if not isinstance(custom_fields, list):
            continue

        for field in custom_fields:
            if not isinstance(field, dict):
                continue

            if field.get("name") == field_name:
                # Check both display_value and text_value
                field_value = field.get("display_value") or field.get("text_value")
                if field_value == value:
                    filtered.append(task)
                    break

    return filtered


def get_task_custom_field_value(task: Dict[str, Any], field_name: str) -> Optional[Any]:
    """
    Get the value of a custom field from a task.

    Args:
        task: Task dictionary from Asana
        field_name: Name of the custom field to retrieve

    Returns:
        Field value (string, dict, list, etc.) or None if not found

    Example:
        priority = get_task_custom_field_value(task, 'Priority')
        project_name = get_task_custom_field_value(task, 'Project Name')
    """
    if not isinstance(task, dict):
        return None

    custom_fields = task.get("custom_fields", [])
    if not isinstance(custom_fields, list):
        return None

    for field in custom_fields:
        if not isinstance(field, dict):
            continue

        if field.get("name") == field_name:
            # Return display_value if available, otherwise try text_value or value
            return (
                field.get("display_value")
                or field.get("text_value")
                or field.get("value")
            )

    return None
