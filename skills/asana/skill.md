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

# Followers (creating a task makes you a follower)
asana followers rm <gid> me            # Stop following
asana followers add <gid> <user>...    # "me", email, or user GID

# Copies and templates (asynchronous in Asana; the CLI waits for the result)
asana duplicate <gid> "Copy name" --include notes,subtasks,assignee
asana duplicate <project_gid> "Copy name" --project
asana templates -p <project_gid>       # Task templates on a project
asana templates                        # Project templates
asana from-template <template_gid> ["Name"] [--project]

# Projects and out of office
asana project-search "words" --owner me   # Paid plans only
asana ooo                              # My out-of-office entries
asana ooo add 2030-01-02 2030-01-05

# Inbox (unarchived only; the API can't archive)
asana -v inbox                         # List notifications with GIDs
asana inbox read <notif_gid>...        # Mark read
asana inbox unread <notif_gid>...      # Mark unread (also unarchives)
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

### Tables & Records

A **record** is a row in an Asana **table**: durable metadata about an object
(a company, a vendor, a customer account) that you keep updating. A **task** is
work that gets done and closed. Use a record when the thing outlives any piece
of work about it; use a task for the work, and point the task at the record by
pasting the record URL in its description.

Records are their own object type. Task commands (`task`, `tasks`, `search`)
never return them, and `asana task <record_gid>` fails with 404.

```bash
asana -v tables                                  # Tables in the workspace
asana table <table_gid>                          # Columns: names, GIDs, types, enum options
asana create-table "Accounts"
asana add-column <table_gid> "Domain"            # text (default)
asana add-column <table_gid> "Stage" --type enum -o Lead -o Customer -o Churned
asana add-column <table_gid> "Tags" --type multi_enum -o Partner -o Reseller
asana add-column <table_gid> "Employees" --type number --precision 0
asana add-column <table_gid> "Since" --type date
asana add-column <table_gid> "Owner" --type people
asana add-column <table_gid> --custom-field <field_gid>   # Reuse an existing global field
asana delete-table <table_gid>                   # Deletes its records; columns stay in the workspace

asana -v records <table_gid>                     # Every record, all pages, with values
asana records <table_gid> --modified-since 2026-01-01T00:00:00Z
asana record <record_gid>                        # Values, URL, and comments
asana create-record "Acme" -t <table_gid> -f "Domain=acme.example" -f "Stage=Lead"
asana update-record <record_gid> -f "Stage=Customer" --name "Acme Inc"
asana upsert-record "Acme" -t <table_gid> -k Domain -f "Domain=acme.example" -f "Stage=Lead"
asana import-records <table_gid> accounts.csv -k Domain       # Bulk upsert (CSV/JSONL/JSON)
asana import-records <table_gid> accounts.csv -k Domain --dry-run --skip-empty
asana record-comment <record_gid> "Renewal call booked"
asana search-records "acme" -t <table_gid>
asana delete-record <record_gid>
```

**Names, not GIDs.** `-f "Column=value"` (repeatable) and `--fields-json
'{"Column": value}'` take column **names** and enum option **names**, matched
case-insensitively; the CLI reads the table's columns and sends GIDs. GIDs are
accepted too. Values by type: text as-is; number parsed; enum one option name;
multi_enum and people comma-separated (people take `me`, an email, or a user
GID); date `YYYY-MM-DD`. An empty value (`-f "Stage="`) clears the field. A
misspelled column or option fails before anything is written, listing the valid
ones.

**Upsert by key.** `upsert-record -k <column>` (or `-k name`) treats that column
as the object's identity. The key value is sent as the record's
`unique_fingerprint`, so Asana refuses a second record with the same key (409).
On a 409 the CLI finds the existing record by scanning the table for the key
value and updates it. Asana's 409 carries no GID and the fingerprint can't be
read back, so the key must also be stored in a column (or be the name).
`import-records` reads the table once, updates rows whose key matches (case-
insensitive), and upserts the rest; the row's `Name` column (`--name-column`)
is the record name and every other column header must match a table column.
It prints created/updated/skipped/failed counts and exits 1 if any row failed.

Gotchas:
- **No description, no attachments.** Records have a name, column values, and
  comments. Anything long goes in a text column or a comment.
- **Columns first.** A record can only hold values for columns already on its
  table; there's no force-write. `add-column` creates a workspace-global custom
  field (tables only take global fields), so pick names that won't collide.
- **Deleting a table leaves its columns** as workspace custom fields. Delete them
  separately if they were only for that table.
- **Task reference fields can't point at records.** Store the record GID or URL
  (`https://app.asana.com/1/<workspace_gid>/record/<record_gid>`) in a text field
  or the task description.
- **Search** (`search-records`) is Premium-only (402 otherwise), needs text or
  `-t`, returns one page (max 100), and lags writes by 10-60s. For
  read-your-writes or a complete list, use `records`.
- **Records created outside the CLI** have no fingerprint, so `upsert-record`'s
  create can succeed and make a duplicate. `import-records` matches on the key
  column first, so it doesn't.
- Record comments show in `record`; field-change history isn't returned.

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
5. **Looking for records with task commands** → Records aren't tasks. Use `records`, `record`, and `search-records`.
6. **Passing GIDs to record commands by hand** → Use column and option names with `-f`; run `asana table <gid>` to see them.

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
