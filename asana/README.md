# Asana CLI Tool

Direct REST API client for Asana task management. All operations have 30-second timeouts and automatic retries.

## Features

- 30-second timeouts on all requests (vs MCP tools that can hang)
- Automatic retry with exponential backoff
- Clear, actionable error messages
- No external dependencies beyond `requests`
- Works as CLI or Python library

## Setup

1. Get a Personal Access Token from https://app.asana.com/0/my-apps
2. Set the environment variable: `export ASANA_ACCESS_TOKEN=your_token_here`
3. Optionally set default workspace: `export ASANA_WORKSPACE=your_workspace_gid`

See [SETUP.md](SETUP.md) for detailed instructions.

## Quick Start

```bash
# Install dependencies
pip install requests

# Test your setup
python3 asana_client.py workspaces

# Get your tasks
python3 asana_client.py my-tasks -i
```

## Commands

### Read Operations

| Command | Description |
|---------|-------------|
| `task <gid>` | Get task details |
| `tasks --project <gid>` | List tasks in project |
| `subtasks <gid>` | Get subtasks of a task |
| `search <query>` | Search tasks by text |
| `my-tasks` | Tasks assigned to me |
| `projects` | List all projects |
| `sections <project_gid>` | List sections in project |
| `stories <task_gid>` | Get task activity history |
| `workspaces` | List all workspaces |

### Write Operations

| Command | Description |
|---------|-------------|
| `create <name>` | Create a task |
| `update <gid> [options]` | Update a task |
| `comment <gid> <text>` | Add comment to task |

## Examples

```bash
# Get task details
python3 asana_client.py task 1234567890

# Search incomplete tasks
python3 asana_client.py search "bug fix" -i

# List my incomplete tasks
python3 asana_client.py my-tasks -i

# Create a task
python3 asana_client.py create "Fix login bug" --project 1234567890 --due 2024-12-31

# Complete a task
python3 asana_client.py update 1234567890 --completed true

# Add a comment
python3 asana_client.py comment 1234567890 "Fixed in commit abc123"

# Get JSON output
python3 asana_client.py task 1234567890 --json
```

## Options

### Create options

- `--project <gid>` or `-p <gid>` - Add to project
- `--assignee <gid|me>` or `-a` - Assign to user
- `--due <YYYY-MM-DD>` or `-d` - Set due date
- `--notes <text>` or `-n` - Add description

### Update options

- `--name <text>` - Change task name
- `--completed true|false` or `-c` - Mark complete/incomplete
- `--assignee <gid|me>` or `-a` - Reassign
- `--due <YYYY-MM-DD>` or `-d` - Change due date

### Common flags

- `--json` - Output raw JSON
- `-v, --verbose` - Show task GIDs in listings
- `-i, --incomplete` - Filter to incomplete tasks only
- `-l, --limit <n>` - Limit number of results

## Library Usage

```python
from asana_client import AsanaClient

client = AsanaClient()

# Search tasks
tasks = client.search_tasks(text="bug", completed=False)

# Create task
task = client.create_task(
    name="Fix the thing",
    project="1234567890",
    assignee="me",
    due_on="2024-12-31"
)

# Update task
client.update_task(task["gid"], completed=True)

# Add comment
client.add_comment(task["gid"], "Done!")
```

### Portfolio Operations

```python
# List portfolios
portfolios = client.get_portfolios()

# Get portfolio details
portfolio = client.get_portfolio("portfolio_gid")

# Get projects in a portfolio
items = client.get_portfolio_items("portfolio_gid")
```

### Team Operations

```python
# List teams in organization
teams = client.get_teams()

# Get team details
team = client.get_team("team_gid")

# Get team members
members = client.get_team_members("team_gid")
```

### Tag Operations

```python
# List tags
tags = client.get_tags()

# Create a tag
tag = client.create_tag(name="urgent", color="red")

# Add/remove tags from tasks
client.add_tag_to_task("task_gid", "tag_gid")
client.remove_tag_from_task("task_gid", "tag_gid")

# Update or delete tags
client.update_tag("tag_gid", name="critical")
client.delete_tag("tag_gid")
```

### Section Operations

```python
# List sections in a project
sections = client.get_project_sections("project_gid")

# Create a section
section = client.create_section("project_gid", "In Review")

# Update section name
client.update_section("section_gid", "Done")

# Move/reorder a section
client.move_section("project_gid", "section_gid", after_section="other_section_gid")

# Delete a section
client.delete_section("section_gid")
```

### Dependency Operations

```python
# Get task dependencies
deps = client.get_dependencies("task_gid")

# Add dependencies
client.add_dependency("task_gid", "depends_on_gid")
client.add_dependencies("task_gid", ["dep1", "dep2", "dep3"])

# Chain tasks sequentially (B depends on A, C depends on B, etc.)
client.chain_dependencies(["task_a", "task_b", "task_c"])

# Remove dependency
client.remove_dependency("task_gid", "depends_on_gid")

# Get tasks that depend on this task
dependents = client.get_dependents("task_gid")
```

## Advanced: Using the Official SDK

For features not covered by `asana_client.py`, use the official SDK with managed auth:

```python
from asana_sdk import get_client
import asana

# Get client with OAuth token management
client = get_client()

# Use any SDK API directly
goals_api = asana.GoalsApi(client)
goals = goals_api.get_goals(opts={"workspace": "workspace_gid"})
```

## Requirements

```
requests>=2.25.0
```

## License

MIT
