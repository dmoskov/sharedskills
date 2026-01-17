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

## Requirements

```
requests>=2.25.0
```

## License

MIT
