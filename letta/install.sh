#!/bin/bash
#
# Letta Hooks Installer for Claude Code
#
# This script:
# 1. Copies hook scripts to ~/.claude/hooks/letta/
# 2. Creates config template
# 3. Updates ~/.claude/settings.json with hook configuration
# 4. Installs Python dependencies
#
# Usage:
#   ./install.sh
#   ./install.sh --uninstall
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DIR="$HOME/.claude/hooks/letta"
SETTINGS_FILE="$HOME/.claude/settings.json"
CONFIG_FILE="$HOOKS_DIR/config.json"
ENV_FILE="$HOOKS_DIR/.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

uninstall() {
    log_info "Uninstalling Letta hooks..."

    if [ -d "$HOOKS_DIR" ]; then
        rm -rf "$HOOKS_DIR"
        log_info "Removed $HOOKS_DIR"
    fi

    if [ -f "$SETTINGS_FILE" ]; then
        # Remove hook entries from settings (simplified - just warn user)
        log_warn "Please manually remove Letta hook entries from $SETTINGS_FILE"
    fi

    log_info "Uninstall complete"
    exit 0
}

# Handle uninstall flag
if [ "$1" = "--uninstall" ]; then
    uninstall
fi

log_info "Installing Letta hooks for Claude Code..."

# 1. Create hooks directory
log_info "Creating hooks directory at $HOOKS_DIR"
mkdir -p "$HOOKS_DIR/utils"

# 2. Copy hook scripts
log_info "Copying hook scripts..."
cp "$SCRIPT_DIR/hooks/session_start.py" "$HOOKS_DIR/"
cp "$SCRIPT_DIR/hooks/prompt_submit.py" "$HOOKS_DIR/"
cp "$SCRIPT_DIR/hooks/post_tool.py" "$HOOKS_DIR/"
cp "$SCRIPT_DIR/hooks/session_end_prepare.py" "$HOOKS_DIR/"
cp "$SCRIPT_DIR/hooks/session_end_save.py" "$HOOKS_DIR/"
cp "$SCRIPT_DIR/hooks/pre_tool_bash.py" "$HOOKS_DIR/"

# Copy utils
cp "$SCRIPT_DIR/hooks/utils/__init__.py" "$HOOKS_DIR/utils/"
cp "$SCRIPT_DIR/hooks/utils/letta_client.py" "$HOOKS_DIR/utils/"
cp "$SCRIPT_DIR/hooks/utils/local_memory.py" "$HOOKS_DIR/utils/"
cp "$SCRIPT_DIR/hooks/utils/dedup.py" "$HOOKS_DIR/utils/"

# Make scripts executable
chmod +x "$HOOKS_DIR/"*.py

# 3. Create config file if it doesn't exist
if [ ! -f "$CONFIG_FILE" ]; then
    log_info "Creating config file..."
    cp "$SCRIPT_DIR/templates/config.json" "$CONFIG_FILE"
fi

# 4. Create .env template if it doesn't exist
if [ ! -f "$ENV_FILE" ]; then
    log_info "Creating .env template..."
    cp "$SCRIPT_DIR/templates/env.example" "$ENV_FILE"
    log_warn "Please edit $ENV_FILE and add your LETTA_API_KEY"
fi

# 5. Install Python dependencies
log_info "Installing Python dependencies..."
pip3 install --quiet letta-client python-dotenv || {
    log_warn "Failed to install Python packages. Please run manually:"
    echo "  pip3 install letta-client python-dotenv"
}

# 6. Update settings.json
log_info "Updating Claude Code settings..."

# Create settings directory if needed
mkdir -p "$(dirname "$SETTINGS_FILE")"

# Create settings file if it doesn't exist
if [ ! -f "$SETTINGS_FILE" ]; then
    echo '{}' > "$SETTINGS_FILE"
fi

# Check if hooks are already configured
if grep -q "letta/session_start.py" "$SETTINGS_FILE" 2>/dev/null; then
    log_info "Letta hooks already configured in settings.json"
else
    # Use Python to safely merge hooks into settings
    python3 - "$SETTINGS_FILE" << 'PYTHON_SCRIPT'
import json
import sys

settings_file = sys.argv[1]

# Load existing settings
try:
    with open(settings_file, 'r') as f:
        settings = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    settings = {}

# Initialize hooks if not present
if 'hooks' not in settings:
    settings['hooks'] = {}

hooks = settings['hooks']

# Add SessionStart hook (new format requires hooks array wrapper)
if 'SessionStart' not in hooks:
    hooks['SessionStart'] = []
hooks['SessionStart'].append({
    "hooks": [{
        "type": "command",
        "command": "~/.claude/hooks/letta/session_start.py",
        "timeout": 30
    }]
})

# Add UserPromptSubmit hook
if 'UserPromptSubmit' not in hooks:
    hooks['UserPromptSubmit'] = []
hooks['UserPromptSubmit'].append({
    "hooks": [{
        "type": "command",
        "command": "~/.claude/hooks/letta/prompt_submit.py",
        "timeout": 10
    }]
})

# Add PreToolUse hook for bash permission prompts
if 'PreToolUse' not in hooks:
    hooks['PreToolUse'] = []
hooks['PreToolUse'].append({
    "matcher": "Bash",
    "hooks": [{
        "type": "command",
        "command": "~/.claude/hooks/letta/pre_tool_bash.py",
        "timeout": 5
    }]
})

# Add PostToolUse hook (already has correct format with matcher)
if 'PostToolUse' not in hooks:
    hooks['PostToolUse'] = []
hooks['PostToolUse'].append({
    "matcher": "Edit|Write|MultiEdit|Bash",
    "hooks": [{
        "type": "command",
        "command": "~/.claude/hooks/letta/post_tool.py",
        "timeout": 5
    }]
})

# Add SessionEnd hooks
if 'SessionEnd' not in hooks:
    hooks['SessionEnd'] = []
hooks['SessionEnd'].extend([
    {
        "hooks": [{
            "type": "command",
            "command": "~/.claude/hooks/letta/session_end_prepare.py",
            "timeout": 10
        }]
    },
    {
        "hooks": [{
            "type": "prompt",
            "prompt": "Extract memories from session. Output JSON: {\"memories\": [{\"content\": \"...\", \"tier\": \"global|project\", \"category\": \"decision|pattern|learning\", \"reason\": \"...\"}]}"
        }]
    },
    {
        "hooks": [{
            "type": "command",
            "command": "~/.claude/hooks/letta/session_end_save.py",
            "timeout": 30
        }]
    }
])

# Save updated settings
with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

print("Hooks added to settings.json")
PYTHON_SCRIPT
fi

log_info "Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Get a Letta API key from https://www.letta.com/"
echo "  2. Add your key to $ENV_FILE"
echo "  3. Restart Claude Code"
echo ""
echo "To verify installation:"
echo "  python3 $HOOKS_DIR/session_start.py"
