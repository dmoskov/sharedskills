#!/usr/bin/env python3
"""
Asana SDK - Python client for Asana API

A decoupled, reusable SDK for interacting with the Asana API.
Supports OAuth token management, rate limiting hooks, and pluggable alerts.

Usage:
    from asana_sdk import (
        # Configuration
        get_config,

        # Workspace/User operations
        get_workspaces,
        get_workspace_by_name,

        # Project operations
        get_project,
        get_project_custom_fields,

        # Task operations
        get_asana_tasks,
        get_asana_task,
        create_asana_task,
        update_asana_task,
        delete_asana_task,
        search_asana_tasks,

        # Custom fields
        get_custom_field_gid,
        get_enum_option_gid,
        preload_custom_fields_cache,

        # Attachments
        upload_attachment_to_task,
        get_task_attachments,
        download_attachment,
    )

Configuration:
    # Set up alert callback for critical issues
    from asana_sdk import get_config

    config = get_config()
    config.set_alert_callback(my_alert_handler)
    config.set_rate_limit_hooks(check_fn, record_fn)
"""

# Error classes
from .errors import (
    AsanaClientError,
    AsanaAuthenticationError,
    AsanaRateLimitError,
    AsanaNotFoundError,
    AsanaValidationError,
    AsanaServerError,
)

# Infrastructure
from .infrastructure import (
    get_config,
    AsanaSDKConfig,
    get_client,
    ASANA_SDK_AVAILABLE,
    raise_alert,
    with_api_error_handling,
)

# Token management
from .token_manager import (
    TokenManager,
    DEFAULT_TOKEN_FILE,
)

# User/Workspace operations
from .users import (
    get_workspaces,
    get_workspace_by_name,
)

# Project operations
from .projects import (
    get_project,
    get_project_custom_fields,
)

# Custom fields
from .custom_fields import (
    CustomFieldCache,
    get_custom_field_cache,
    preload_custom_fields_cache,
    get_custom_field_gid,
    get_enum_option_gid,
    filter_tasks_by_custom_field,
    get_task_custom_field_value,
)

# Task operations
from .tasks import (
    get_asana_tasks,
    get_asana_task,
    create_asana_task,
    update_asana_task,
    delete_asana_task,
    add_task_to_project,
    get_task_dependencies,
    remove_task_dependencies,
    add_task_dependencies,
    set_task_parent,
    get_subtasks_for_task,
    create_task_story,
    create_project_status_update,
    get_task_stories,
    delete_story,
    search_asana_tasks,
    search_tasks,
    TaskTemplate,
    search_tasks_by_assignee,
    get_overdue_tasks,
    get_recently_completed_tasks,
)

# Attachment operations
from .attachments import (
    upload_attachment_to_task,
    get_task_attachments,
    get_attachment,
    download_attachment,
    delete_attachment,
)

# Goal operations
from .goals import (
    get_goals,
    get_goal,
    create_goal,
    update_goal,
    delete_goal,
    update_goal_metric,
    create_goal_metric,
    add_goal_followers,
    remove_goal_followers,
    get_parent_goals,
)

__all__ = [
    # Errors
    "AsanaClientError",
    "AsanaAuthenticationError",
    "AsanaRateLimitError",
    "AsanaNotFoundError",
    "AsanaValidationError",
    "AsanaServerError",
    # Infrastructure
    "get_config",
    "AsanaSDKConfig",
    "get_client",
    "ASANA_SDK_AVAILABLE",
    "raise_alert",
    "with_api_error_handling",
    # Token management
    "TokenManager",
    "DEFAULT_TOKEN_FILE",
    # Users/Workspaces
    "get_workspaces",
    "get_workspace_by_name",
    # Projects
    "get_project",
    "get_project_custom_fields",
    # Custom fields
    "CustomFieldCache",
    "get_custom_field_cache",
    "preload_custom_fields_cache",
    "get_custom_field_gid",
    "get_enum_option_gid",
    "filter_tasks_by_custom_field",
    "get_task_custom_field_value",
    # Tasks
    "get_asana_tasks",
    "get_asana_task",
    "create_asana_task",
    "update_asana_task",
    "delete_asana_task",
    "add_task_to_project",
    "get_task_dependencies",
    "remove_task_dependencies",
    "add_task_dependencies",
    "set_task_parent",
    "get_subtasks_for_task",
    "create_task_story",
    "create_project_status_update",
    "get_task_stories",
    "delete_story",
    "search_asana_tasks",
    "search_tasks",
    "TaskTemplate",
    "search_tasks_by_assignee",
    "get_overdue_tasks",
    "get_recently_completed_tasks",
    # Attachments
    "upload_attachment_to_task",
    "get_task_attachments",
    "get_attachment",
    "download_attachment",
    "delete_attachment",
    # Goals
    "get_goals",
    "get_goal",
    "create_goal",
    "update_goal",
    "delete_goal",
    "update_goal_metric",
    "create_goal_metric",
    "add_goal_followers",
    "remove_goal_followers",
    "get_parent_goals",
]

__version__ = "1.0.0"
