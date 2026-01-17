"""
Local project memory management.

Stores project-specific memories in .memory/ directory.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional


class LocalMemory:
    """
    Manages project-local .memory/ directory.

    Structure:
        .memory/
            decisions/     # Architecture and design decisions
            patterns/      # Code patterns and conventions
            learnings/     # Bug fixes, troubleshooting, insights
            sessions/      # Session activity logs (JSONL)
    """

    CATEGORIES = ["decisions", "patterns", "learnings"]
    SESSIONS_DIR = "sessions"

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize local memory for a project.

        Args:
            project_root: Project root directory. If not provided, uses current working directory.
        """
        self._root = Path(project_root or os.getcwd())
        self._memory_dir = self._root / ".memory"

    @property
    def memory_dir(self) -> Path:
        """Get .memory directory path."""
        return self._memory_dir

    @property
    def exists(self) -> bool:
        """Check if .memory directory exists."""
        return self._memory_dir.exists()

    def initialize(self) -> None:
        """Create .memory directory structure."""
        for category in self.CATEGORIES:
            (self._memory_dir / category).mkdir(parents=True, exist_ok=True)
        (self._memory_dir / self.SESSIONS_DIR).mkdir(parents=True, exist_ok=True)

        # Create .gitignore for sessions (logs can be large)
        gitignore = self._memory_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("sessions/*.session.jsonl\n")

    def load_all(self) -> dict[str, list[dict]]:
        """
        Load all memories from all categories.

        Returns:
            Dict with category names as keys and lists of memories as values
        """
        result = {}
        for category in self.CATEGORIES:
            result[category] = self.load_category(category)
        return result

    def load_category(self, category: str) -> list[dict]:
        """
        Load all memories from a category.

        Args:
            category: Category name (decisions, patterns, learnings)

        Returns:
            List of memory dicts with filename, title, and content
        """
        if category not in self.CATEGORIES:
            raise ValueError(f"Invalid category: {category}. Must be one of {self.CATEGORIES}")

        category_dir = self._memory_dir / category
        if not category_dir.exists():
            return []

        memories = []
        for file_path in sorted(category_dir.glob("*.md")):
            content = file_path.read_text()
            # Extract title from first line if it's a heading
            title = file_path.stem
            lines = content.strip().split("\n")
            if lines and lines[0].startswith("# "):
                title = lines[0][2:].strip()
                content = "\n".join(lines[1:]).strip()

            memories.append({
                "filename": file_path.name,
                "title": title,
                "content": content,
                "category": category,
                "path": str(file_path),
            })

        return memories

    def save_memory(self, category: str, title: str, content: str) -> Path:
        """
        Save a memory to a category.

        Args:
            category: Category name
            title: Memory title
            content: Memory content

        Returns:
            Path to created file
        """
        if category not in self.CATEGORIES:
            raise ValueError(f"Invalid category: {category}")

        category_dir = self._memory_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)

        # Create filename from title
        filename = self._title_to_filename(title)
        file_path = category_dir / f"{filename}.md"

        # Handle filename conflicts
        counter = 1
        while file_path.exists():
            file_path = category_dir / f"{filename}-{counter}.md"
            counter += 1

        # Write with title header
        file_content = f"# {title}\n\n{content}"
        file_path.write_text(file_content)

        return file_path

    def _title_to_filename(self, title: str) -> str:
        """Convert title to valid filename."""
        # Lowercase and replace spaces with hyphens
        filename = title.lower().replace(" ", "-")
        # Remove invalid characters
        filename = re.sub(r"[^a-z0-9\-]", "", filename)
        # Collapse multiple hyphens
        filename = re.sub(r"-+", "-", filename)
        # Limit length
        return filename[:50].strip("-")

    def search(self, query: str, categories: Optional[list[str]] = None) -> list[dict]:
        """
        Search memories by keyword.

        Simple case-insensitive substring matching.

        Args:
            query: Search query
            categories: Categories to search (default: all)

        Returns:
            List of matching memories
        """
        query_lower = query.lower()
        categories = categories or self.CATEGORIES
        results = []

        for category in categories:
            memories = self.load_category(category)
            for memory in memories:
                if (query_lower in memory["title"].lower() or
                    query_lower in memory["content"].lower()):
                    results.append(memory)

        return results

    # Session logging

    def get_session_log_path(self, date: Optional[datetime] = None) -> Path:
        """
        Get path to session log file for a date.

        Args:
            date: Date for log file (default: today)

        Returns:
            Path to session log file
        """
        date = date or datetime.now()
        filename = f"{date.strftime('%Y-%m-%d')}.session.jsonl"
        return self._memory_dir / self.SESSIONS_DIR / filename

    def log_session_event(self, event_type: str, data: dict) -> None:
        """
        Log a session event.

        Args:
            event_type: Type of event (e.g., "edit", "write", "bash")
            data: Event data
        """
        sessions_dir = self._memory_dir / self.SESSIONS_DIR
        sessions_dir.mkdir(parents=True, exist_ok=True)

        log_path = self.get_session_log_path()

        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            **data,
        }

        with open(log_path, "a") as f:
            f.write(json.dumps(event) + "\n")

    def load_session_log(self, date: Optional[datetime] = None) -> list[dict]:
        """
        Load session log for a date.

        Args:
            date: Date to load (default: today)

        Returns:
            List of session events
        """
        log_path = self.get_session_log_path(date)
        if not log_path.exists():
            return []

        events = []
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        return events

    def get_context_summary(self) -> str:
        """
        Generate a summary of project memories for context injection.

        Returns:
            Formatted string suitable for injecting into session context
        """
        if not self.exists:
            return ""

        memories = self.load_all()
        sections = []

        for category in self.CATEGORIES:
            items = memories.get(category, [])
            if items:
                section = f"## {category.title()}\n"
                for item in items[:5]:  # Limit to 5 per category
                    section += f"- **{item['title']}**: {item['content'][:200]}...\n" if len(item['content']) > 200 else f"- **{item['title']}**: {item['content']}\n"
                sections.append(section)

        if sections:
            return "# Project Memory\n\n" + "\n".join(sections)
        return ""
