# Asana Skill for Claude Code

A reliable, timeout-resistant skill for managing Asana tasks directly from Claude Code. This skill provides a fast alternative to MCP Asana tools that frequently timeout or hang.

## What This Does

The `/asana` skill lets you interact with Asana tasks directly from Claude Code sessions:

- **List workspaces and projects** to discover your Asana structure
- **Create tasks** with names, descriptions, and due dates
- **Read task details** including comments and activity
- **Update tasks** (mark complete, change fields)
- **Search tasks** by keyword
- **Manage comments** on tasks
- **Handle dependencies** between tasks

## Why This Exists

**Problem:** MCP Asana tools (`mcp__asana__*`) frequently timeout (20+ minutes) or hang entirely, making them unreliable for production use.

**Solution:** This skill uses direct REST API calls with:
- **30-second timeouts** on all requests (vs 20+ minute hangs)
- **Automatic retry** with exponential backoff
- **Clear error messages** when things go wrong
- **Reliable token refresh** via OAuth or environment variables

**Always use this skill instead of MCP Asana tools.**

## Quick Start

### 1. Get Authentication

**Option A: Personal Access Token (Quick)**
1. Go to [Asana Developer Console](https://app.asana.com/0/developer-console)
2. Click "Personal Access Tokens" → "Create New Token"
3. Copy the token and set: `export ASANA_ACCESS_TOKEN="your_token"`

**Option B: OAuth (Recommended)**
```bash
cd asana && python3 oauth_setup.py
```

### 2. Find Your Workspace

```bash
python3 asana_client.py workspaces
```

Optionally set default: `export ASANA_WORKSPACE="your_workspace_gid"`

### 3. Use the Skill

```bash
# List projects
/asana projects

# Search tasks
/asana search "authentication"

# Create a task
/asana create "Fix login bug" --project PROJECT_GID

# Mark complete
/asana update TASK_GID --completed true
```

## Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `workspaces` | List available workspaces | `/asana workspaces` |
| `projects` | List projects in workspace | `/asana projects` |
| `task <id>` | Get task details | `/asana task 1234567890` |
| `tasks --project <gid>` | List tasks in project | `/asana tasks --project 123 --incomplete` |
| `subtasks <id>` | List subtasks | `/asana subtasks 1234567890` |
| `search <query>` | Search tasks | `/asana search "bug"` |
| `my-tasks` | Your assigned tasks | `/asana my-tasks` |
| `stories <id>` | Task comments/activity | `/asana stories 1234567890` |
| `create` | Create task | `/asana create "Name" --project GID` |
| `update <id>` | Update task | `/asana update 123 --completed true` |
| `comment <id>` | Add comment | `/asana comment 123 "Done!"` |

## Troubleshooting

### "No Asana token found"
```bash
# Option 1: Set token directly
export ASANA_ACCESS_TOKEN="your_token"

# Option 2: Use OAuth
python3 oauth_setup.py
```

### "Workspace not found"
```bash
# List workspaces to find your GID
python3 asana_client.py workspaces

# Set default workspace
export ASANA_WORKSPACE="your_workspace_gid"
```

## Resources

- [Asana API Documentation](https://developers.asana.com/docs)
- [OAuth Setup Guide](https://developers.asana.com/docs/oauth)
- [Rate Limits](https://developers.asana.com/docs/rate-limits)
