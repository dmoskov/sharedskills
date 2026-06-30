# Asana CLI Skill

Use `asana` for all Asana operations. Direct REST API with 30s timeouts and automatic retry.

## Output Flags

`--json` and `-v` work in any position (before or after subcommand):

```bash
asana --json tasks -p <gid>       # Before subcommand
asana tasks -p <gid> --json       # After subcommand
asana sections <gid> -v           # Show GIDs
```

`-v` controls whether GIDs are shown. Without it, output is clean names only.

## Markdown (Default)

Markdown-to-rich-text conversion is **on by default**. All text passed via `-n` or `-m` is converted to Asana rich text automatically.

```bash
# Markdown conversion happens automatically
asana create "Task" -n "## Summary\n- Point one"
asana update <gid> -n "**Done:** fixed bug"
asana comment <gid> "### Update\nFixed the **bug**"

# -m with text still works as shorthand for -n "text"
asana create "Task" -m "## Summary\n- Point one"
asana update <gid> -m "**Done:** fixed bug"

# Use --plain to disable markdown conversion (send as literal text)
asana create "Task" -n "Use the * operator" --plain
asana comment <gid> "raw text, no conversion" --plain
```

## Command Reference

### Read

```bash
asana workspaces                        # List workspaces
asana projects                          # List projects (add --archived for archived)
asana projects -l 100                   # Limit results

asana task <gid>                        # Full task details (shows subtask count if any)
asana task <gid> --subtasks             # Include subtask list inline
asana task <gid>                        # Description displayed as markdown by default
asana task <gid> --plain                # Display raw description without markdown conversion
asana subtasks <gid>                    # List subtasks
asana stories <gid>                     # Comments and activity
asana stories <gid> -l 20              # Limit to 20 entries

asana tasks -p <project_gid>           # Tasks in project (default: 100)
asana tasks -s <section_gid>           # Tasks in section
asana tasks -p <gid> -i                # Incomplete only
asana tasks -p <gid> -i -l 50         # Incomplete, limit 50
asana tasks -p <gid> -a me -i         # My incomplete tasks in project
asana tasks -p <gid> -a <user_gid>    # Tasks assigned to specific user
asana tasks -a me -i                   # All my incomplete tasks (any project)

asana search "query text"              # Search tasks
asana search "query" -i                # Incomplete only
asana search "query" -a me             # Assigned to me
asana search "query" -a <user_gid>     # Assigned to specific user
asana search "query" -p <project_gid>  # Within project
asana search -t "query" -i -l 20      # Text via flag, incomplete, limit 20
asana search "query" --custom-field <field_gid> <value_gid>  # Filter by custom field (repeatable)

asana my-tasks                          # All my tasks
asana my-tasks -i                       # My incomplete tasks

asana sections <project_gid>           # List sections (names only, use -v for GIDs)
asana custom-fields <project_gid>      # List custom fields

asana help search                       # Help for a specific command
```

### Dependencies
```bash
asana dep <task_gid>                             # Show blockers and dependents
asana dep add <task_gid> --blocked-by <gid>      # Task is blocked by another
asana dep add <task_gid> --blocks <gid>          # Task blocks another
asana dep add <task_gid> --blocked-by <a> <b>    # Multiple blockers at once
asana dep rm <task_gid> --blocked-by <gid>       # Remove a blocker
asana dep rm <task_gid> --blocks <gid>           # Remove a dependent
asana dep chain <gid1> <gid2> <gid3>             # Chain: gid1 → gid2 → gid3
```

### Write

```bash
# Create task
asana create "Task name"
asana create "Task name" -p <project_gid>
asana create "Task name" -p <gid> -a me -d 2026-03-15
asana create "Task name" -p <gid> --start 2026-03-01 -d 2026-03-15  # Date range
asana create "Task name" -n "Plain description"
asana create "Task name" -n "## Rich description\n- bullet"    # markdown by default
asana create "Task name" -p <gid> --custom-fields '{"<field_gid>": "value"}'

# Create a subtask (NOT added to the parent's project — see note below)
asana create "Subtask name" --parent <parent_gid>
asana create "Subtask name" --parent <parent_gid> -a me -d 2026-03-15

# Update task
asana update <gid> --name "New name"
asana update <gid> -n "New description"                       # markdown by default
asana update <gid> -c true              # Mark complete
asana update <gid> -c false             # Mark incomplete
asana update <gid> -a me                # Assign to self
asana update <gid> -a <user_gid>        # Assign to user
asana update <gid> -d 2026-03-15        # Set due date
asana update <gid> --start 2026-03-01 -d 2026-03-15  # Set date range
asana update <gid> --start ""           # Clear start date

# Recurrence (requires a due date on the task)
asana create "Weekly review" -d 2026-06-01 \
  --recurrence-json '{"type":"weekly","data":{"frequency":1}}'
asana update <gid> \
  --recurrence-json '{"type":"monthly","data":{"days_of_month":[15],"frequency":1}}'
asana update <gid> --recurrence-json ""  # Clear recurrence

# Comment
asana comment <gid> "Comment text"
asana comment <gid> "**Bold** comment with _formatting_"      # markdown by default

# Organize
asana move <gid> -s <section_gid>                    # Move to section
asana move <gid> -s <section_gid> --after <task_gid>  # Position after task
asana move <gid> -s <section_gid> --before <task_gid> # Position before task
asana set-parent <gid> -p <parent_gid>               # Make subtask
asana set-parent <gid> -p none                        # Remove parent

# Remove associations
asana remove <gid> -p <project_gid>    # Remove task from project
asana remove <gid> -t <tag_gid>        # Remove tag from task
```

**Subtasks and projects:** When building a task with subtasks, add **only the
parent** to the project. Create each subtask with `--parent <parent_gid>` and
**no** `-p/--project` — subtasks live under their parent and should not clutter
the project's task list. Only pass `--project` on a subtask if the user
explicitly wants it to also appear in a project.

```bash
parent=$(asana --json create "Ship feature" -p <project_gid> | jq -r .gid)
asana create "Write tests" --parent "$parent"   # subtask only, not in project
asana create "Update docs"  --parent "$parent"
```

### Goals

```bash
asana goals                             # All goals in workspace
asana goals -t <team_gid>              # Filter by team
asana goals -p <time_period_gid>       # Filter by time period
asana goal <gid>                        # Goal details
asana goal <gid> --subgoals             # Include sub-goals
asana create-goal "Goal name" --owner <user_gid> --notes "Description"
asana update-goal <gid> --status green --notes "On track"
asana goal-metric <gid> 75             # Update metric progress
```

### Status Updates

```bash
asana status-update create <parent_gid> "Title" --text "Body" --status on_track
asana status-update list <parent_gid>                # Recent status updates
asana status-update list <parent_gid> -l 10          # More results
asana status-update delete <status_update_gid>       # Delete a status update
```

Status types: `on_track`, `at_risk`, `off_track`, `on_hold`, `complete`, `achieved`, `partial`, `missed`, `dropped`.

**Note:** Setting a goal's status via `update-goal --status` auto-creates an empty status update. Delete it with `status-update delete`, then create one with content.

## Output Options

| Flag | Effect |
|------|--------|
| `--json` | Raw JSON output |
| `-v` / `--verbose` | Show GIDs in formatted output (sections, projects, workspaces, tasks) |

Default output shows clean names/data without GIDs. Use `-v` when you need GIDs for follow-up commands.

## Result Limits

Default limits: tasks=100, search=50. When results hit the limit, the CLI shows:

```
(100 tasks shown, more exist - use -l to increase limit)
```

Use `-l` to adjust:
```bash
asana tasks -p <gid> -l 200           # Fetch up to 200 tasks
asana search "query" -l 100            # Search up to 100 results
```

**Note:** When combining `-a` (assignee) with `-p` (project), the CLI delegates to the search API since `GET /tasks` doesn't support both filters together.

## Supported Markdown

These markdown features are converted to Asana rich text by default:

- `# H1`, `## H2` (H3-H6 rendered as H2)
- `**bold**`, `*italic*`, `~~strikethrough~~`
- `` `inline code` `` and fenced code blocks
- `- unordered` and `1. ordered` lists
- `[text](url)` links **and bare URLs** (auto-linked)
- GFM pipe tables → real Asana tables (header row bolded; Asana has no `<th>`)
- `> blockquotes`
- `---` horizontal rules

**Rich Asana links:** Any link to an `app.asana.com` URL — whether `[text](url)`
or a bare pasted URL — is auto-resolved by Asana into a rich object chip showing
the live task/project name. Just include the URL; no special syntax needed.

```bash
asana update <gid> -n "Blocked by https://app.asana.com/0/0/<task_gid>"
asana create "Report" -n "| Metric | Value |\n| --- | --- |\n| Users | 1.2k |"
```

## Task Recurrence

Asana's API supports task recurrence via a `recurrence` object on tasks but **doesn't document it**. The CLI exposes it as raw JSON passthrough.

```json
{"type": "weekly",  "data": {"frequency": 1}}
{"type": "monthly", "data": {"days_of_month": [15], "frequency": 1}}
{"type": "daily",   "data": {"frequency": 1}}
{"type": "never",   "data": null}   // clear
```

Caveats:
- **Requires a due date** — Asana rejects recurrence without `due_on` or `due_at`. The CLI raises `ValueError` on create if `-d` is missing; on update, the existing due date on the task counts.
- **Readback is partial** — `asana task <gid>` shows `type` + `frequency`, but Asana's REST response strips other inner fields you sent (e.g. `days_of_month`, `weekday`). The full rule is stored — visible in the Asana web UI — but not echoed back. This is a server quirk, not a CLI bug.
- **Undocumented field** — Shape may evolve. If something breaks, check the [forum thread](https://forum.asana.com/t/add-recurring-task-support-to-the-asana-api/1130930) for current state.

## Common Agent Mistakes

1. **Not using `-v` when GIDs are needed** → Default output omits GIDs for readability. Use `-v` to see them for follow-up commands.
2. **Using `--plain` when markdown is intended** → Only use `--plain` when you explicitly want literal text without rich formatting.
3. **Setting recurrence without a due date** → Always pair `--recurrence-json` with `-d`/`--due` on create.
4. **Adding subtasks to the project** → Use `--parent` (not `-p/--project`) for subtasks. Only the parent task belongs in the project; subtasks live under it.

## Project Configuration

Check for `.asana-config.json` in the project root at the start of any Asana operation. This is a **GID registry** — stable identifiers for the workspace's projects, sections, custom fields, users, and goals. Use its GIDs as defaults instead of asking the user. The `context` field explains when/how to use each resource.

This file is **not** for workflows, conventions, or agent logic — those belong in skills and agent definitions.

```json
{
  "workspace": { "gid": "...", "name": "..." },
  "projects": {
    "key": {
      "gid": "...", "name": "...", "context": "when to use this project",
      "sections": { "key": { "gid": "...", "name": "..." } }
    }
  },
  "custom_fields": {
    "key": {
      "gid": "...", "name": "...",
      "values": { "key": { "gid": "...", "name": "..." } }
    }
  },
  "users": { "key": { "gid": "...", "name": "..." } },
  "goals": { "key": { "gid": "...", "name": "..." } }
}
```

If no `.asana-config.json` exists, rely on env vars and ask for GIDs as needed.

## Environment

```bash
# Required: Personal access token
export ASANA_ACCESS_TOKEN="your_token"

# Optional: Default workspace GID
export ASANA_WORKSPACE="your_workspace_gid"
```

Or use OAuth:
```bash
cd asana && python3 oauth_setup.py
```
