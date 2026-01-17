#!/usr/bin/env python3
"""
Session Start Hook for Claude Code.

Loads Letta Cloud memories and local project memories at session start.
Injects relevant context into the session.

Output:
    Prints context to inject into the session (read by Claude Code).
"""

import json
import os
import sys
from pathlib import Path

# Add hooks directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.letta_client import LettaClient
from utils.local_memory import LocalMemory


def main():
    """Load memories and output context for session injection."""
    output_parts = []

    # Load Letta Cloud memories (global)
    try:
        letta = LettaClient()

        # Get core memory
        core = letta.get_core_memory()
        if core:
            output_parts.append("## Global Context (Letta)")
            if core.get("persona"):
                output_parts.append(f"**Persona**: {core['persona']}")
            if core.get("human"):
                output_parts.append(f"**User**: {core['human']}")

        # Get recent archival memories (most relevant patterns/learnings)
        archival = letta.list_archival(limit=10)
        if archival:
            output_parts.append("\n### Recent Learnings")
            for memory in archival[:5]:
                text = memory.get("text", "")[:200]
                output_parts.append(f"- {text}")

    except Exception as e:
        # Don't fail the session if Letta is unavailable
        print(f"<!-- Letta unavailable: {e} -->", file=sys.stderr)

    # Load local project memories
    try:
        local = LocalMemory()
        if local.exists:
            summary = local.get_context_summary()
            if summary:
                output_parts.append(f"\n{summary}")
    except Exception as e:
        print(f"<!-- Local memory error: {e} -->", file=sys.stderr)

    # Output combined context
    if output_parts:
        print("<session-memory>")
        print("\n".join(output_parts))
        print("</session-memory>")


if __name__ == "__main__":
    main()
