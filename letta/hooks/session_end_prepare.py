#!/usr/bin/env python3
"""
Session End Prepare Hook for Claude Code.

Prepares session summary for memory extraction.
Outputs guidance for Claude to extract memories in the right format.

Output:
    Instructions for Claude to extract memories from the session.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add hooks directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.local_memory import LocalMemory


def main():
    """Prepare session summary and output extraction instructions."""
    # Load session log for context
    session_summary = []

    try:
        local = LocalMemory()
        if local.exists:
            events = local.load_session_log()
            if events:
                # Summarize session activity
                edit_count = sum(1 for e in events if e.get("type") == "edit")
                write_count = sum(1 for e in events if e.get("type") == "write")
                bash_count = sum(1 for e in events if e.get("type") == "bash")

                files_modified = set()
                for e in events:
                    if e.get("file"):
                        files_modified.add(e["file"])

                session_summary.append(f"Session activity: {edit_count} edits, {write_count} writes, {bash_count} commands")
                if files_modified:
                    session_summary.append(f"Files modified: {', '.join(sorted(files_modified)[:10])}")
    except Exception:
        pass

    # Output context for memory extraction
    print("<session-end-context>")
    if session_summary:
        print("## Session Summary")
        for line in session_summary:
            print(f"- {line}")
        print()

    print("""## Memory Extraction Instructions

Review this session and extract valuable memories. For each memory, determine:

1. **Tier**: Where should it be stored?
   - `global`: Cross-project patterns, general best practices, reusable insights
   - `project`: Project-specific decisions, local conventions, implementation details

2. **Category**: What type of memory?
   - `decision`: Architecture/design decisions with rationale
   - `pattern`: Code patterns, conventions, or techniques
   - `learning`: Bug fixes, troubleshooting steps, insights

3. **Content**: What was learned? Be specific and actionable.

Output JSON format:
```json
{
  "memories": [
    {
      "content": "Description of what was learned",
      "tier": "global|project",
      "category": "decision|pattern|learning",
      "reason": "Why this is worth remembering"
    }
  ]
}
```

Only extract memories that would be valuable for future sessions. Skip:
- Trivial changes (typo fixes, simple renames)
- One-off tasks with no reusable insight
- Information already documented elsewhere
</session-end-context>""")


if __name__ == "__main__":
    main()
