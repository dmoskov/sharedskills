#!/usr/bin/env python3
"""
Asana Goals Operations

CRUD operations for Asana Goals including metrics and followers.
"""

import logging
from typing import Dict, List, Any, Optional

from .infrastructure import (
    get_client,
    with_api_error_handling,
    ASANA_SDK_AVAILABLE,
    asana,
)
from .errors import AsanaClientError

logger = logging.getLogger(__name__)

# Valid status values for goals (Asana API values)
VALID_GOAL_STATUSES = ["achieved", "dropped", "green", "missed", "partial", "red", "yellow"]

# Valid metric types
VALID_METRIC_TYPES = ["number", "percentage", "currency"]

# Valid metric unit types (Asana API values)
VALID_METRIC_UNITS = ["currency", "none", "percentage"]


@with_api_error_handling("fetching goals for workspace {workspace_gid}")
def get_goals(
    workspace_gid: str,
    team_gid: Optional[str] = None,
    time_period_gid: Optional[str] = None,
    opt_fields: Optional[List[str]] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Get goals from a workspace.

    Args:
        workspace_gid: Workspace GID to fetch goals from
        team_gid: Optional team GID to filter by
        time_period_gid: Optional time period GID to filter by
        opt_fields: Optional list of fields to include
        limit: Maximum number of goals to return (default: 100)

    Returns:
        List of goal dictionaries

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If workspace_gid is invalid

    Example:
        goals = get_goals('workspace123', team_gid='team456')
    """
    if not workspace_gid or not isinstance(workspace_gid, str):
        raise ValueError(f"Invalid workspace_gid: {workspace_gid}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    client = get_client()
    goals_api = asana.GoalsApi(client)

    # Build opts
    opts = {"workspace": workspace_gid, "limit": min(limit, 100)}

    if team_gid:
        opts["team"] = team_gid

    if time_period_gid:
        opts["time_periods"] = time_period_gid

    if opt_fields:
        opts["opt_fields"] = ",".join(opt_fields)

    result = goals_api.get_goals(opts)

    goals = list(result) if result else []
    logger.info(f"Fetched {len(goals)} goals from workspace {workspace_gid}")
    return goals


@with_api_error_handling("fetching goal {goal_gid}")
def get_goal(
    goal_gid: str,
    opt_fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Get a single goal by GID.

    Args:
        goal_gid: Goal GID to fetch
        opt_fields: Optional list of fields to include

    Returns:
        Goal dictionary

    Raises:
        AsanaClientError: If the operation fails
        AsanaNotFoundError: If goal is not found
        ValueError: If goal_gid is invalid

    Example:
        goal = get_goal('goal123')
        print(f"Status: {goal['status']}")
    """
    if not goal_gid or not isinstance(goal_gid, str):
        raise ValueError(f"Invalid goal_gid: {goal_gid}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    client = get_client()
    goals_api = asana.GoalsApi(client)

    opts = {}
    if opt_fields:
        opts["opt_fields"] = ",".join(opt_fields)

    result = goals_api.get_goal(goal_gid, opts)

    if hasattr(result, "to_dict"):
        return result.to_dict()
    return result


@with_api_error_handling("creating goal '{name}'")
def create_goal(
    name: str,
    workspace_gid: str,
    owner_gid: Optional[str] = None,
    due_on: Optional[str] = None,
    start_on: Optional[str] = None,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    html_notes: Optional[str] = None,
    time_period_gid: Optional[str] = None,
    team_gid: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Create a goal in Asana.

    Args:
        name: Goal name/title
        workspace_gid: Workspace GID where goal will be created
        owner_gid: Optional user GID for goal owner
        due_on: Optional due date (YYYY-MM-DD format)
        start_on: Optional start date (YYYY-MM-DD format)
        status: Optional status ('on_track', 'at_risk', 'off_track', 'on_hold')
        notes: Optional plain text description
        html_notes: Optional HTML description
        time_period_gid: Optional time period GID (Q1, Q2, etc.)
        team_gid: Optional team GID (for team-level goals)
        **kwargs: Additional goal properties

    Returns:
        GID of the created goal

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        goal_gid = create_goal(
            name='Q1 Revenue Target',
            workspace_gid='ws123',
            owner_gid='user456',
            due_on='2026-03-31',
            status='on_track'
        )
    """
    if not name or not isinstance(name, str):
        raise ValueError(f"Invalid name: {name}")

    if not workspace_gid or not isinstance(workspace_gid, str):
        raise ValueError(f"Invalid workspace_gid: {workspace_gid}")

    if status and status not in VALID_GOAL_STATUSES:
        raise ValueError(
            f"Invalid status: {status}. Must be one of: {VALID_GOAL_STATUSES}"
        )

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    client = get_client()
    goals_api = asana.GoalsApi(client)

    # Build goal data
    goal_data = {
        "name": name,
        "workspace": workspace_gid,
    }

    if owner_gid:
        goal_data["owner"] = owner_gid

    if due_on:
        goal_data["due_on"] = due_on

    if start_on:
        goal_data["start_on"] = start_on

    if status:
        goal_data["status"] = status

    if notes:
        goal_data["notes"] = notes

    if html_notes:
        goal_data["html_notes"] = html_notes

    if time_period_gid:
        goal_data["time_period"] = time_period_gid

    if team_gid:
        goal_data["team"] = team_gid

    # Add any additional kwargs
    goal_data.update(kwargs)

    body = {"data": goal_data}
    result = goals_api.create_goal(body, opts={})

    goal_gid = result["gid"]
    logger.info(f"Created goal '{name}' with GID {goal_gid}")
    return goal_gid


@with_api_error_handling("updating goal {goal_gid}")
def update_goal(
    goal_gid: str,
    name: Optional[str] = None,
    owner_gid: Optional[str] = None,
    due_on: Optional[str] = None,
    start_on: Optional[str] = None,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    html_notes: Optional[str] = None,
    **kwargs,
) -> bool:
    """
    Update a goal in Asana.

    Args:
        goal_gid: Goal GID to update
        name: Optional new name
        owner_gid: Optional new owner user GID
        due_on: Optional new due date (YYYY-MM-DD)
        start_on: Optional new start date (YYYY-MM-DD)
        status: Optional new status ('on_track', 'at_risk', 'off_track', 'on_hold')
        notes: Optional new plain text description
        html_notes: Optional new HTML description
        **kwargs: Additional fields to update

    Returns:
        True if successful

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        update_goal('goal123', status='at_risk', notes='Falling behind schedule')
    """
    if not goal_gid or not isinstance(goal_gid, str):
        raise ValueError(f"Invalid goal_gid: {goal_gid}")

    if status and status not in VALID_GOAL_STATUSES:
        raise ValueError(
            f"Invalid status: {status}. Must be one of: {VALID_GOAL_STATUSES}"
        )

    # Build update data
    update_data = {}

    if name:
        update_data["name"] = name

    if owner_gid:
        update_data["owner"] = owner_gid

    if due_on:
        update_data["due_on"] = due_on

    if start_on:
        update_data["start_on"] = start_on

    if status:
        update_data["status"] = status

    if notes:
        update_data["notes"] = notes

    if html_notes:
        update_data["html_notes"] = html_notes

    update_data.update(kwargs)

    if not update_data:
        logger.warning(f"No updates provided for goal {goal_gid}")
        return True

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    client = get_client()
    goals_api = asana.GoalsApi(client)

    body = {"data": update_data}
    goals_api.update_goal(body, goal_gid, opts={})

    logger.info(f"Updated goal {goal_gid}")
    return True


@with_api_error_handling("deleting goal {goal_gid}")
def delete_goal(goal_gid: str) -> bool:
    """
    Delete a goal from Asana.

    Args:
        goal_gid: Goal GID to delete

    Returns:
        True if successful

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If goal_gid is invalid

    Example:
        delete_goal('goal123')
    """
    if not goal_gid or not isinstance(goal_gid, str):
        raise ValueError(f"Invalid goal_gid: {goal_gid}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    client = get_client()
    goals_api = asana.GoalsApi(client)

    goals_api.delete_goal(goal_gid)

    logger.info(f"Deleted goal {goal_gid}")
    return True


@with_api_error_handling("updating metric for goal {goal_gid}")
def update_goal_metric(
    goal_gid: str,
    current_number_value: float,
) -> Dict[str, Any]:
    """
    Update the current value of a goal's metric.

    This updates the progress of a goal that has a metric attached.
    The goal must already have a metric set up via create_goal_metric().

    Args:
        goal_gid: Goal GID to update
        current_number_value: New current value for the metric

    Returns:
        Updated metric dictionary

    Raises:
        AsanaClientError: If the operation fails or goal has no metric
        ValueError: If inputs are invalid

    Example:
        # Update revenue goal progress
        update_goal_metric('goal123', current_number_value=75000)
    """
    if not goal_gid or not isinstance(goal_gid, str):
        raise ValueError(f"Invalid goal_gid: {goal_gid}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    client = get_client()
    goals_api = asana.GoalsApi(client)

    body = {"data": {"current_number_value": current_number_value}}
    result = goals_api.update_goal_metric(body, goal_gid, opts={})

    logger.info(f"Updated metric for goal {goal_gid} to {current_number_value}")

    if hasattr(result, "to_dict"):
        return result.to_dict()
    return result


@with_api_error_handling("creating metric for goal {goal_gid}")
def create_goal_metric(
    goal_gid: str,
    metric_type: str,
    target_number_value: float,
    initial_number_value: float = 0,
    unit: Optional[str] = None,
    currency_code: Optional[str] = None,
    precision: int = 0,
) -> Dict[str, Any]:
    """
    Create/set a metric for a goal.

    Args:
        goal_gid: Goal GID to add metric to
        metric_type: Type of metric ('number', 'percentage', 'currency')
        target_number_value: Target value to achieve
        initial_number_value: Starting value (default: 0)
        unit: Optional unit label (e.g., 'users', 'deals')
        currency_code: Currency code if metric_type is 'currency' (e.g., 'USD')
        precision: Decimal precision (default: 0)

    Returns:
        Created metric dictionary

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        # Create a revenue metric
        create_goal_metric(
            goal_gid='goal123',
            metric_type='currency',
            target_number_value=100000,
            currency_code='USD'
        )
    """
    if not goal_gid or not isinstance(goal_gid, str):
        raise ValueError(f"Invalid goal_gid: {goal_gid}")

    if metric_type not in VALID_METRIC_TYPES:
        raise ValueError(
            f"Invalid metric_type: {metric_type}. Must be one of: {VALID_METRIC_TYPES}"
        )

    if unit and unit not in VALID_METRIC_UNITS:
        raise ValueError(
            f"Invalid unit: {unit}. Must be one of: {VALID_METRIC_UNITS}"
        )

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    client = get_client()
    goals_api = asana.GoalsApi(client)

    metric_data = {
        "resource_subtype": metric_type,
        "target_number_value": target_number_value,
        "initial_number_value": initial_number_value,
        "precision": precision,
    }

    if unit:
        metric_data["unit"] = unit

    if currency_code:
        metric_data["currency_code"] = currency_code

    body = {"data": metric_data}
    result = goals_api.create_goal_metric(body, goal_gid, opts={})

    logger.info(f"Created {metric_type} metric for goal {goal_gid}")

    if hasattr(result, "to_dict"):
        return result.to_dict()
    return result


@with_api_error_handling("adding followers to goal {goal_gid}")
def add_goal_followers(goal_gid: str, follower_gids: List[str]) -> bool:
    """
    Add followers (collaborators) to a goal.

    Args:
        goal_gid: Goal GID
        follower_gids: List of user GIDs to add as followers

    Returns:
        True if successful

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        add_goal_followers('goal123', ['user1', 'user2'])
    """
    if not goal_gid or not isinstance(goal_gid, str):
        raise ValueError(f"Invalid goal_gid: {goal_gid}")

    if not follower_gids or not isinstance(follower_gids, list):
        raise ValueError(f"Invalid follower_gids: {follower_gids}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    client = get_client()
    goals_api = asana.GoalsApi(client)

    body = {"data": {"followers": follower_gids}}
    goals_api.add_followers(body, goal_gid, opts={})

    logger.info(f"Added {len(follower_gids)} followers to goal {goal_gid}")
    return True


@with_api_error_handling("removing followers from goal {goal_gid}")
def remove_goal_followers(goal_gid: str, follower_gids: List[str]) -> bool:
    """
    Remove followers (collaborators) from a goal.

    Args:
        goal_gid: Goal GID
        follower_gids: List of user GIDs to remove

    Returns:
        True if successful

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If inputs are invalid

    Example:
        remove_goal_followers('goal123', ['user1'])
    """
    if not goal_gid or not isinstance(goal_gid, str):
        raise ValueError(f"Invalid goal_gid: {goal_gid}")

    if not follower_gids or not isinstance(follower_gids, list):
        raise ValueError(f"Invalid follower_gids: {follower_gids}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    client = get_client()
    goals_api = asana.GoalsApi(client)

    body = {"data": {"followers": follower_gids}}
    goals_api.remove_followers(body, goal_gid, opts={})

    logger.info(f"Removed {len(follower_gids)} followers from goal {goal_gid}")
    return True


@with_api_error_handling("fetching parent goals for goal {goal_gid}")
def get_parent_goals(
    goal_gid: str,
    opt_fields: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Get parent goals for a goal.

    Args:
        goal_gid: Goal GID
        opt_fields: Optional list of fields to include

    Returns:
        List of parent goal dictionaries

    Raises:
        AsanaClientError: If the operation fails
        ValueError: If goal_gid is invalid

    Example:
        parents = get_parent_goals('goal123')
    """
    if not goal_gid or not isinstance(goal_gid, str):
        raise ValueError(f"Invalid goal_gid: {goal_gid}")

    if not ASANA_SDK_AVAILABLE:
        raise AsanaClientError(
            "Asana SDK not available. Install with: pip install asana"
        )

    client = get_client()
    goals_api = asana.GoalsApi(client)

    opts = {}
    if opt_fields:
        opts["opt_fields"] = ",".join(opt_fields)

    result = goals_api.get_parent_goals_for_goal(goal_gid, opts)

    goals = list(result) if result else []
    logger.info(f"Found {len(goals)} parent goals for {goal_gid}")
    return goals
