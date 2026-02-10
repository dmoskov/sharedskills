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

## Critical: Markdown Flag

`-m` / `--markdown` enables markdown-to-rich-text conversion. Two usage patterns:

```bash
# Pattern 1: -n for body, -m as toggle
asana create "Task" -n "## Summary\n- Point one" -m
asana update <gid> -n "**Done:** fixed bug" -m

# Pattern 2: -m with text (shorthand for -n "text" -m)
asana create "Task" -m "## Summary\n- Point one"
asana update <gid> -m "**Done:** fixed bug"

# comment: text is positional, -m is a flag
asana comment <gid> "### Update\nFixed the **bug**" -m
asana comment <gid> "plain text without formatting"         # no -m needed
```

Always use `-m` when text contains markdown (`**bold**`, `## headings`, `- lists`, `` `code` ``).
Without `-m`, text is posted as-is (literal asterisks, hashes, etc).

## Command Reference

### Read

```bash
asana workspaces                        # List workspaces
asana projects                          # List projects (add --archived for archived)
asana projects -l 100                   # Limit results

asana task <gid>                        # Full task details
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

asana my-tasks                          # All my tasks
asana my-tasks -i                       # My incomplete tasks

asana sections <project_gid>           # List sections (names only, use -v for GIDs)
asana custom-fields <project_gid>      # List custom fields

asana help search                       # Help for a specific command
```

### Write

```bash
# Create task
asana create "Task name"
asana create "Task name" -p <project_gid>
asana create "Task name" -p <gid> -a me -d 2026-03-15
asana create "Task name" -n "Plain description"
asana create "Task name" -n "## Rich description\n- bullet" -m
asana create "Task name" -p <gid> --custom-fields '{"<field_gid>": "value"}'

# Update task
asana update <gid> --name "New name"
asana update <gid> -n "New description" -m
asana update <gid> -c true              # Mark complete
asana update <gid> -c false             # Mark incomplete
asana update <gid> -a me                # Assign to self
asana update <gid> -a <user_gid>        # Assign to user
asana update <gid> -d 2026-03-15        # Set due date

# Comment
asana comment <gid> "Comment text"
asana comment <gid> "**Bold** comment with _formatting_" -m

# Organize
asana move <gid> -s <section_gid>                    # Move to section
asana move <gid> -s <section_gid> --after <task_gid>  # Position after task
asana set-parent <gid> -p <parent_gid>               # Make subtask
asana set-parent <gid> -p none                        # Remove parent
```

### Goals (uses asana_sdk)

```bash
asana goals                             # All goals in workspace
asana goals -t <team_gid>              # Filter by team
asana goals -p <time_period_gid>       # Filter by time period
asana goal <gid>                        # Goal details
asana create-goal "Goal name" --owner <user_gid> --notes "Description"
asana update-goal <gid> --status green --notes "On track"
asana goal-metric <gid> 75             # Update metric progress
```

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

When using `-m` flag, these are converted to Asana rich text:

- `# H1`, `## H2` (H3-H6 rendered as H2)
- `**bold**`, `*italic*`, `~~strikethrough~~`
- `` `inline code` `` and fenced code blocks
- `- unordered` and `1. ordered` lists
- `[text](url)` links
- `> blockquotes`
- `---` horizontal rules

## Common Agent Mistakes

1. **Forgetting `-m` on markdown content** → Without it, `**bold**` renders as literal asterisks
2. **Not using `-v` when GIDs are needed** → Default output omits GIDs for readability. Use `-v` to see them for follow-up commands.

## Configuration

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
