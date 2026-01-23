#!/usr/bin/env python3
"""
Asana User and Workspace Operations

Functions for managing Asana users and workspaces.
"""

import logging
from typing import Dict, List, Any, Optional

# Import infrastructure
from .infrastructure import (
    get_client,
    ASANA_SDK_AVAILABLE,
    asana,
    with_api_error_handling,
)

# Import error classes
from .errors import AsanaClientError

# Configure logging
logger = logging.getLogger(__name__)


@with_api_error_handling("getting workspaces")
def get_workspaces() -> List[Dict[str, Any]]:
    """
    Get all workspaces accessible by the authenticated user.

    Returns:
        List of workspace dictionaries with gid, name, etc.

    Raises:
        AsanaClientError: If the operation fails

    Example:
        workspaces = get_workspaces()
        for ws in workspaces:
            print(f"{ws['name']}: {ws['gid']}")
    """
    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    client = get_client()
    workspaces_api = asana.WorkspacesApi(client)

    # Get all workspaces
    opts = {"opt_fields": "name,gid"}
    result = workspaces_api.get_workspaces(opts=opts)

    # Convert to list of dicts
    workspaces = [dict(ws) for ws in result]
    logger.info(f"Retrieved {len(workspaces)} workspaces")
    return workspaces


def get_workspace_by_name(workspace_name: Optional[str] = None) -> str:
    """
    Get workspace GID by name, or return the first workspace if no name specified.

    This is a centralized helper to avoid duplicate workspace lookup code across scripts.
    Most users have only one workspace, so defaulting to the first workspace is safe.

    Args:
        workspace_name: Optional workspace name to search for. If None, returns first workspace.

    Returns:
        Workspace GID as string

    Raises:
        AsanaClientError: If no workspaces found or workspace name not found
        ValueError: If inputs are invalid

    Example:
        # Get first workspace (most common case)
        workspace_gid = get_workspace_by_name()

        # Get specific workspace by name
        workspace_gid = get_workspace_by_name('My Workspace')
    """
    workspaces = get_workspaces()

    if not workspaces:
        raise AsanaClientError(
            "No workspaces found. Verify your Asana account has access to at least one workspace."
        )

    # If no name specified, return first workspace
    if workspace_name is None:
        ws = workspaces[0]
        logger.info(f"Using first workspace: {ws['name']} (GID: {ws['gid']})")
        return ws["gid"]

    # Search for workspace by name
    workspace_name_lower = workspace_name.lower()
    for ws in workspaces:
        if ws["name"].lower() == workspace_name_lower:
            logger.info(f"Found workspace: {ws['name']} (GID: {ws['gid']})")
            return ws["gid"]

    # Not found - provide helpful error with available workspaces
    available = ", ".join(f"'{ws['name']}'" for ws in workspaces)
    raise AsanaClientError(
        f"Workspace '{workspace_name}' not found. Available workspaces: {available}"
    )
