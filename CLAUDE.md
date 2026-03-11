# Shared Skills & Tools

Cross-project shared utilities for Dustin's AI development ecosystem.

## Structure

- **`asana/`** — Asana client library and SDK. Used by all projects via `sys.path.insert(0, "ai-dev-tools/asana")`.
  - `asana_client.py` — Unified Asana client (PAT auth preferred)
  - `asana_sdk/` — Full SDK: tasks, projects, custom_fields, goals, attachments, users
  - `bin/asana` — CLI tool
- **`letta/`** — Letta agent integration: hooks, session management, templates
- **`skills/`** — Claude Code skills (SKILL.md format)
  - `asana/` — Asana CLI skill
  - `rlm/` — Recursive Language Model for long-context decomposition
- **`tools/`** — Letta agent tools (installed on all agents)
  - `aws_tool.py`, `claude_tool.py`, `db_query_tool.py`, `fetch_webpage_tool.py`, `semantic_search_tool.py`, `web_search_tool.py`

## Important

- This repo is **PUBLIC**. Generic skills only. Project-specific code goes in project repos.
- `sharedskills/` symlink → `tools/` for backward compatibility.
- `asana/` path must not change — 5+ files across repos import from it.
