#!/usr/bin/env python3
"""
Post Tool Use Hook for Claude Code.

Logs Edit/Write/MultiEdit/Bash tool calls to session log.
Useful for tracking what changes were made during a session.

Input (stdin):
    JSON with tool call information including:
    - tool_name: Name of the tool used
    - tool_input: Input parameters
    - tool_output: Output/result (may be truncated)

Output:
    No output (just logs to .memory/sessions/)
"""

import json
import os
import sys
from pathlib import Path

# Add hooks directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.local_memory import LocalMemory


def main():
    """Log tool usage to session log."""
    # Read tool call info from stdin
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, IOError):
        return

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only log file modification tools
    if tool_name not in ("Edit", "Write", "MultiEdit", "Bash"):
        return

    # Initialize local memory
    try:
        local = LocalMemory()
        local.initialize()  # Ensure .memory dir exists
    except Exception as e:
        print(f"<!-- Failed to initialize local memory: {e} -->", file=sys.stderr)
        return

    # Prepare log entry
    if tool_name == "Edit":
        event_data = {
            "file": tool_input.get("file_path", ""),
            "old_string_preview": (tool_input.get("old_string", ""))[:100],
            "new_string_preview": (tool_input.get("new_string", ""))[:100],
        }
    elif tool_name == "MultiEdit":
        event_data = {
            "file": tool_input.get("file_path", ""),
            "edit_count": len(tool_input.get("edits", [])),
        }
    elif tool_name == "Write":
        event_data = {
            "file": tool_input.get("file_path", ""),
            "content_length": len(tool_input.get("content", "")),
        }
    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        event_data = {
            "command_preview": command[:200] if command else "",
        }
    else:
        event_data = {}

    # Log the event
    try:
        local.log_session_event(tool_name.lower(), event_data)
    except Exception as e:
        print(f"<!-- Failed to log event: {e} -->", file=sys.stderr)


if __name__ == "__main__":
    main()
