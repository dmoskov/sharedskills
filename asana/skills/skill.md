# Asana CLI Skill

Use `asana` for all Asana operations. Direct REST API with 30s timeouts and automatic retry.

## Critical: Flag Positioning

`--json` and `-v` are **top-level flags** and MUST come BEFORE the subcommand:

```bash
asana --json tasks -p <gid>       # CORRECT
asana -v sections <project_gid>   # CORRECT
asana tasks -p <gid> --json       # WRONG - will error
asana sections <gid> -v           # WRONG - will error
```

## Critical: Markdown Flag

`-m` / `--markdown` is a **boolean toggle**, not a value flag. It converts the text in `-n` (notes) or the comment positional arg to Asana rich text. Never pass text after `-m`.

```bash
# create: body goes in -n, markdown toggle is -m
asana create "Task" -n "## Summary\n- Point one" -m       # CORRECT
asana create "Task" -m "## Summary"                        # WRONG - -m takes no value

# update: same pattern
asana update <gid> -n "**Done:** fixed bug" -m             # CORRECT

# comment: text is positional, -m is a flag
asana comment <gid> "### Update\nFixed the **bug**" -m     # CORRECT
asana comment <gid> "plain text without formatting"         # CORRECT (no -m needed)
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

asana search "query text"              # Search tasks
asana search "query" -i                # Incomplete only
asana search "query" -a me             # Assigned to me
asana search "query" -a <user_gid>     # Assigned to specific user
asana search "query" -p <project_gid>  # Within project
asana search -t "query" -i -l 20      # Text via flag, incomplete, limit 20

asana my-tasks                          # All my tasks
asana my-tasks -i                       # My incomplete tasks

asana sections <project_gid>           # List sections in project
asana custom-fields <project_gid>      # List custom fields
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

| Flag | Position | Effect |
|------|----------|--------|
| `--json` | Before subcommand | Raw JSON output |
| `-v` / `--verbose` | Before subcommand | Show GIDs in formatted output |

```bash
asana --json task <gid>              # JSON output
asana -v tasks -p <gid>             # Show GIDs in table
asana --json -v tasks -p <gid>      # Both flags
```

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

1. **Putting `--json`/`-v` after the subcommand** → Use `asana --json <cmd>` not `asana <cmd> --json`
2. **Passing text to `-m`** → `-m` is a boolean flag. Body text goes in `-n` (create/update) or as positional arg (comment)
3. **Forgetting `-m` on markdown content** → Without it, `**bold**` renders as literal asterisks
4. **Using `tasks` when `search` is needed** → `tasks` filters by project/section only. For assignee filtering, use `search -a`
5. **Assuming all results are returned** → Default limits: tasks=100, search=50. Use `-l` to adjust. When count equals limit, there may be more results.

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
