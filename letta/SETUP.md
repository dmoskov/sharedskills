# Letta Hooks Setup Guide

This guide walks through setting up persistent memory for Claude Code using Letta Cloud.

## Prerequisites

- Python 3.9 or higher
- Claude Code installed
- A Letta account (free tier available)

## Step 1: Get a Letta API Key

1. Go to [https://www.letta.com/](https://www.letta.com/)
2. Sign up or log in
3. Navigate to Settings → API Keys
4. Create a new API key
5. Copy the key (you won't be able to see it again)

## Step 2: Install the Hooks

### Automatic Installation

```bash
cd ai-dev-tools/letta
./install.sh
```

This will:
- Copy hooks to `~/.claude/hooks/letta/`
- Install Python dependencies
- Update `~/.claude/settings.json`
- Create config templates

### Manual Installation

If the installer fails, you can set up manually:

1. Create the hooks directory:
   ```bash
   mkdir -p ~/.claude/hooks/letta/utils
   ```

2. Copy hook files:
   ```bash
   cp hooks/*.py ~/.claude/hooks/letta/
   cp hooks/utils/*.py ~/.claude/hooks/letta/utils/
   chmod +x ~/.claude/hooks/letta/*.py
   ```

3. Install Python packages:
   ```bash
   pip install letta-client python-dotenv
   ```

4. Create config file at `~/.claude/hooks/letta/config.json`:
   ```json
   {
     "agent_id": null,
     "settings": {
       "search_limit": 5,
       "dedup_threshold": 0.85
     }
   }
   ```

5. Add hooks to `~/.claude/settings.json`:
   ```json
   {
     "hooks": {
       "SessionStart": [
         {"type": "command", "command": "~/.claude/hooks/letta/session_start.py", "timeout": 30}
       ],
       "UserPromptSubmit": [
         {"type": "command", "command": "~/.claude/hooks/letta/prompt_submit.py", "timeout": 10}
       ],
       "PostToolUse": [
         {"matcher": "Edit|Write|MultiEdit|Bash", "hooks": [
           {"type": "command", "command": "~/.claude/hooks/letta/post_tool.py", "timeout": 5}
         ]}
       ],
       "SessionEnd": [
         {"type": "command", "command": "~/.claude/hooks/letta/session_end_prepare.py", "timeout": 10},
         {"type": "prompt", "prompt": "Extract memories from session. Output JSON: {\"memories\": [{\"content\": \"...\", \"tier\": \"global|project\", \"category\": \"decision|pattern|learning\", \"reason\": \"...\"}]}"},
         {"type": "command", "command": "~/.claude/hooks/letta/session_end_save.py", "timeout": 30}
       ]
     }
   }
   ```

## Step 3: Configure Your API Key

Create the environment file:

```bash
echo "LETTA_API_KEY=your_key_here" > ~/.claude/hooks/letta/.env
```

Or edit the file directly:

```bash
nano ~/.claude/hooks/letta/.env
```

Add:
```
LETTA_API_KEY=letta_...your_actual_key...
```

## Step 4: Verify Installation

Test the session start hook:

```bash
cd ~/.claude/hooks/letta
python3 session_start.py
```

You should see either:
- Memory context output (if agent exists)
- Or a brief error about missing agent (normal on first run)

## Step 5: Restart Claude Code

Close and reopen Claude Code. The hooks will now be active.

## Configuration Options

### `~/.claude/hooks/letta/config.json`

| Setting | Default | Description |
|---------|---------|-------------|
| `agent_id` | `null` | Auto-populated on first run |
| `search_limit` | `5` | Max memories to surface per search |
| `dedup_threshold` | `0.85` | Similarity threshold for deduplication (0-1) |
| `max_archival_per_session` | `10` | Max global memories to save per session |
| `max_local_per_category` | `50` | Max local memories per category |

### Hook Timeouts

Default timeouts in settings.json:

| Hook | Timeout | Purpose |
|------|---------|---------|
| SessionStart | 30s | Loading memories can take time |
| UserPromptSubmit | 10s | Search should be fast |
| PostToolUse | 5s | Just logging, should be quick |
| SessionEndPrepare | 10s | Summary generation |
| SessionEndSave | 30s | Saving to cloud + local |

Adjust timeouts in `~/.claude/settings.json` if needed.

## Using Project-Local Memory

To enable local memory for a project, the hooks will automatically create `.memory/` when needed.

To manually initialize:

```bash
mkdir -p .memory/{decisions,patterns,learnings,sessions}
```

### Add to .gitignore

The session logs can be large. Add to your `.gitignore`:

```
.memory/sessions/
```

Keep the memory files themselves in version control so team members benefit.

## Troubleshooting

### "No Letta API key provided"

The environment variable isn't being read. Check:

1. The `.env` file exists at `~/.claude/hooks/letta/.env`
2. It contains `LETTA_API_KEY=your_actual_key`
3. The key is valid (try it at letta.com)

### Hooks not running

1. Check settings.json has the hook entries
2. Verify hooks are executable: `ls -la ~/.claude/hooks/letta/`
3. Check for Python errors: `python3 ~/.claude/hooks/letta/session_start.py`

### Memory search returns nothing

1. Verify memories exist: Check Letta Cloud dashboard
2. Try a broader search term
3. Check `search_limit` setting

### Too many duplicate warnings

Lower the `dedup_threshold` in config.json (e.g., 0.75 for less strict matching)

### Hooks are slow

1. Reduce `search_limit` for faster searches
2. Check your network connection to Letta Cloud
3. Consider using a local Letta server for development

## Uninstalling

```bash
./install.sh --uninstall
```

Or manually:

```bash
rm -rf ~/.claude/hooks/letta
# Then remove hook entries from ~/.claude/settings.json
```

## Support

- Letta documentation: [https://docs.letta.com/](https://docs.letta.com/)
- Claude Code hooks: Check Claude Code documentation
- Issues: Open an issue in this repository
