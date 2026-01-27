"""
Sophisticated file management utilities for reading and writing subsections.

Provides markdown-aware section operations and precise line-based operations.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Section:
    """Represents a markdown section."""
    heading: str
    level: int  # Number of # characters
    start_line: int  # 1-indexed, line with heading
    end_line: int  # 1-indexed, last line of content (before next section or EOF)
    content: str  # Content without the heading line


@dataclass
class LineRange:
    """Represents a range of lines."""
    start: int  # 1-indexed, inclusive
    end: int  # 1-indexed, inclusive
    content: str


class FileManager:
    """
    File management with section-aware and line-based operations.

    Section operations work with markdown headings (# ## ### etc).
    Line operations use 1-indexed line numbers.
    """

    def __init__(self, file_path: str | Path):
        """
        Initialize file manager for a specific file.

        Args:
            file_path: Path to the file to manage
        """
        self._path = Path(file_path)

    @property
    def path(self) -> Path:
        """Get file path."""
        return self._path

    @property
    def exists(self) -> bool:
        """Check if file exists."""
        return self._path.exists()

    def read(self) -> str:
        """Read entire file content."""
        if not self.exists:
            raise FileNotFoundError(f"File not found: {self._path}")
        return self._path.read_text()

    def write(self, content: str) -> None:
        """Write entire file content."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(content)

    # =========================================================================
    # Section-based operations (markdown-aware)
    # =========================================================================

    def list_sections(self) -> list[Section]:
        """
        List all sections in the file.

        Returns:
            List of Section objects with heading, level, line range, and content
        """
        if not self.exists:
            return []

        lines = self.read().split('\n')
        sections = []
        heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$')

        # Find all headings with their positions
        headings = []
        for i, line in enumerate(lines):
            match = heading_pattern.match(line)
            if match:
                level = len(match.group(1))
                heading = match.group(2).strip()
                headings.append((i, level, heading))

        # Build sections with content
        for idx, (line_num, level, heading) in enumerate(headings):
            # Find end: next heading of same or higher level, or EOF
            if idx + 1 < len(headings):
                end_line = headings[idx + 1][0] - 1
            else:
                end_line = len(lines) - 1

            # Extract content (lines after heading until end)
            content_lines = lines[line_num + 1:end_line + 1]
            content = '\n'.join(content_lines).strip()

            sections.append(Section(
                heading=heading,
                level=level,
                start_line=line_num + 1,  # Convert to 1-indexed
                end_line=end_line + 1,
                content=content
            ))

        return sections

    def read_section(self, heading: str, include_subsections: bool = True) -> Optional[Section]:
        """
        Read a section by its heading.

        Args:
            heading: The heading text (without # prefix)
            include_subsections: If True, include nested subsections in content

        Returns:
            Section object or None if not found
        """
        if not self.exists:
            return None

        lines = self.read().split('\n')
        heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$')

        # Find the target heading
        target_line = None
        target_level = None
        for i, line in enumerate(lines):
            match = heading_pattern.match(line)
            if match and match.group(2).strip() == heading:
                target_line = i
                target_level = len(match.group(1))
                break

        if target_line is None:
            return None

        # Find the end line based on include_subsections
        end_line = len(lines) - 1
        for i in range(target_line + 1, len(lines)):
            match = heading_pattern.match(lines[i])
            if match:
                found_level = len(match.group(1))
                if include_subsections:
                    # Stop at next same-or-higher level heading
                    if found_level <= target_level:
                        end_line = i - 1
                        break
                else:
                    # Stop at any heading
                    end_line = i - 1
                    break

        # Extract content
        content_lines = lines[target_line + 1:end_line + 1]
        content = '\n'.join(content_lines).strip()

        return Section(
            heading=heading,
            level=target_level,
            start_line=target_line + 1,  # Convert to 1-indexed
            end_line=end_line + 1,
            content=content
        )

    def write_section(self, heading: str, content: str, create_if_missing: bool = False, level: int = 2) -> bool:
        """
        Replace content under a section heading.

        Args:
            heading: The heading text (without # prefix)
            content: New content for the section
            create_if_missing: If True, create section at end if not found
            level: Heading level for new sections (default: 2 = ##)

        Returns:
            True if section was written, False if not found and create_if_missing=False
        """
        section = self.read_section(heading)

        if section is None:
            if not create_if_missing:
                return False
            # Append new section at end
            current = self.read() if self.exists else ''
            new_section = f"\n\n{'#' * level} {heading}\n\n{content}"
            self.write(current.rstrip() + new_section)
            return True

        lines = self.read().split('\n')

        # Build new content
        new_lines = (
            lines[:section.start_line] +  # Everything before section content
            [content] +  # New content
            lines[section.end_line:]  # Everything after section
        )

        self.write('\n'.join(new_lines))
        return True

    def append_to_section(self, heading: str, content: str) -> bool:
        """
        Append content to the end of a section.

        Args:
            heading: The heading text (without # prefix)
            content: Content to append

        Returns:
            True if content was appended, False if section not found
        """
        section = self.read_section(heading)
        if section is None:
            return False

        new_content = section.content + '\n' + content if section.content else content
        return self.write_section(heading, new_content)

    def insert_section(self, new_heading: str, content: str, after_heading: Optional[str] = None, level: int = 2) -> bool:
        """
        Insert a new section.

        Args:
            new_heading: Heading for the new section
            content: Content for the new section
            after_heading: Insert after this heading (None = at end)
            level: Heading level (default: 2 = ##)

        Returns:
            True if section was inserted
        """
        new_section_text = f"{'#' * level} {new_heading}\n\n{content}"

        if after_heading is None:
            current = self.read() if self.exists else ''
            self.write(current.rstrip() + '\n\n' + new_section_text)
            return True

        section = self.read_section(after_heading)
        if section is None:
            return False

        lines = self.read().split('\n')
        new_lines = (
            lines[:section.end_line] +
            ['', new_section_text] +
            lines[section.end_line:]
        )

        self.write('\n'.join(new_lines))
        return True

    def delete_section(self, heading: str) -> bool:
        """
        Delete a section and its content.

        Args:
            heading: The heading text (without # prefix)

        Returns:
            True if section was deleted, False if not found
        """
        section = self.read_section(heading)
        if section is None:
            return False

        lines = self.read().split('\n')

        # Remove from heading line through end of content
        new_lines = lines[:section.start_line - 1] + lines[section.end_line:]

        # Clean up extra blank lines
        content = '\n'.join(new_lines)
        content = re.sub(r'\n{3,}', '\n\n', content)

        self.write(content.strip() + '\n')
        return True

    # =========================================================================
    # Line-based operations
    # =========================================================================

    def read_lines(self, start: int, end: Optional[int] = None) -> LineRange:
        """
        Read a range of lines.

        Args:
            start: Start line (1-indexed, inclusive)
            end: End line (1-indexed, inclusive). None = just start line.

        Returns:
            LineRange object with the content
        """
        if not self.exists:
            raise FileNotFoundError(f"File not found: {self._path}")

        lines = self.read().split('\n')
        end = end or start

        if start < 1 or end < 1:
            raise ValueError("Line numbers must be >= 1")
        if start > len(lines) or end > len(lines):
            raise ValueError(f"Line number out of range (file has {len(lines)} lines)")
        if start > end:
            raise ValueError("Start line must be <= end line")

        # Convert to 0-indexed
        content = '\n'.join(lines[start - 1:end])

        return LineRange(start=start, end=end, content=content)

    def insert_lines(self, after_line: int, content: str) -> None:
        """
        Insert content after a specific line.

        Args:
            after_line: Insert after this line (0 = at beginning)
            content: Content to insert (can be multi-line)
        """
        if not self.exists:
            if after_line == 0:
                self.write(content)
                return
            raise FileNotFoundError(f"File not found: {self._path}")

        lines = self.read().split('\n')

        if after_line < 0 or after_line > len(lines):
            raise ValueError(f"Line number out of range (file has {len(lines)} lines)")

        new_content_lines = content.split('\n')
        new_lines = lines[:after_line] + new_content_lines + lines[after_line:]

        self.write('\n'.join(new_lines))

    def replace_lines(self, start: int, end: int, content: str) -> LineRange:
        """
        Replace a range of lines with new content.

        Args:
            start: Start line (1-indexed, inclusive)
            end: End line (1-indexed, inclusive)
            content: Replacement content

        Returns:
            LineRange of the old content that was replaced
        """
        if not self.exists:
            raise FileNotFoundError(f"File not found: {self._path}")

        old = self.read_lines(start, end)
        lines = self.read().split('\n')

        new_content_lines = content.split('\n')
        new_lines = lines[:start - 1] + new_content_lines + lines[end:]

        self.write('\n'.join(new_lines))
        return old

    def delete_lines(self, start: int, end: Optional[int] = None) -> LineRange:
        """
        Delete a range of lines.

        Args:
            start: Start line (1-indexed, inclusive)
            end: End line (1-indexed, inclusive). None = just start line.

        Returns:
            LineRange of the deleted content
        """
        end = end or start
        return self.replace_lines(start, end, '')

    # =========================================================================
    # String-based operations
    # =========================================================================

    def str_replace(self, old_str: str, new_str: str, replace_all: bool = False) -> int:
        """
        Find and replace string in file.

        Args:
            old_str: String to find
            new_str: Replacement string
            replace_all: If True, replace all occurrences. If False, replace first only.

        Returns:
            Number of replacements made
        """
        if not self.exists:
            raise FileNotFoundError(f"File not found: {self._path}")

        content = self.read()

        if old_str not in content:
            return 0

        if replace_all:
            count = content.count(old_str)
            new_content = content.replace(old_str, new_str)
        else:
            count = 1
            new_content = content.replace(old_str, new_str, 1)

        self.write(new_content)
        return count

    def find_in_file(self, pattern: str, regex: bool = False) -> list[tuple[int, str]]:
        """
        Find occurrences of a pattern in the file.

        Args:
            pattern: String or regex pattern to find
            regex: If True, treat pattern as regex

        Returns:
            List of (line_number, line_content) tuples for matches
        """
        if not self.exists:
            return []

        lines = self.read().split('\n')
        matches = []

        if regex:
            compiled = re.compile(pattern)
            for i, line in enumerate(lines, 1):
                if compiled.search(line):
                    matches.append((i, line))
        else:
            for i, line in enumerate(lines, 1):
                if pattern in line:
                    matches.append((i, line))

        return matches

    def count_lines(self) -> int:
        """Return total number of lines in file."""
        if not self.exists:
            return 0
        return len(self.read().split('\n'))


def read_section(file_path: str | Path, heading: str, include_subsections: bool = True) -> Optional[Section]:
    """Convenience function to read a section from a file."""
    return FileManager(file_path).read_section(heading, include_subsections)


def write_section(file_path: str | Path, heading: str, content: str, create_if_missing: bool = False) -> bool:
    """Convenience function to write a section to a file."""
    return FileManager(file_path).write_section(heading, content, create_if_missing)


def list_sections(file_path: str | Path) -> list[Section]:
    """Convenience function to list sections in a file."""
    return FileManager(file_path).list_sections()


def str_replace(file_path: str | Path, old_str: str, new_str: str, replace_all: bool = False) -> int:
    """Convenience function for string replacement in a file."""
    return FileManager(file_path).str_replace(old_str, new_str, replace_all)
