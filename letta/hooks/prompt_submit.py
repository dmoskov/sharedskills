#!/usr/bin/env python3
"""
User Prompt Submit Hook for Claude Code.

Searches memories for context relevant to the user's prompt
and injects matching memories into the conversation.

Input (stdin):
    JSON with "prompt" field containing user's input

Output:
    Prints relevant context to inject (read by Claude Code).
"""

import json
import os
import sys
from pathlib import Path

# Add hooks directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.letta_client import LettaClient
from utils.local_memory import LocalMemory


def extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from text for search."""
    # Simple keyword extraction: words > 3 chars, excluding common words
    stopwords = {
        "the", "and", "for", "that", "this", "with", "from", "have", "been",
        "will", "would", "could", "should", "what", "when", "where", "which",
        "there", "their", "about", "into", "more", "some", "only", "just",
        "also", "than", "then", "them", "these", "those", "being", "does",
        "please", "want", "need", "help", "make", "like", "know", "think",
    }

    words = text.lower().split()
    keywords = [w for w in words if len(w) > 3 and w not in stopwords]
    return keywords[:5]  # Limit to 5 keywords


def main():
    """Search memories and output relevant context."""
    # Read prompt from stdin
    try:
        input_data = json.load(sys.stdin)
        prompt = input_data.get("prompt", "")
    except (json.JSONDecodeError, IOError):
        # No input or invalid JSON - nothing to do
        return

    if not prompt:
        return

    # Extract keywords for search
    keywords = extract_keywords(prompt)
    if not keywords:
        return

    query = " ".join(keywords)
    results = []

    # Search Letta Cloud
    try:
        letta = LettaClient()
        archival = letta.search_archival(query, limit=3)
        for memory in archival:
            results.append({
                "source": "global",
                "text": memory.get("text", ""),
            })
    except Exception:
        pass  # Continue without Letta if unavailable

    # Search local memories
    try:
        local = LocalMemory()
        if local.exists:
            local_results = local.search(query)
            for memory in local_results[:3]:
                results.append({
                    "source": "project",
                    "text": f"[{memory['category']}] {memory['title']}: {memory['content'][:200]}",
                })
    except Exception:
        pass

    # Output relevant context
    if results:
        print("<relevant-memory>")
        for r in results[:5]:  # Limit total results
            source = r["source"]
            text = r["text"][:300]  # Truncate long texts
            print(f"[{source}] {text}")
        print("</relevant-memory>")


if __name__ == "__main__":
    main()
