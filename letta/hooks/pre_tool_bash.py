#!/usr/bin/env python3
"""
Pre Tool Use Hook - Bash Permission Prompt

Prompts the user for permission before executing any bash command.
Exit codes:
  0 = Allow (skip prompt)
  1 = Prompt user for confirmation
  2 = Block with error message

Configure which commands require prompts by editing ALLOW_PATTERNS.
"""

import json
import re
import sys


# Commands that are always allowed without prompting
ALLOW_PATTERNS = [
    r'^ls\b',           # List files
    r'^pwd$',           # Print working directory
    r'^echo\s',         # Echo (for debugging)
    r'^cat\s',          # View files
    r'^head\b',         # View file head
    r'^tail\b',         # View file tail
    r'^wc\b',           # Word count
    r'^find\b',         # Find files
    r'^which\b',        # Find executables
    r'^type\b',         # Command type
    r'^file\b',         # File type
    r'^stat\b',         # File stats
    r'^git\s+status',   # Git status
    r'^git\s+log',      # Git log
    r'^git\s+diff',     # Git diff
    r'^git\s+branch',   # Git branch (list)
    r'^git\s+show',     # Git show
    r'^git\s+remote\s+-v',  # Git remotes
]

# Commands that are always blocked (supplement dangerous_command_filter.py)
BLOCK_PATTERNS = [
    r'sudo\s+rm\s+-rf\s+/',
    r'>\s*/dev/sda',
]


def main():
    try:
        hook_data = json.load(sys.stdin)
    except (json.JSONDecodeError, IOError):
        sys.exit(0)  # Allow on parse error

    # Only handle Bash tool
    tool_name = hook_data.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    command = hook_data.get("tool_input", {}).get("command", "").strip()
    if not command:
        sys.exit(0)

    # Check block patterns first
    for pattern in BLOCK_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            print(f"Blocked: {command[:100]}", file=sys.stderr)
            sys.exit(2)

    # Check allow patterns - skip prompt for safe read-only commands
    for pattern in ALLOW_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            sys.exit(0)

    # Everything else: prompt user for confirmation
    desc = hook_data.get("tool_input", {}).get("description", "")
    if desc:
        print(f"Command: {desc}", file=sys.stderr)
    print(f"$ {command[:200]}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
