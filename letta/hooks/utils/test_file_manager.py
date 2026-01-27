#!/usr/bin/env python3
"""
Unit tests for file_manager.py

Tests cover:
- Section-based operations (list, read, write, append, insert, delete)
- Line-based operations (read, insert, replace, delete)
- String-based operations (str_replace, find_in_file)
- Edge cases and error handling
"""

import sys
from pathlib import Path
from textwrap import dedent

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from file_manager import (
    FileManager,
    Section,
    LineRange,
    read_section,
    write_section,
    list_sections,
    str_replace,
)


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file for testing."""
    file_path = tmp_path / "test.md"
    return file_path


@pytest.fixture
def markdown_file(tmp_path):
    """Create a markdown file with sections for testing."""
    file_path = tmp_path / "test.md"
    content = dedent("""\
        # Main Title

        Introduction paragraph.

        ## Section One

        Content of section one.
        Multiple lines here.

        ## Section Two

        Content of section two.

        ### Subsection

        Nested content.

        ## Section Three

        Final section content.
    """)
    file_path.write_text(content)
    return file_path


class TestFileManagerBasics:
    """Tests for basic file operations."""

    def test_init(self, temp_file):
        """Should initialize with file path."""
        fm = FileManager(temp_file)
        assert fm.path == temp_file

    def test_init_with_string_path(self, temp_file):
        """Should accept string path."""
        fm = FileManager(str(temp_file))
        assert fm.path == temp_file

    def test_exists_false(self, temp_file):
        """Should return False for non-existent file."""
        fm = FileManager(temp_file)
        assert fm.exists is False

    def test_exists_true(self, markdown_file):
        """Should return True for existing file."""
        fm = FileManager(markdown_file)
        assert fm.exists is True

    def test_read(self, markdown_file):
        """Should read entire file content."""
        fm = FileManager(markdown_file)
        content = fm.read()
        assert "# Main Title" in content
        assert "## Section One" in content

    def test_read_nonexistent(self, temp_file):
        """Should raise FileNotFoundError for non-existent file."""
        fm = FileManager(temp_file)
        with pytest.raises(FileNotFoundError):
            fm.read()

    def test_write(self, temp_file):
        """Should write content to file."""
        fm = FileManager(temp_file)
        fm.write("Test content")
        assert temp_file.read_text() == "Test content"

    def test_write_creates_parents(self, tmp_path):
        """Should create parent directories if needed."""
        file_path = tmp_path / "subdir" / "nested" / "test.md"
        fm = FileManager(file_path)
        fm.write("Content")
        assert file_path.exists()
        assert file_path.read_text() == "Content"

    def test_count_lines(self, markdown_file):
        """Should return correct line count."""
        fm = FileManager(markdown_file)
        count = fm.count_lines()
        assert count > 0

    def test_count_lines_nonexistent(self, temp_file):
        """Should return 0 for non-existent file."""
        fm = FileManager(temp_file)
        assert fm.count_lines() == 0


class TestSectionOperations:
    """Tests for section-based operations."""

    def test_list_sections(self, markdown_file):
        """Should list all sections."""
        fm = FileManager(markdown_file)
        sections = fm.list_sections()

        headings = [s.heading for s in sections]
        assert "Main Title" in headings
        assert "Section One" in headings
        assert "Section Two" in headings
        assert "Subsection" in headings
        assert "Section Three" in headings

    def test_list_sections_levels(self, markdown_file):
        """Should capture correct heading levels."""
        fm = FileManager(markdown_file)
        sections = fm.list_sections()

        section_dict = {s.heading: s for s in sections}
        assert section_dict["Main Title"].level == 1
        assert section_dict["Section One"].level == 2
        assert section_dict["Subsection"].level == 3

    def test_list_sections_empty_file(self, temp_file):
        """Should return empty list for non-existent file."""
        fm = FileManager(temp_file)
        sections = fm.list_sections()
        assert sections == []

    def test_list_sections_no_headings(self, temp_file):
        """Should return empty list for file without headings."""
        temp_file.write_text("Just plain text\nNo headings here")
        fm = FileManager(temp_file)
        sections = fm.list_sections()
        assert sections == []

    def test_read_section(self, markdown_file):
        """Should read content under a heading."""
        fm = FileManager(markdown_file)
        section = fm.read_section("Section One")

        assert section is not None
        assert section.heading == "Section One"
        assert section.level == 2
        assert "Content of section one" in section.content
        assert "Multiple lines here" in section.content

    def test_read_section_not_found(self, markdown_file):
        """Should return None for non-existent section."""
        fm = FileManager(markdown_file)
        section = fm.read_section("Nonexistent Section")
        assert section is None

    def test_read_section_with_subsections(self, markdown_file):
        """Should include subsections when include_subsections=True."""
        fm = FileManager(markdown_file)
        section = fm.read_section("Section Two", include_subsections=True)

        assert section is not None
        assert "### Subsection" in section.content or "Nested content" in section.content

    def test_write_section(self, markdown_file):
        """Should replace section content."""
        fm = FileManager(markdown_file)
        result = fm.write_section("Section One", "New content here")

        assert result is True
        content = fm.read()
        assert "New content here" in content
        assert "Content of section one" not in content

    def test_write_section_not_found(self, markdown_file):
        """Should return False when section not found."""
        fm = FileManager(markdown_file)
        result = fm.write_section("Nonexistent", "Content")
        assert result is False

    def test_write_section_create_if_missing(self, markdown_file):
        """Should create section when create_if_missing=True."""
        fm = FileManager(markdown_file)
        result = fm.write_section("New Section", "New content", create_if_missing=True)

        assert result is True
        content = fm.read()
        assert "## New Section" in content
        assert "New content" in content

    def test_write_section_create_with_level(self, markdown_file):
        """Should create section with specified level."""
        fm = FileManager(markdown_file)
        fm.write_section("Deep Section", "Content", create_if_missing=True, level=3)

        content = fm.read()
        assert "### Deep Section" in content

    def test_append_to_section(self, markdown_file):
        """Should append content to section."""
        fm = FileManager(markdown_file)
        result = fm.append_to_section("Section One", "Appended content")

        assert result is True
        section = fm.read_section("Section One")
        assert "Content of section one" in section.content
        assert "Appended content" in section.content

    def test_append_to_section_not_found(self, markdown_file):
        """Should return False when section not found."""
        fm = FileManager(markdown_file)
        result = fm.append_to_section("Nonexistent", "Content")
        assert result is False

    def test_insert_section(self, markdown_file):
        """Should insert new section at end."""
        fm = FileManager(markdown_file)
        result = fm.insert_section("Inserted Section", "Inserted content")

        assert result is True
        sections = fm.list_sections()
        headings = [s.heading for s in sections]
        assert "Inserted Section" in headings

    def test_insert_section_after(self, markdown_file):
        """Should insert section after specified heading."""
        fm = FileManager(markdown_file)
        result = fm.insert_section("Middle Section", "Middle content", after_heading="Section One")

        assert result is True
        content = fm.read()
        # Verify the new section appears after Section One content
        idx_one = content.find("## Section One")
        idx_middle = content.find("## Middle Section")
        idx_two = content.find("## Section Two")
        assert idx_one < idx_middle < idx_two

    def test_insert_section_after_not_found(self, markdown_file):
        """Should return False when after_heading not found."""
        fm = FileManager(markdown_file)
        result = fm.insert_section("New", "Content", after_heading="Nonexistent")
        assert result is False

    def test_delete_section(self, markdown_file):
        """Should delete section and its content."""
        fm = FileManager(markdown_file)
        result = fm.delete_section("Section Two")

        assert result is True
        sections = fm.list_sections()
        headings = [s.heading for s in sections]
        assert "Section Two" not in headings
        # Subsection should also be gone (it was part of Section Two)
        content = fm.read()
        assert "Content of section two" not in content

    def test_delete_section_not_found(self, markdown_file):
        """Should return False when section not found."""
        fm = FileManager(markdown_file)
        result = fm.delete_section("Nonexistent")
        assert result is False


class TestLineOperations:
    """Tests for line-based operations."""

    def test_read_lines_single(self, markdown_file):
        """Should read a single line."""
        fm = FileManager(markdown_file)
        result = fm.read_lines(1)

        assert result.start == 1
        assert result.end == 1
        assert "# Main Title" in result.content

    def test_read_lines_range(self, markdown_file):
        """Should read a range of lines."""
        fm = FileManager(markdown_file)
        result = fm.read_lines(1, 3)

        assert result.start == 1
        assert result.end == 3
        lines = result.content.split('\n')
        assert len(lines) == 3

    def test_read_lines_invalid_start(self, markdown_file):
        """Should raise ValueError for line < 1."""
        fm = FileManager(markdown_file)
        with pytest.raises(ValueError, match="must be >= 1"):
            fm.read_lines(0)

    def test_read_lines_out_of_range(self, markdown_file):
        """Should raise ValueError for line beyond file."""
        fm = FileManager(markdown_file)
        with pytest.raises(ValueError, match="out of range"):
            fm.read_lines(1000)

    def test_read_lines_start_after_end(self, markdown_file):
        """Should raise ValueError when start > end."""
        fm = FileManager(markdown_file)
        with pytest.raises(ValueError, match="Start line must be <= end line"):
            fm.read_lines(5, 3)

    def test_read_lines_nonexistent(self, temp_file):
        """Should raise FileNotFoundError for non-existent file."""
        fm = FileManager(temp_file)
        with pytest.raises(FileNotFoundError):
            fm.read_lines(1)

    def test_insert_lines(self, temp_file):
        """Should insert content after specified line."""
        temp_file.write_text("Line 1\nLine 2\nLine 3")
        fm = FileManager(temp_file)
        fm.insert_lines(1, "Inserted line")

        content = temp_file.read_text()
        lines = content.split('\n')
        assert lines[0] == "Line 1"
        assert lines[1] == "Inserted line"
        assert lines[2] == "Line 2"

    def test_insert_lines_at_beginning(self, temp_file):
        """Should insert at beginning when after_line=0."""
        temp_file.write_text("Line 1\nLine 2")
        fm = FileManager(temp_file)
        fm.insert_lines(0, "First line")

        content = temp_file.read_text()
        lines = content.split('\n')
        assert lines[0] == "First line"
        assert lines[1] == "Line 1"

    def test_insert_lines_multiline(self, temp_file):
        """Should insert multiple lines."""
        temp_file.write_text("Line 1\nLine 3")
        fm = FileManager(temp_file)
        fm.insert_lines(1, "Line 1.5\nLine 2")

        content = temp_file.read_text()
        lines = content.split('\n')
        assert lines == ["Line 1", "Line 1.5", "Line 2", "Line 3"]

    def test_insert_lines_creates_file(self, temp_file):
        """Should create file when inserting at position 0."""
        fm = FileManager(temp_file)
        fm.insert_lines(0, "New content")
        assert temp_file.read_text() == "New content"

    def test_replace_lines(self, temp_file):
        """Should replace a range of lines."""
        temp_file.write_text("Line 1\nLine 2\nLine 3\nLine 4")
        fm = FileManager(temp_file)
        old = fm.replace_lines(2, 3, "Replacement")

        assert old.content == "Line 2\nLine 3"
        content = temp_file.read_text()
        lines = content.split('\n')
        assert lines == ["Line 1", "Replacement", "Line 4"]

    def test_replace_lines_single(self, temp_file):
        """Should replace a single line."""
        temp_file.write_text("Line 1\nLine 2\nLine 3")
        fm = FileManager(temp_file)
        fm.replace_lines(2, 2, "New Line 2")

        content = temp_file.read_text()
        lines = content.split('\n')
        assert lines[1] == "New Line 2"

    def test_delete_lines(self, temp_file):
        """Should delete a range of lines."""
        temp_file.write_text("Line 1\nLine 2\nLine 3\nLine 4")
        fm = FileManager(temp_file)
        deleted = fm.delete_lines(2, 3)

        assert deleted.content == "Line 2\nLine 3"
        content = temp_file.read_text()
        lines = content.split('\n')
        assert lines == ["Line 1", "", "Line 4"]

    def test_delete_lines_single(self, temp_file):
        """Should delete a single line."""
        temp_file.write_text("Line 1\nLine 2\nLine 3")
        fm = FileManager(temp_file)
        fm.delete_lines(2)

        content = temp_file.read_text()
        lines = content.split('\n')
        assert len(lines) == 3  # Empty string replaces the line


class TestStringOperations:
    """Tests for string-based operations."""

    def test_str_replace_single(self, temp_file):
        """Should replace first occurrence."""
        temp_file.write_text("foo bar foo baz foo")
        fm = FileManager(temp_file)
        count = fm.str_replace("foo", "qux")

        assert count == 1
        content = temp_file.read_text()
        assert content == "qux bar foo baz foo"

    def test_str_replace_all(self, temp_file):
        """Should replace all occurrences when replace_all=True."""
        temp_file.write_text("foo bar foo baz foo")
        fm = FileManager(temp_file)
        count = fm.str_replace("foo", "qux", replace_all=True)

        assert count == 3
        content = temp_file.read_text()
        assert content == "qux bar qux baz qux"

    def test_str_replace_not_found(self, temp_file):
        """Should return 0 when string not found."""
        temp_file.write_text("hello world")
        fm = FileManager(temp_file)
        count = fm.str_replace("nonexistent", "replacement")
        assert count == 0

    def test_str_replace_nonexistent_file(self, temp_file):
        """Should raise FileNotFoundError for non-existent file."""
        fm = FileManager(temp_file)
        with pytest.raises(FileNotFoundError):
            fm.str_replace("foo", "bar")

    def test_str_replace_multiline(self, temp_file):
        """Should work with multiline patterns."""
        temp_file.write_text("line1\nold\ncontent\nline4")
        fm = FileManager(temp_file)
        count = fm.str_replace("old\ncontent", "new\nstuff")

        assert count == 1
        content = temp_file.read_text()
        assert "new\nstuff" in content

    def test_find_in_file_simple(self, temp_file):
        """Should find simple string matches."""
        temp_file.write_text("line one\nline two with match\nline three\nmatch again")
        fm = FileManager(temp_file)
        matches = fm.find_in_file("match")

        assert len(matches) == 2
        assert matches[0] == (2, "line two with match")
        assert matches[1] == (4, "match again")

    def test_find_in_file_regex(self, temp_file):
        """Should find regex pattern matches."""
        temp_file.write_text("foo123\nbar456\nfoo789\nbaz")
        fm = FileManager(temp_file)
        matches = fm.find_in_file(r"foo\d+", regex=True)

        assert len(matches) == 2
        assert matches[0] == (1, "foo123")
        assert matches[1] == (3, "foo789")

    def test_find_in_file_no_matches(self, temp_file):
        """Should return empty list when no matches."""
        temp_file.write_text("hello world")
        fm = FileManager(temp_file)
        matches = fm.find_in_file("nonexistent")
        assert matches == []

    def test_find_in_file_nonexistent(self, temp_file):
        """Should return empty list for non-existent file."""
        fm = FileManager(temp_file)
        matches = fm.find_in_file("pattern")
        assert matches == []


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_read_section_function(self, markdown_file):
        """Should read section via convenience function."""
        section = read_section(markdown_file, "Section One")
        assert section is not None
        assert section.heading == "Section One"

    def test_write_section_function(self, markdown_file):
        """Should write section via convenience function."""
        result = write_section(markdown_file, "Section One", "Updated content")
        assert result is True
        content = markdown_file.read_text()
        assert "Updated content" in content

    def test_list_sections_function(self, markdown_file):
        """Should list sections via convenience function."""
        sections = list_sections(markdown_file)
        assert len(sections) > 0
        assert any(s.heading == "Section One" for s in sections)

    def test_str_replace_function(self, temp_file):
        """Should replace via convenience function."""
        temp_file.write_text("hello world")
        count = str_replace(temp_file, "world", "universe")
        assert count == 1
        assert temp_file.read_text() == "hello universe"


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_empty_file(self, temp_file):
        """Should handle empty file."""
        temp_file.write_text("")
        fm = FileManager(temp_file)

        assert fm.list_sections() == []
        assert fm.count_lines() == 1  # Empty file has one empty line

    def test_file_with_only_heading(self, temp_file):
        """Should handle file with only a heading."""
        temp_file.write_text("# Only Heading")
        fm = FileManager(temp_file)

        sections = fm.list_sections()
        assert len(sections) == 1
        assert sections[0].heading == "Only Heading"
        assert sections[0].content == ""

    def test_consecutive_headings(self, temp_file):
        """Should handle consecutive headings with no content between."""
        temp_file.write_text("# First\n## Second\n### Third\n\nContent here")
        fm = FileManager(temp_file)

        sections = fm.list_sections()
        assert len(sections) == 3
        # First two should have empty content
        first = next(s for s in sections if s.heading == "First")
        assert first.content == ""

    def test_heading_like_content(self, temp_file):
        """Should not match headings inside code blocks."""
        # Note: This is a limitation - we don't parse code blocks
        temp_file.write_text("# Real Heading\n\nSome text\n\n## Another Heading")
        fm = FileManager(temp_file)

        sections = fm.list_sections()
        headings = [s.heading for s in sections]
        assert "Real Heading" in headings
        assert "Another Heading" in headings

    def test_special_characters_in_heading(self, temp_file):
        """Should handle special characters in headings."""
        temp_file.write_text("## Section: With (Special) Characters!\n\nContent")
        fm = FileManager(temp_file)

        section = fm.read_section("Section: With (Special) Characters!")
        assert section is not None
        assert "Content" in section.content

    def test_unicode_content(self, temp_file):
        """Should handle unicode content."""
        temp_file.write_text("## 日本語見出し\n\nContent with émojis 🎉 and ñ")
        fm = FileManager(temp_file)

        sections = fm.list_sections()
        assert sections[0].heading == "日本語見出し"
        assert "🎉" in sections[0].content


class TestDataclasses:
    """Tests for dataclass structures."""

    def test_section_dataclass(self):
        """Should create Section with all fields."""
        section = Section(
            heading="Test",
            level=2,
            start_line=1,
            end_line=5,
            content="Test content"
        )
        assert section.heading == "Test"
        assert section.level == 2
        assert section.start_line == 1
        assert section.end_line == 5
        assert section.content == "Test content"

    def test_line_range_dataclass(self):
        """Should create LineRange with all fields."""
        lr = LineRange(start=10, end=20, content="Line content")
        assert lr.start == 10
        assert lr.end == 20
        assert lr.content == "Line content"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
