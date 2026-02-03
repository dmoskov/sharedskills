# Asana Direct API Skill

**ALWAYS USE THIS SKILL INSTEAD OF MCP ASANA TOOLS**

MCP Asana tools frequently timeout (20+ minutes) or hang entirely. This skill uses direct REST API calls and is far more reliable.

## Usage

```
/asana <command> [args]
```

## Commands

### Read Commands
- `workspaces` - List available workspaces
- `projects` - List projects in workspace
- `task <id>` - Get task details
- `tasks --project <gid>` - List tasks in project
- `subtasks <id>` - Get subtasks of a task
- `search <query>` - Search tasks
- `my-tasks` - Tasks assigned to current user
- `stories <id>` - Get task comments/activity

### Write Commands
- `create "<name>" --project <gid>` - Create a new task
- `update <id> --completed true` - Update task
- `comment <id> "<message>"` - Add comment to task

## Configuration

Set these environment variables:

```bash
# Required: Get token from https://app.asana.com/0/developer-console
export ASANA_ACCESS_TOKEN="your_token"

# Optional: Default workspace (discover with: /asana workspaces)
export ASANA_WORKSPACE="your_workspace_gid"
```

Or use OAuth (recommended for production):
```bash
cd asana && python3 oauth_setup.py
```

## Instructions

When invoked, run from the `asana/` directory in ai-dev-tools:

### For `workspaces`:
```bash
python3 asana_client.py workspaces
```

### For `projects`:
```bash
python3 asana_client.py projects
```

### For `task <id>`:
```bash
python3 asana_client.py task <task_id>
```

### For `tasks --project <gid>`:
```bash
python3 asana_client.py tasks --project <project_gid> --incomplete
```

### For `subtasks <id>`:
```bash
python3 asana_client.py subtasks <task_id>
```

### For `search <query>`:
```bash
python3 asana_client.py search "<query>"
```

### For `my-tasks`:
```bash
python3 asana_client.py my-tasks
```

### For `stories <id>`:
```bash
python3 asana_client.py stories <task_id>
```

### For `create "<name>" --project <gid>`:
```bash
python3 asana_client.py create "<name>" --project <project_gid> [--notes "<description>"] [--due-on YYYY-MM-DD]
```

### For `update <id> [options]`:
```bash
python3 asana_client.py update <task_id> --completed true
```

### For `comment <id> "<message>"`:
```bash
python3 asana_client.py comment <task_id> "<message>"
```

## Python API

```python
from asana_client import AsanaClient

client = AsanaClient()

# List workspaces
workspaces = client.list_workspaces()

# Search tasks
tasks = client.search_tasks(text="keyword", completed=False)

# Create task
task = client.create_task(name="Task name", project="PROJECT_GID")

# Update task
client.update_task("TASK_GID", completed=True)

# Add comment
client.create_story("TASK_GID", "Comment text")

# Manage dependencies
client.add_dependency(dependent_gid, dependency_gid)
client.chain_dependencies(["task1", "task2", "task3"])
```

## Why This Exists

MCP Asana tools frequently timeout (20+ minutes) or hang entirely. This skill uses direct REST API calls with:
- 30-second timeouts on all requests
- Automatic retry with exponential backoff
- Clear error messages
- Reliable token refresh

**NEVER use MCP Asana tools (`mcp__asana__*`). Always use this skill instead.**
