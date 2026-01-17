# Letta Memory Hooks for Claude Code

Persistent memory system for Claude Code using [Letta](https://www.letta.com/) Cloud and local project files.

## Features

- **Global memories** stored in Letta Cloud (cross-project patterns, best practices)
- **Project memories** stored locally in `.memory/` (decisions, patterns, learnings)
- **Session logging** tracks file changes for review
- **Automatic deduplication** prevents storing similar memories
- **Context injection** surfaces relevant memories when you need them

## How It Works

### Session Start
When Claude Code starts, the `session_start.py` hook:
1. Loads your global memories from Letta Cloud
2. Loads project-specific memories from `.memory/`
3. Injects relevant context into the session

### During Conversation
The `prompt_submit.py` hook:
1. Analyzes your prompt for keywords
2. Searches both global and local memories
3. Surfaces relevant context to help Claude

### Tool Usage
The `post_tool.py` hook:
1. Logs Edit/Write/MultiEdit/Bash operations
2. Creates session activity log at `.memory/sessions/YYYY-MM-DD.session.jsonl`

### Session End
When the session ends:
1. `session_end_prepare.py` creates a session summary
2. Claude extracts valuable memories
3. `session_end_save.py` stores them appropriately

## Quick Start

```bash
# 1. Clone or download this repo
git clone https://github.com/your-org/ai-dev-tools.git

# 2. Run the installer
cd ai-dev-tools/letta
./install.sh

# 3. Add your Letta API key
echo "LETTA_API_KEY=your_key_here" > ~/.claude/hooks/letta/.env

# 4. Restart Claude Code
```

## Memory Tiers

### Global (Letta Cloud)
Cross-project learnings that apply everywhere:
- Best practices and patterns
- Framework knowledge
- Debugging techniques
- API quirks

### Project (Local `.memory/`)
Project-specific knowledge:
- Architecture decisions
- Local conventions
- Implementation details
- Troubleshooting steps

## Local Memory Structure

```
your-project/
└── .memory/
    ├── decisions/     # Architecture decisions
    │   └── use-postgres-over-mysql.md
    ├── patterns/      # Code patterns
    │   └── error-handling-convention.md
    ├── learnings/     # Bug fixes, insights
    │   └── websocket-reconnection-fix.md
    └── sessions/      # Activity logs
        └── 2024-01-15.session.jsonl
```

## Memory Format

Memories are extracted in this format:

```json
{
  "memories": [
    {
      "content": "When using React Query with SSR, always set staleTime > 0 to prevent hydration mismatches",
      "tier": "global",
      "category": "pattern",
      "reason": "Encountered this issue in multiple projects"
    },
    {
      "content": "API rate limiting is set to 100 req/min, use the RateLimiter class",
      "tier": "project",
      "category": "decision",
      "reason": "Important for new developers joining the project"
    }
  ]
}
```

## Configuration

Edit `~/.claude/hooks/letta/config.json`:

```json
{
  "agent_id": null,
  "settings": {
    "search_limit": 5,
    "dedup_threshold": 0.85,
    "max_archival_per_session": 10,
    "max_local_per_category": 50
  }
}
```

## Requirements

- Python 3.9+
- Claude Code
- Letta Cloud account (free tier available)

## Files

```
letta/
├── install.sh              # Installer script
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── SETUP.md                # Detailed setup guide
├── hooks/
│   ├── session_start.py    # Load memories at start
│   ├── prompt_submit.py    # Search relevant context
│   ├── post_tool.py        # Log tool usage
│   ├── session_end_prepare.py  # Prepare extraction
│   ├── session_end_save.py     # Save memories
│   └── utils/
│       ├── __init__.py
│       ├── letta_client.py    # Letta Cloud wrapper
│       ├── local_memory.py    # .memory/ operations
│       └── dedup.py           # Deduplication
└── templates/
    ├── config.json         # Config template
    └── env.example         # Environment template
```

## Troubleshooting

### Hooks not running
1. Check `~/.claude/settings.json` for hook configuration
2. Verify scripts are executable: `chmod +x ~/.claude/hooks/letta/*.py`
3. Check logs for errors

### Letta connection failed
1. Verify `LETTA_API_KEY` in `~/.claude/hooks/letta/.env`
2. Test connection: `python3 -c "from letta_client import Letta; Letta(token='your_key')"`

### Duplicate memories
Adjust `dedup_threshold` in config (0.85 = 85% similarity)

## License

MIT
