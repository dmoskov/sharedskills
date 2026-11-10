"""Remote MCP server exposing the ~/Code/asana library (asana_client + asana_sdk).

Every tool runs as the Asana user who connected the Claude connector: the
OAuthProxy in asana_auth.py hands each request that person's Asana token.

Run:  python server.py        (reads config from the environment; see README.md)
"""

from __future__ import annotations

import base64
import json
import logging
import os
import secrets
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Any, Literal, Optional
from urllib.parse import unquote, urlparse

import anyio
from key_value.aio.protocols import AsyncKeyValue
from key_value.aio.stores.memory import MemoryStore
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

LIB_DIR = Path(__file__).resolve().parent.parent
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

# The SDK must never fall back to a local token file inside a multi-user server.
os.environ["ASANA_SDK_REQUIRE_TOKEN_OVERRIDE"] = "1"

import asana_sdk  # noqa: E402
from asana_client import AsanaClient  # noqa: E402
from asana_to_markdown import asana_html_to_markdown  # noqa: E402
from markdown_to_asana import markdown_to_asana_html  # noqa: E402
from fastmcp import FastMCP  # noqa: E402
from fastmcp.exceptions import ToolError  # noqa: E402
from fastmcp.server.auth.ssrf import SSRFError, SSRFFetchError, ssrf_safe_fetch_response  # noqa: E402
from fastmcp.server.dependencies import get_access_token  # noqa: E402

logger = logging.getLogger(__name__)

READ = {"readOnlyHint": True, "openWorldHint": True}
WRITE = {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True}
DESTRUCTIVE = {"readOnlyHint": False, "destructiveHint": True, "openWorldHint": True}

JOB_WAIT_SECONDS = 20.0

TextFormat = Literal["markdown", "plain"]
Gid = Annotated[str, Field(description="Asana GID (numeric string)")]
OptGid = Optional[str]
Limit = Annotated[int, Field(ge=1, le=100)]
Date = Annotated[Optional[str], Field(description="YYYY-MM-DD")]

INSTRUCTIONS = """\
Asana, acting as the signed-in person in their default workspace.
- Use GIDs for every follow-up call; `find` turns names (people, projects, tags) into GIDs.
- `assignee` accepts "me", a user GID, or an email.
- Descriptions and comments default to markdown and are converted to Asana rich text;
  task descriptions come back as markdown.
- Dates are YYYY-MM-DD. Every task result includes a `url` to open it in Asana.
- To attach photos, PDFs or other real files, use `get_upload_link` and upload the file
  from a shell, or `attach_file_from_url`. `attach_file` is only for small text content.
"""


def _workspace() -> str:
    workspace = os.environ.get("ASANA_WORKSPACE")
    if not workspace:
        raise ToolError("Server misconfigured: ASANA_WORKSPACE is not set")
    return workspace


def _user_token() -> str:
    access = get_access_token()
    if access is None or not access.token:
        raise ToolError("No Asana session for this request. Reconnect the Asana connector.")
    return access.token


def _client() -> AsanaClient:
    return AsanaClient(token=_user_token(), workspace=_workspace())


@contextmanager
def _sdk():
    with asana_sdk.use_access_token(_user_token()):
        yield


def _task_url(gid: str) -> str:
    return f"https://app.asana.com/0/0/{gid}/f"


def _with_url(task: dict) -> dict:
    if task.get("gid"):
        task["url"] = _task_url(task["gid"])
    return task


def _with_urls(tasks: list[dict]) -> list[dict]:
    return [_with_url(t) for t in tasks]


def _rich(text: Optional[str], fmt: TextFormat) -> tuple[Optional[str], Optional[str]]:
    """Return (plain, html) for a body, converting markdown to Asana rich text."""
    if text is None:
        return None, None
    if fmt == "markdown":
        return None, markdown_to_asana_html(text)
    return text, None


def _project_url(gid: str) -> str:
    return f"https://app.asana.com/0/{gid}"


def _finish_job(client: AsanaClient, job: dict, key: Optional[str] = None) -> dict:
    """Wait briefly for an Asana job and return what it produced."""
    job = client.wait_for_job(job, timeout=JOB_WAIT_SECONDS)
    status = job.get("status")
    if status == "failed":
        raise ToolError("Asana reported that the job failed")
    out: dict = {"status": status, "job_gid": job.get("gid")}
    created = job.get(key) if key else None
    if created and created.get("gid"):
        url = _task_url(created["gid"]) if key == "new_task" else _project_url(created["gid"])
        out[key] = {**created, "url": url}
    if job.get("dates_rollup_progress"):
        out["dates_rollup_progress"] = job["dates_rollup_progress"]
    if status != "succeeded":
        out["note"] = "Still running in Asana; the result will appear shortly."
    return out


def _client_error(exc: ValueError) -> ToolError:
    return ToolError(str(exc))


mcp = FastMCP(name=os.environ.get("MCP_SERVER_NAME", "Asana"), instructions=INSTRUCTIONS)


# ========== Identity & discovery ==========


@mcp.tool(annotations=READ)
def whoami() -> dict:
    """The signed-in Asana user (name, email, GID, workspaces)."""
    return _client().get_me()


@mcp.tool(annotations=READ)
def find(
    query: Annotated[str, Field(description="Name or partial name to look up")],
    resource_type: Literal["user", "project", "tag", "task", "portfolio", "goal", "team"] = "user",
    limit: Limit = 10,
) -> list[dict]:
    """Fuzzy-find people, projects, tags, tasks, portfolios, goals, or teams by name; returns GIDs."""
    return _client().typeahead(query, resource_type=resource_type, count=limit)


@mcp.tool(annotations=READ)
def list_workspaces() -> list[dict]:
    """Workspaces the signed-in user can access."""
    return _client().list_workspaces()


# ========== Projects & sections ==========


@mcp.tool(annotations=READ)
def list_projects(archived: bool = False, limit: Limit = 50) -> list[dict]:
    """Projects in the workspace (owner, due date, status color)."""
    return _client().get_projects(archived=archived, limit=limit)


@mcp.tool(annotations=READ)
def get_project(project_gid: Gid) -> dict:
    """Project details: notes, owner, due date, current status, custom fields."""
    return _client().get_project(project_gid)


ProjectView = Literal["list", "board", "calendar", "timeline"]
ProjectPrivacy = Literal["public_to_workspace", "private"]
Users = Annotated[list[str], Field(min_length=1, description='Each "me", an email, or a user GID')]


@mcp.tool(annotations=READ)
def search_projects(
    text: Annotated[Optional[str], Field(description="Words in the project name")] = None,
    completed: Optional[bool] = None,
    team_gid: OptGid = None,
    owner: Annotated[Optional[str], Field(description='"me", user GID, or email')] = None,
    member: Annotated[Optional[str], Field(description='"me", user GID, or email')] = None,
    portfolio_gid: OptGid = None,
    due_before: Date = None,
    due_after: Date = None,
    sort_by: Literal["modified_at", "created_at", "completed_at", "due_date", "relevance"] = "modified_at",
    limit: Limit = 50,
) -> list[dict]:
    """Search projects by name, team, owner, member, portfolio or due date (paid Asana plans only; new projects can take a minute to appear)."""
    return _client().search_projects(
        text=text,
        completed=completed,
        team=team_gid,
        owner=owner,
        member=member,
        portfolio=portfolio_gid,
        due_before=due_before,
        due_after=due_after,
        sort_by=sort_by,
        limit=limit,
    )


@mcp.tool(annotations=WRITE)
def create_project(
    name: str,
    team_gid: Annotated[OptGid, Field(description="Required when the workspace is an organization")] = None,
    notes: Annotated[Optional[str], Field(description="Description")] = None,
    notes_format: TextFormat = "markdown",
    default_view: Optional[ProjectView] = None,
    start_on: Date = None,
    due_on: Date = None,
    privacy: Optional[ProjectPrivacy] = None,
    owner: Annotated[Optional[str], Field(description='"me", user GID, or email')] = None,
    color: Optional[str] = None,
) -> dict:
    """Create a project."""
    plain, html = _rich(notes, notes_format)
    project = _client().create_project(
        name,
        team=team_gid,
        notes=plain,
        html_notes=html,
        default_view=default_view,
        start_on=start_on,
        due_on=due_on,
        privacy_setting=privacy,
        owner=owner,
        color=color,
    )
    if project.get("gid"):
        project["url"] = _project_url(project["gid"])
    return project


@mcp.tool(annotations=WRITE)
def update_project(
    project_gid: Gid,
    name: Optional[str] = None,
    notes: Annotated[Optional[str], Field(description="Replaces the whole description")] = None,
    notes_format: TextFormat = "markdown",
    archived: Optional[bool] = None,
    default_view: Optional[ProjectView] = None,
    start_on: Date = None,
    due_on: Date = None,
    privacy: Optional[ProjectPrivacy] = None,
    owner: Annotated[Optional[str], Field(description='"me", user GID, or email')] = None,
    color: Optional[str] = None,
) -> dict:
    """Change a project's name, description, dates, owner, view, privacy or color, or archive/unarchive it."""
    plain, html = _rich(notes, notes_format)
    try:
        return _client().update_project(
            project_gid,
            name=name,
            notes=plain,
            html_notes=html,
            archived=archived,
            default_view=default_view,
            start_on=start_on,
            due_on=due_on,
            privacy_setting=privacy,
            owner=owner,
            color=color,
        )
    except ValueError as exc:
        raise _client_error(exc) from exc


@mcp.tool(annotations=WRITE)
def duplicate_project(
    project_gid: Gid,
    name: str,
    include: Annotated[
        Optional[list[str]],
        Field(
            description="Extras to copy (tasks, views and rules always are): allocations, forms, members, notes, "
            "permissions, task_assignee, task_attachments, task_dates, task_dependencies, task_followers, "
            "task_notes, task_projects, task_subtasks, task_tags, task_templates, task_type_default"
        ),
    ] = None,
    team_gid: OptGid = None,
    start_on: Annotated[Optional[str], Field(description="Shift task dates so the copy starts here; needs task_dates")] = None,
    due_on: Annotated[Optional[str], Field(description="Or shift so it ends here; not both")] = None,
) -> dict:
    """Copy a project. Returns the new project once Asana finishes (usually seconds)."""
    client = _client()
    try:
        job = client.duplicate_project(
            project_gid, name, include=include, team=team_gid, start_on=start_on, due_on=due_on
        )
    except ValueError as exc:
        raise _client_error(exc) from exc
    return _finish_job(client, job, "new_project")


@mcp.tool(annotations=READ)
def list_project_templates(team_gid: OptGid = None, limit: Limit = 50) -> list[dict]:
    """Project templates in a team, or across every team when team_gid is omitted."""
    return _client().get_project_templates(team_gid=team_gid, limit=limit)


@mcp.tool(annotations=READ)
def get_project_template(project_template_gid: Gid) -> dict:
    """A project template, with the dates and roles it asks for when used."""
    return _client().get_project_template(project_template_gid)


@mcp.tool(annotations=WRITE)
def create_project_from_template(
    project_template_gid: Gid,
    name: str,
    team_gid: Annotated[OptGid, Field(description="Required when the workspace is an organization")] = None,
    privacy: Optional[ProjectPrivacy] = None,
    dates: Annotated[
        Optional[dict[str, str]],
        Field(description='Template date GID -> YYYY-MM-DD ("1" = project start, "2" = project due; see get_project_template)'),
    ] = None,
    roles: Annotated[
        Optional[dict[str, str]], Field(description='Template role GID -> "me", email, or user GID')
    ] = None,
) -> dict:
    """Create a project from a project template. Returns the new project once Asana finishes."""
    client = _client()
    job = client.instantiate_project_template(
        project_template_gid,
        name,
        team=team_gid,
        privacy_setting=privacy,
        requested_dates=dates,
        requested_roles=roles,
    )
    return _finish_job(client, job, "new_project")


def _people(project: dict) -> dict:
    return {
        "project": project.get("gid"),
        "followers": project.get("followers", []),
        "members": project.get("members", []),
    }


@mcp.tool(annotations=WRITE)
def add_project_followers(project_gid: Gid, followers: Users) -> dict:
    """Make people followers of a project (they also become members)."""
    return _people(_client().add_project_followers(project_gid, followers))


@mcp.tool(annotations=WRITE)
def remove_project_followers(project_gid: Gid, followers: Users) -> dict:
    """Stop people following a project; they stay members."""
    return _people(_client().remove_project_followers(project_gid, followers))


@mcp.tool(annotations=WRITE)
def add_project_members(project_gid: Gid, members: Users) -> dict:
    """Give people access to a project as members."""
    return _people(_client().add_project_members(project_gid, members))


@mcp.tool(annotations=WRITE)
def remove_project_members(project_gid: Gid, members: Users) -> dict:
    """Remove people from a project's members."""
    return _people(_client().remove_project_members(project_gid, members))


@mcp.tool(annotations=READ)
def list_sections(project_gid: Gid) -> list[dict]:
    """Sections (columns) of a project, in order."""
    return _client().get_project_sections(project_gid)


@mcp.tool(annotations=READ)
def list_custom_fields(project_gid: Gid) -> list[dict]:
    """Custom fields on a project, including enum option GIDs (needed to set or filter by them)."""
    return _client().get_custom_field_settings(project_gid)


@mcp.tool(annotations=WRITE)
def create_section(
    project_gid: Gid,
    name: str,
    insert_before: OptGid = None,
    insert_after: OptGid = None,
) -> dict:
    """Add a section to a project, optionally positioned before/after another section GID."""
    return _client().create_section(project_gid, name, insert_before=insert_before, insert_after=insert_after)


@mcp.tool(annotations=WRITE)
def rename_section(section_gid: Gid, name: str) -> dict:
    """Rename a section."""
    return _client().update_section(section_gid, name)


@mcp.tool(annotations=DESTRUCTIVE)
def delete_section(section_gid: Gid) -> dict:
    """Delete an empty section (Asana refuses if it still holds tasks)."""
    _client().delete_section(section_gid)
    return {"deleted": section_gid}


@mcp.tool(annotations=WRITE)
def post_project_status(
    project_gid: Gid,
    title: str,
    text: str,
    status: Literal["on_track", "at_risk", "off_track", "on_hold", "complete"] = "on_track",
    text_format: TextFormat = "markdown",
) -> dict:
    """Post a status update on a project."""
    plain, html = _rich(text, text_format)
    with _sdk():
        return asana_sdk.create_project_status_update(
            project_gid, title=title, text=plain or text, status_type=status, html_text=html
        )


# ========== Tasks ==========


@mcp.tool(annotations=READ)
def get_task(task_gid: Gid) -> dict:
    """Full task details; the description is returned as markdown in `notes_markdown`.

    `effective_memberships` lists the projects a subtask inherits from its parents (is_inherited).
    """
    task = _client().get_task(task_gid)
    html = task.pop("html_notes", None)
    if html:
        task["notes_markdown"] = asana_html_to_markdown(html)
        task.pop("notes", None)
    return _with_url(task)


@mcp.tool(annotations=READ)
def list_tasks(
    project_gid: OptGid = None,
    section_gid: OptGid = None,
    assignee: Annotated[Optional[str], Field(description='"me", user GID, or email')] = None,
    incomplete_only: bool = True,
    limit: Limit = 100,
) -> list[dict]:
    """Tasks in a project or section, or assigned to someone. Give at least one of the three."""
    client = _client()
    if not (project_gid or section_gid or assignee):
        raise ToolError("Give project_gid, section_gid, or assignee")
    if section_gid and (project_gid or assignee):
        raise ToolError("section_gid can't be combined with project_gid or assignee; filter by project_gid + assignee instead")
    if project_gid and assignee:
        # GET /tasks can't filter by both; the search API can.
        tasks = client.search_tasks(
            assignee=assignee,
            projects=project_gid,
            completed=False if incomplete_only else None,
            limit=limit,
        )
    else:
        tasks = client.get_tasks(
            project=project_gid,
            section=section_gid,
            assignee=assignee,
            completed=False if incomplete_only else None,
            limit=limit,
        )
    return _with_urls(tasks)


@mcp.tool(annotations=READ)
def my_tasks(incomplete_only: bool = True, limit: Limit = 100) -> list[dict]:
    """Tasks assigned to the signed-in user."""
    tasks = _client().get_tasks(assignee="me", completed=False if incomplete_only else None, limit=limit)
    return _with_urls(tasks)


@mcp.tool(annotations=READ)
def search_tasks(
    text: Optional[str] = None,
    assignee: Annotated[Optional[str], Field(description='"me", user GID, or email')] = None,
    project_gid: OptGid = None,
    completed: Optional[bool] = None,
    custom_fields: Annotated[
        Optional[dict[str, str]],
        Field(description="Map of custom field GID -> enum option GID (see list_custom_fields)"),
    ] = None,
    limit: Limit = 50,
) -> list[dict]:
    """Search the workspace's tasks by text and filters, newest-modified first (max 100)."""
    tasks = _client().search_tasks(
        text=text,
        assignee=assignee,
        projects=project_gid,
        completed=completed,
        custom_fields=custom_fields,
        limit=limit,
    )
    return _with_urls(tasks)


@mcp.tool(annotations=WRITE)
def create_task(
    name: str,
    project_gid: OptGid = None,
    section_gid: Annotated[OptGid, Field(description="Section within project_gid")] = None,
    parent_gid: Annotated[OptGid, Field(description="Create as a subtask of this task")] = None,
    assignee: Annotated[Optional[str], Field(description='"me", user GID, or email')] = None,
    due_on: Date = None,
    start_on: Annotated[Optional[str], Field(description="YYYY-MM-DD; needs due_on too")] = None,
    notes: Annotated[Optional[str], Field(description="Description")] = None,
    notes_format: TextFormat = "markdown",
    custom_fields: Annotated[
        Optional[dict[str, Any]],
        Field(description="Map of custom field GID -> value (enum option GID, number, or text)"),
    ] = None,
    remove_me_as_follower: Annotated[
        bool, Field(description="Asana makes the creator a follower; set true to drop the signed-in user afterwards")
    ] = False,
) -> dict:
    """Create a task in a project/section, or a subtask with parent_gid (project_gid then also lists it on that project)."""
    plain, html = _rich(notes, notes_format)
    client = _client()
    if section_gid and not project_gid:
        raise ToolError("section_gid requires project_gid")
    if parent_gid:
        if section_gid or start_on:
            raise ToolError("Subtasks can't take section_gid or start_on at creation; move or update them afterwards")
        task = client.create_subtask(
            parent_gid,
            name,
            assignee=assignee,
            due_on=due_on,
            notes=plain,
            html_notes=html,
            custom_fields=custom_fields,
            projects=[project_gid] if project_gid else None,
        )
    else:
        task = client.create_task(
            name,
            project=project_gid,
            section=section_gid,
            assignee=assignee,
            due_on=due_on,
            start_on=start_on,
            notes=plain,
            html_notes=html,
            custom_fields=custom_fields,
        )
    if remove_me_as_follower and task.get("gid"):
        updated = client.remove_followers(task["gid"], ["me"])
        task["followers"] = updated.get("followers", [])
        task["removed_followers"] = ["me"]
    return _with_url(task)


@mcp.tool(annotations=WRITE)
def update_task(
    task_gid: Gid,
    name: Optional[str] = None,
    completed: Optional[bool] = None,
    assignee: Annotated[Optional[str], Field(description='"me", user GID, or email')] = None,
    due_on: Date = None,
    start_on: Annotated[Optional[str], Field(description='YYYY-MM-DD, or "" to clear')] = None,
    notes: Annotated[Optional[str], Field(description="Replaces the whole description")] = None,
    notes_format: TextFormat = "markdown",
    custom_fields: Optional[dict[str, Any]] = None,
) -> dict:
    """Change a task's name, completion, assignee, dates, description, or custom fields."""
    plain, html = _rich(notes, notes_format)
    task = _client().update_task(
        task_gid,
        name=name,
        completed=completed,
        assignee=assignee,
        due_on=due_on,
        start_on=start_on,
        notes=plain,
        html_notes=html,
        custom_fields=custom_fields,
    )
    return _with_url(task)


@mcp.tool(annotations=DESTRUCTIVE)
def delete_task(task_gid: Gid) -> dict:
    """Delete a task (it goes to Asana's trash for 30 days)."""
    _client().delete_task(task_gid)
    return {"deleted": task_gid}


@mcp.tool(annotations=READ)
def list_subtasks(task_gid: Gid) -> list[dict]:
    """Subtasks of a task."""
    return _with_urls(_client().get_subtasks(task_gid))


@mcp.tool(annotations=WRITE)
def set_parent(
    task_gid: Gid,
    parent_gid: Annotated[OptGid, Field(description="New parent task; omit to make it a top-level task")] = None,
    insert_before: OptGid = None,
    insert_after: OptGid = None,
) -> dict:
    """Make a task a subtask of another task, or detach it from its parent."""
    return _with_url(_client().set_parent(task_gid, parent_gid, insert_before=insert_before, insert_after=insert_after))


@mcp.tool(annotations=WRITE)
def move_task_to_section(
    task_gid: Gid,
    section_gid: Gid,
    insert_before: OptGid = None,
    insert_after: OptGid = None,
) -> dict:
    """Move a task into a section (and out of its current section in that project)."""
    _client().move_task_to_section(task_gid, section_gid, insert_before=insert_before, insert_after=insert_after)
    return {"moved": task_gid, "section": section_gid}


@mcp.tool(annotations=WRITE)
def add_task_to_project(task_gid: Gid, project_gid: Gid) -> dict:
    """Also list an existing task in another project (multi-homing)."""
    with _sdk():
        asana_sdk.add_task_to_project(task_gid, project_gid)
    return {"task": task_gid, "added_to_project": project_gid}


@mcp.tool(annotations=WRITE)
def remove_task_from_project(task_gid: Gid, project_gid: Gid) -> dict:
    """Take a task off a project without deleting it (it stays in its other projects)."""
    _client().remove_from_project(task_gid, project_gid)
    return {"task": task_gid, "removed_from_project": project_gid}


@mcp.tool(annotations=WRITE)
def duplicate_task(
    task_gid: Gid,
    name: str,
    include: Annotated[
        Optional[list[str]],
        Field(
            description="What to copy besides the name: assignee, attachments, dates, dependencies, followers, "
            "notes, parent, projects, subtasks, tags"
        ),
    ] = None,
) -> dict:
    """Copy a task. Returns the new task once Asana finishes (usually seconds)."""
    client = _client()
    try:
        job = client.duplicate_task(task_gid, name, include=include)
    except ValueError as exc:
        raise _client_error(exc) from exc
    return _finish_job(client, job, "new_task")


@mcp.tool(annotations=READ)
def list_task_templates(project_gid: Gid, limit: Limit = 50) -> list[dict]:
    """Task templates defined on a project."""
    return _client().get_task_templates(project_gid, limit=limit)


@mcp.tool(annotations=WRITE)
def create_task_from_template(
    task_template_gid: Gid,
    name: Annotated[Optional[str], Field(description="Defaults to the template's name")] = None,
) -> dict:
    """Create a task from a task template (in the template's project). Returns the new task once Asana finishes."""
    client = _client()
    return _finish_job(client, client.instantiate_task_template(task_template_gid, name=name), "new_task")


@mcp.tool(annotations=READ)
def get_task_projects(task_gid: Gid, include_inherited: bool = True) -> list[dict]:
    """Projects a task is in; for a subtask, also the projects it inherits from its parent tasks."""
    return _client().get_task_projects(task_gid, include_inherited=include_inherited)


@mcp.tool(annotations=WRITE)
def rollup_subtask_dates(task_gid: OptGid = None, project_gid: OptGid = None) -> dict:
    """Stretch parent task dates to cover their subtasks' dates, for one task or every task in a project."""
    if bool(task_gid) == bool(project_gid):
        raise ToolError("Give exactly one of task_gid or project_gid")
    client = _client()
    job = client.rollup_task_dates(task_gid) if task_gid else client.rollup_project_dates(project_gid)
    return _finish_job(client, job)


@mcp.tool(annotations=WRITE)
def like_task(task_gid: Gid, liked: bool = True) -> dict:
    """Like a task as the signed-in user, or unlike it with liked=false."""
    return _with_url(_client().set_task_liked(task_gid, liked))


@mcp.tool(annotations=WRITE)
def add_followers(task_gid: Gid, followers: Users) -> dict:
    """Make people followers of a task so they get its notifications."""
    task = _client().add_followers(task_gid, followers)
    return {"task": task_gid, "followers": task.get("followers", [])}


@mcp.tool(annotations=WRITE)
def remove_followers(task_gid: Gid, followers: Users) -> dict:
    """Stop people following a task (e.g. drop the creator). People not following are ignored."""
    task = _client().remove_followers(task_gid, followers)
    return {"task": task_gid, "followers": task.get("followers", [])}


@mcp.tool(annotations=READ)
def overdue_tasks(project_gid: Gid) -> list[dict]:
    """Incomplete tasks in a project whose due date has passed."""
    with _sdk():
        return _with_urls(asana_sdk.get_overdue_tasks(project_gid))


@mcp.tool(annotations=READ)
def recently_completed_tasks(project_gid: Gid, days: int = 7) -> list[dict]:
    """Tasks in a project completed in the last N days."""
    with _sdk():
        return _with_urls(asana_sdk.get_recently_completed_tasks(project_gid, days=days))


# ========== Comments & activity ==========


@mcp.tool(annotations=READ)
def get_comments(task_gid: Gid, include_activity: bool = False, limit: Limit = 50) -> list[dict]:
    """Comments on a task; set include_activity for the full history (assignments, moves, edits)."""
    client = _client()
    if include_activity:
        return client.get_stories(task_gid, limit=limit)
    return client.get_comments(task_gid, limit=limit)


@mcp.tool(annotations=WRITE)
def add_comment(task_gid: Gid, text: str, text_format: TextFormat = "markdown") -> dict:
    """Comment on a task."""
    plain, html = _rich(text, text_format)
    return _client().add_comment(task_gid, text=plain, html_text=html)


@mcp.tool(annotations=READ)
def get_comment(story_gid: Gid) -> dict:
    """One comment with its pin state, like count and emoji reaction summary."""
    return _client().get_story(story_gid)


@mcp.tool(annotations=WRITE)
def update_comment(
    story_gid: Gid,
    text: Annotated[Optional[str], Field(description="New text; only the author can edit")] = None,
    text_format: TextFormat = "markdown",
    pinned: Annotated[Optional[bool], Field(description="Pin or unpin the comment on its task")] = None,
) -> dict:
    """Edit a comment's text and/or pin or unpin it."""
    plain, html = _rich(text, text_format)
    try:
        return _client().update_story(story_gid, text=plain, html_text=html, is_pinned=pinned)
    except ValueError as exc:
        raise _client_error(exc) from exc


@mcp.tool(annotations=READ)
def list_reactions(
    target_gid: Annotated[str, Field(description="GID of a comment (story) or status update")],
    emoji: Annotated[str, Field(description="The emoji to look up, e.g. 👍 (see get_comment's reaction_summary)")],
    limit: Limit = 50,
) -> list[dict]:
    """Who reacted with a given emoji. Asana's API can't add reactions or like comments; only tasks can be liked (like_task)."""
    return _client().get_reactions(target_gid, emoji, limit=limit)


@mcp.tool(annotations=DESTRUCTIVE)
def delete_comment(story_gid: Gid) -> dict:
    """Delete a comment (story GID from get_comments). Only the author can delete it."""
    with _sdk():
        asana_sdk.delete_story(story_gid)
    return {"deleted": story_gid}


# ========== Inbox ==========

NotificationGids = Annotated[list[str], Field(min_length=1, description="Notification GIDs from get_notifications")]


@mcp.tool(annotations=READ)
def get_notifications(
    limit: Limit = 50,
    offset: Annotated[Optional[str], Field(description="next_offset from a previous call")] = None,
) -> dict:
    """The signed-in user's Inbox, newest first: only unarchived notifications (Asana's API can't list or set archived)."""
    page = _client().get_notifications(limit=limit, offset=offset)
    for n in page["notifications"]:
        for obj in n.get("work_objects") or []:
            if obj.get("resource_type") == "task" and obj.get("gid"):
                obj["url"] = _task_url(obj["gid"])
    return page


@mcp.tool(annotations=WRITE)
def mark_notifications_read(notification_gids: NotificationGids) -> dict:
    """Mark Inbox notifications read. Asana's API has no archive action; this is the closest it allows."""
    failed = _client().mark_notifications_read(notification_gids)
    return {"marked_read": len(set(notification_gids)) - len(failed), "failed_gids": failed}


@mcp.tool(annotations=WRITE)
def mark_notifications_unread(notification_gids: NotificationGids) -> dict:
    """Mark notifications unread. An archived notification also returns to the top of the Inbox."""
    failed = _client().mark_notifications_unread(notification_gids)
    return {"marked_unread": len(set(notification_gids)) - len(failed), "failed_gids": failed}


# ========== Out of office ==========

UserRef = Annotated[str, Field(description='"me" or a user GID')]


@mcp.tool(annotations=READ)
def list_out_of_office(
    user: UserRef = "me",
    start_date: Annotated[Optional[str], Field(description="YYYY-MM-DD; only entries overlapping the range")] = None,
    end_date: Date = None,
    limit: Limit = 50,
) -> list[dict]:
    """When someone is marked out of office in Asana."""
    return _client().get_ooo_entries(user=user, start_date=start_date, end_date=end_date, limit=limit)


@mcp.tool(annotations=WRITE)
def set_out_of_office(
    start_date: Annotated[str, Field(description="YYYY-MM-DD, first day away")],
    end_date: Annotated[str, Field(description="YYYY-MM-DD, last day away")],
    user: UserRef = "me",
) -> dict:
    """Mark someone out of office for a date range. Overlapping an existing entry is rejected; update that one instead."""
    return _client().create_ooo_entry(start_date, end_date, user=user)


@mcp.tool(annotations=WRITE)
def update_out_of_office(ooo_entry_gid: Gid, start_date: Date = None, end_date: Date = None) -> dict:
    """Change the dates of an out-of-office entry."""
    try:
        return _client().update_ooo_entry(ooo_entry_gid, start_date=start_date, end_date=end_date)
    except ValueError as exc:
        raise _client_error(exc) from exc


@mcp.tool(annotations=DESTRUCTIVE)
def delete_out_of_office(ooo_entry_gid: Gid) -> dict:
    """Delete an out-of-office entry."""
    _client().delete_ooo_entry(ooo_entry_gid)
    return {"deleted": ooo_entry_gid}


# ========== Dependencies ==========


@mcp.tool(annotations=READ)
def get_dependencies(task_gid: Gid) -> dict:
    """What blocks this task (`blocked_by`) and what it blocks (`blocking`)."""
    client = _client()
    return {
        "blocked_by": _with_urls(client.get_dependencies(task_gid)),
        "blocking": _with_urls(client.get_dependents(task_gid)),
    }


@mcp.tool(annotations=WRITE)
def add_dependencies(
    task_gid: Gid,
    blocked_by: Annotated[Optional[list[str]], Field(description="Task GIDs that must finish first")] = None,
    blocks: Annotated[Optional[list[str]], Field(description="Task GIDs that wait on this one")] = None,
) -> dict:
    """Mark tasks as blocking or blocked by this task."""
    blocked_by, blocks = blocked_by or [], blocks or []
    if not blocked_by and not blocks:
        raise ToolError("Give blocked_by and/or blocks")
    client = _client()
    if blocked_by:
        client.add_dependencies(task_gid, blocked_by)
    for dependent in blocks:
        client.add_dependent(task_gid, dependent)
    return {"task": task_gid, "blocked_by_added": blocked_by, "blocks_added": blocks}


@mcp.tool(annotations=WRITE)
def remove_dependencies(
    task_gid: Gid,
    blocked_by: Optional[list[str]] = None,
    blocks: Optional[list[str]] = None,
) -> dict:
    """Remove blocking relationships from this task."""
    blocked_by, blocks = blocked_by or [], blocks or []
    if not blocked_by and not blocks:
        raise ToolError("Give blocked_by and/or blocks")
    client = _client()
    for blocker in blocked_by:
        client.remove_dependency(task_gid, blocker)
    for dependent in blocks:
        client.remove_dependent(task_gid, dependent)
    return {"task": task_gid, "blocked_by_removed": blocked_by, "blocks_removed": blocks}


@mcp.tool(annotations=WRITE)
def chain_tasks(task_gids: Annotated[list[str], Field(min_length=2, description="In order; each waits on the previous")]) -> dict:
    """Make tasks sequential: each task is blocked by the one before it."""
    created = _client().chain_dependencies(task_gids)
    return {"dependencies_created": created}


# ========== Tags ==========


@mcp.tool(annotations=READ)
def list_tags(limit: Limit = 100) -> list[dict]:
    """Tags in the workspace."""
    return _client().get_tags(limit=limit)


@mcp.tool(annotations=WRITE)
def create_tag(name: str, color: Optional[str] = None, notes: Optional[str] = None) -> dict:
    """Create a tag (color like "dark-green", "light-blue")."""
    return _client().create_tag(name, color=color, notes=notes)


@mcp.tool(annotations=WRITE)
def tag_task(task_gid: Gid, tag_gid: Gid) -> dict:
    """Add a tag to a task."""
    _client().add_tag_to_task(task_gid, tag_gid)
    return {"task": task_gid, "tag_added": tag_gid}


@mcp.tool(annotations=WRITE)
def untag_task(task_gid: Gid, tag_gid: Gid) -> dict:
    """Remove a tag from a task."""
    _client().remove_tag_from_task(task_gid, tag_gid)
    return {"task": task_gid, "tag_removed": tag_gid}


# ========== Teams & portfolios ==========


@mcp.tool(annotations=READ)
def list_teams() -> list[dict]:
    """Teams in the workspace."""
    return _client().get_teams()


@mcp.tool(annotations=READ)
def list_team_members(team_gid: Gid) -> list[dict]:
    """Members of a team (name, email)."""
    return _client().get_team_members(team_gid)


@mcp.tool(annotations=READ)
def list_portfolios(owner: Annotated[str, Field(description='"me" or a user GID')] = "me") -> list[dict]:
    """Portfolios owned by a user."""
    return _client().get_portfolios(owner=owner)


@mcp.tool(annotations=READ)
def list_portfolio_items(portfolio_gid: Gid) -> list[dict]:
    """Projects (and nested portfolios) in a portfolio, with status and due dates."""
    return _client().get_portfolio_items(portfolio_gid)


# ========== Goals ==========


@mcp.tool(annotations=READ)
def list_goals(team_gid: OptGid = None, time_period_gid: OptGid = None, limit: Limit = 50) -> list[dict]:
    """Goals in the workspace, optionally filtered by team or time period."""
    with _sdk():
        return asana_sdk.get_goals(_workspace(), team_gid=team_gid, time_period_gid=time_period_gid, limit=limit)


@mcp.tool(annotations=READ)
def get_goal(goal_gid: Gid) -> dict:
    """Goal details including owner, dates, status, and metric progress."""
    with _sdk():
        return asana_sdk.get_goal(
            goal_gid,
            opt_fields=["name", "owner.name", "status", "due_on", "start_on", "notes",
                        "metric", "team.name", "time_period.display_name"],
        )


@mcp.tool(annotations=WRITE)
def create_goal(
    name: str,
    owner_gid: OptGid = None,
    due_on: Optional[str] = None,
    start_on: Optional[str] = None,
    notes: Optional[str] = None,
    team_gid: OptGid = None,
    time_period_gid: OptGid = None,
) -> dict:
    """Create a goal in the workspace."""
    with _sdk():
        gid = asana_sdk.create_goal(
            name=name,
            workspace_gid=_workspace(),
            owner_gid=owner_gid,
            due_on=due_on,
            start_on=start_on,
            notes=notes,
            team_gid=team_gid,
            time_period_gid=time_period_gid,
        )
    return {"gid": gid, "name": name}


@mcp.tool(annotations=WRITE)
def update_goal(
    goal_gid: Gid,
    name: Optional[str] = None,
    owner_gid: OptGid = None,
    due_on: Optional[str] = None,
    start_on: Optional[str] = None,
    status: Annotated[
        Optional[str], Field(description="green, yellow, red, missed, achieved, partial, dropped")
    ] = None,
    notes: Optional[str] = None,
) -> dict:
    """Update a goal's fields or status."""
    with _sdk():
        return asana_sdk.update_goal(
            goal_gid, name=name, owner_gid=owner_gid, due_on=due_on,
            start_on=start_on, status=status, notes=notes,
        )


@mcp.tool(annotations=WRITE)
def update_goal_progress(goal_gid: Gid, current_value: float) -> dict:
    """Set the current value of a goal's metric (the goal must already have a metric)."""
    with _sdk():
        return asana_sdk.update_goal_metric(goal_gid, current_number_value=current_value)


# ========== Attachments ==========


@mcp.tool(annotations=READ)
def list_attachments(task_gid: Gid) -> list[dict]:
    """Files attached to a task."""
    with _sdk():
        return asana_sdk.get_task_attachments(task_gid)


@mcp.tool(annotations=READ)
def get_attachment(attachment_gid: Gid) -> dict:
    """Attachment details including a download_url that is valid for about 2 minutes."""
    with _sdk():
        return asana_sdk.get_attachment(attachment_gid)


FileName = Annotated[str, Field(description="Name in Asana, with the extension, e.g. notes.md or photo.jpg")]

UPLOAD_COLLECTION = "asana_mcp_uploads"
UPLOAD_TTL_SECONDS = 15 * 60

# Pending upload links. main() swaps in the encrypted OAuth store when one is configured,
# so links survive restarts and work across replicas.
_upload_store: AsyncKeyValue = MemoryStore()


def set_upload_store(store: AsyncKeyValue) -> None:
    global _upload_store
    _upload_store = store


def _max_upload_bytes() -> int:
    return int(os.environ.get("ASANA_MCP_MAX_UPLOAD_MB", "50")) * 1024 * 1024


def _safe_file_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned or cleaned in {".", ".."} or "/" in cleaned or "\\" in cleaned or "\x00" in cleaned:
        raise ToolError(f"Invalid file name {name!r}: give a bare name like photo.jpg, without folders")
    return cleaned


def _upload_as(token: str, task_gid: str, data: bytes, file_name: str, content_type: Optional[str]) -> dict:
    with asana_sdk.use_access_token(token):
        return asana_sdk.upload_attachment_to_task(
            task_gid, file_content=data, file_name=file_name, content_type=content_type
        )


@mcp.tool(annotations=WRITE)
def attach_file(
    task_gid: Gid,
    file_name: FileName,
    content: str,
    encoding: Literal["text", "base64"] = "text",
    content_type: Optional[str] = None,
) -> dict:
    """Attach a small file whose content you type into this call (text or base64).

    Not for photos, PDFs or anything over a few KB: use get_upload_link or
    attach_file_from_url instead.
    """
    name = _safe_file_name(file_name)
    data = base64.b64decode(content, validate=True) if encoding == "base64" else content.encode("utf-8")
    return _upload_as(_user_token(), task_gid, data, name, content_type)


@mcp.tool(annotations=WRITE)
async def get_upload_link(
    task_gid: Gid,
    file_name: FileName,
    content_type: Annotated[Optional[str], Field(description="MIME type; guessed from file_name if omitted")] = None,
) -> dict:
    """One-time link for attaching a file of any size (photos, PDFs, videos) to a task.

    Send the raw file bytes to `upload_url` with HTTP PUT from a shell, e.g.
    `curl --fail-with-body -T /path/to/photo.jpg '<upload_url>'`. The response is the new
    attachment. The link works once and expires after 15 minutes.
    """
    name = _safe_file_name(file_name)
    base_url = os.environ.get("MCP_BASE_URL")
    if not base_url:
        raise ToolError("Server misconfigured: MCP_BASE_URL is not set")
    upload_id = secrets.token_urlsafe(32)
    await _upload_store.put(
        key=upload_id,
        value={
            "asana_token": _user_token(),
            "task_gid": task_gid,
            "file_name": name,
            "content_type": content_type,
            "expires_at": time.time() + UPLOAD_TTL_SECONDS,
        },
        collection=UPLOAD_COLLECTION,
        ttl=UPLOAD_TTL_SECONDS,
    )
    upload_url = f"{base_url.rstrip('/')}/uploads/{upload_id}"
    return {
        "upload_url": upload_url,
        "method": "PUT",
        "curl": f"curl --fail-with-body -T <path-to-file> '{upload_url}'",
        "expires_in_seconds": UPLOAD_TTL_SECONDS,
        "max_bytes": _max_upload_bytes(),
    }


def _upload_error(status: int, error: str, description: str) -> JSONResponse:
    return JSONResponse({"error": error, "error_description": description}, status_code=status)


@mcp.custom_route("/uploads/{upload_id}", methods=["PUT", "POST"], include_in_schema=False)
async def receive_upload(request: Request) -> Response:
    """Receive the bytes for a get_upload_link link and attach them as the link's owner."""
    upload_id = request.path_params["upload_id"]
    record = await _upload_store.get(key=upload_id, collection=UPLOAD_COLLECTION)
    if record is None or record["expires_at"] < time.time():
        return _upload_error(
            404, "upload_link_invalid", "This upload link is unknown, used, or expired. Get a new one with get_upload_link."
        )

    limit = _max_upload_bytes()
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        return _upload_error(413, "file_too_large", f"The file is {declared} bytes; the limit is {limit} bytes.")
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            return _upload_error(413, "file_too_large", f"The file is over the {limit}-byte limit.")
        chunks.append(chunk)
    if size == 0:
        return _upload_error(400, "empty_body", "No file bytes received. Send the file, e.g. curl -T photo.jpg '<link>'.")

    # Deleting first makes the link single-use even if two uploads race.
    if not await _upload_store.delete(key=upload_id, collection=UPLOAD_COLLECTION):
        return _upload_error(404, "upload_link_invalid", "This upload link was already used.")
    try:
        attachment = await anyio.to_thread.run_sync(
            _upload_as, record["asana_token"], record["task_gid"], b"".join(chunks), record["file_name"], record["content_type"]
        )
    except Exception as e:
        logger.exception("Upload of %s to Asana task %s failed", record["file_name"], record["task_gid"])
        return _upload_error(502, "asana_upload_failed", f"Asana rejected the upload: {e}")
    return Response(json.dumps(attachment, default=str), media_type="application/json")


def _file_name_from_url(url: str) -> str:
    name = unquote(Path(urlparse(url).path).name)
    if not name:
        raise ToolError(f"Can't tell the file name from {url}; pass file_name")
    return name


@mcp.tool(annotations=WRITE)
async def attach_file_from_url(
    task_gid: Gid,
    url: Annotated[str, Field(description="Public https URL of the file itself; redirects are not followed")],
    file_name: Annotated[Optional[str], Field(description="Name in Asana; defaults to the URL's file name")] = None,
) -> dict:
    """Download a file from a public https URL and attach it to a task."""
    token = _user_token()
    name = _safe_file_name(file_name or _file_name_from_url(url))
    try:
        response = await ssrf_safe_fetch_response(url, max_size=_max_upload_bytes(), timeout=20.0, overall_timeout=120.0)
    except SSRFError as e:
        raise ToolError(f"URL not allowed ({e}). Only public https URLs work.") from e
    except SSRFFetchError as e:
        raise ToolError(f"Could not download {url}: {e}") from e
    headers = {k.lower(): v for k, v in response.headers.items()}
    content_type = headers.get("content-type", "").split(";")[0].strip() or None
    return await anyio.to_thread.run_sync(_upload_as, token, task_gid, response.content, name, content_type)


# ========== Entry point ==========


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required environment variable {name} (see mcp_server/README.md)")
    return value


def build_auth():
    from asana_auth import AsanaProvider, build_storage

    allowed = {gid.strip() for gid in _required_env("ASANA_MCP_ALLOWED_USERS").split(",") if gid.strip()}
    redirect_uris = os.environ.get("ASANA_MCP_CLIENT_REDIRECT_URIS")
    jwt_signing_key = _required_env("MCP_JWT_SIGNING_KEY")
    storage = build_storage(
        dynamodb_table=os.environ.get("MCP_STORAGE_DYNAMODB_TABLE"),
        region=os.environ.get("AWS_REGION"),
        jwt_signing_key=jwt_signing_key,
    )
    if storage is not None:
        set_upload_store(storage)
    return AsanaProvider(
        client_id=_required_env("ASANA_OAUTH_CLIENT_ID"),
        client_secret=_required_env("ASANA_OAUTH_CLIENT_SECRET"),
        base_url=_required_env("MCP_BASE_URL"),
        allowed_user_gids=allowed,
        jwt_signing_key=jwt_signing_key,
        client_storage=storage,
        allowed_client_redirect_uris=redirect_uris.split(",") if redirect_uris else None,
    )


def main() -> None:
    for name in ("ASANA_ACCESS_TOKEN", "ASANA_OAUTH_SECRET"):
        if os.environ.get(name):
            raise SystemExit(f"{name} is set; unset it so no request can run as the server's own identity")
    _required_env("ASANA_WORKSPACE")
    mcp.auth = build_auth()
    mcp.run(
        transport="http",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        path="/mcp",
    )


if __name__ == "__main__":
    main()
