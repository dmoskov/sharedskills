#!/usr/bin/env python3
"""
Asana Project Operations

Functions for managing Asana projects and project-level operations.
"""

import logging
from typing import Dict, List, Any

# Import infrastructure
from .infrastructure import (
    get_client,
    with_api_error_handling,
    ASANA_SDK_AVAILABLE,
    asana,
)

# Import error classes
from .errors import AsanaClientError

# Configure logging
logger = logging.getLogger(__name__)


@with_api_error_handling("getting project {project_gid}")
def get_project(project_gid: str) -> Dict[str, Any]:
    """
    Get project information by GID.

    Args:
        project_gid: Asana project GID

    Returns:
        Project dictionary with gid, name, notes, etc.

    Raises:
        AsanaClientError: If the operation fails
        AsanaNotFoundError: If project not found
        ValueError: If inputs are invalid

    Example:
        project = get_project('1234567890')
        print(f"Project: {project['name']}")
        print(f"Description: {project.get('notes', '')}")
    """
    if not project_gid or not isinstance(project_gid, str):
        raise ValueError(f"Invalid project_gid: {project_gid}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    client = get_client()
    projects_api = asana.ProjectsApi(client)

    # Get project with common fields
    opts = {"opt_fields": "name,gid,notes,owner.name,created_at,modified_at"}
    result = projects_api.get_project(project_gid, opts=opts)

    project = dict(result)
    logger.info(f"Retrieved project: {project.get('name')} ({project_gid})")
    return project


@with_api_error_handling("getting custom fields for project {project_gid}")
def get_project_custom_fields(project_gid: str) -> List[Dict[str, Any]]:
    """
    Get all custom fields for a project.

    Args:
        project_gid: Asana project GID

    Returns:
        List of custom field definitions

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        fields = get_project_custom_fields('1234567890')
        for field in fields:
            print(f"{field['name']}: {field['gid']} ({field['resource_subtype']})")
    """
    if not project_gid or not isinstance(project_gid, str):
        raise ValueError(f"Invalid project_gid: {project_gid}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    client = get_client()
    projects_api = asana.ProjectsApi(client)

    # Get project with custom fields
    opts = {
        "opt_fields": "custom_field_settings.custom_field.name,"
        "custom_field_settings.custom_field.gid,"
        "custom_field_settings.custom_field.resource_subtype,"
        "custom_field_settings.custom_field.enum_options.gid,"
        "custom_field_settings.custom_field.enum_options.name"
    }

    project = projects_api.get_project(project_gid, opts)

    custom_field_settings = project.get("custom_field_settings", [])

    # Extract custom fields from settings
    custom_fields = []
    for setting in custom_field_settings:
        cf = setting.get("custom_field")
        if cf:
            custom_fields.append(cf)

    logger.info(
        f"Retrieved {len(custom_fields)} custom fields for project {project_gid}"
    )
    return custom_fields
