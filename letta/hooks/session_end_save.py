#!/usr/bin/env python3
"""
Session End Save Hook for Claude Code.

Receives extracted memories from Claude and saves them:
- Global memories -> Letta Cloud archival
- Project memories -> Local .memory/ directory

Input (stdin):
    JSON with "memories" array from Claude's extraction

Output:
    Summary of saved memories
"""

import json
import os
import sys
from pathlib import Path

# Add hooks directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.letta_client import LettaClient
from utils.local_memory import LocalMemory
from utils.dedup import is_duplicate


def main():
    """Save extracted memories to appropriate storage."""
    # Read memories from stdin
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, IOError):
        print("<!-- No memory data received -->", file=sys.stderr)
        return

    memories = input_data.get("memories", [])
    if not memories:
        print("<!-- No memories to save -->")
        return

    saved_global = 0
    saved_project = 0
    skipped_dupes = 0

    # Initialize clients
    letta = None
    local = None
    existing_global = []
    existing_local = []

    try:
        letta = LettaClient()
        # Load existing for dedup
        archival = letta.list_archival(limit=100)
        existing_global = [m.get("text", "") for m in archival]
    except Exception as e:
        print(f"<!-- Letta unavailable: {e} -->", file=sys.stderr)

    try:
        local = LocalMemory()
        local.initialize()
        all_local = local.load_all()
        for cat_memories in all_local.values():
            for m in cat_memories:
                existing_local.append(m.get("content", ""))
    except Exception as e:
        print(f"<!-- Local memory error: {e} -->", file=sys.stderr)

    # Process each memory
    for memory in memories:
        content = memory.get("content", "").strip()
        tier = memory.get("tier", "").lower()
        category = memory.get("category", "learning").lower()
        reason = memory.get("reason", "")

        if not content:
            continue

        # Validate category
        if category not in ("decision", "pattern", "learning"):
            category = "learning"

        # Create full memory text
        full_text = content
        if reason:
            full_text = f"{content}\n\nReason: {reason}"

        if tier == "global":
            # Save to Letta Cloud
            if not letta:
                continue

            # Check for duplicates
            if is_duplicate(full_text, existing_global, threshold=0.85):
                skipped_dupes += 1
                continue

            try:
                letta.insert_archival(full_text)
                existing_global.append(full_text)
                saved_global += 1
            except Exception as e:
                print(f"<!-- Failed to save global memory: {e} -->", file=sys.stderr)

        elif tier == "project":
            # Save to local .memory/
            if not local:
                continue

            # Check for duplicates
            if is_duplicate(content, existing_local, threshold=0.85):
                skipped_dupes += 1
                continue

            try:
                # Use first line as title, or truncate content
                lines = content.split("\n")
                if len(lines) > 1 and len(lines[0]) < 100:
                    title = lines[0]
                    body = "\n".join(lines[1:]).strip()
                else:
                    title = content[:60] + "..." if len(content) > 60 else content
                    body = content

                if reason:
                    body = f"{body}\n\n**Why this matters:** {reason}"

                local.save_memory(category, title, body)
                existing_local.append(content)
                saved_project += 1
            except Exception as e:
                print(f"<!-- Failed to save project memory: {e} -->", file=sys.stderr)

    # Output summary
    print(f"<memory-save-summary>")
    print(f"Saved {saved_global} global memories to Letta Cloud")
    print(f"Saved {saved_project} project memories to .memory/")
    if skipped_dupes:
        print(f"Skipped {skipped_dupes} duplicate memories")
    print(f"</memory-save-summary>")


if __name__ == "__main__":
    main()
