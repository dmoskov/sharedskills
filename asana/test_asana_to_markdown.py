#!/usr/bin/env python3
"""
Unit tests for asana_to_markdown.py

Tests cover:
- Basic formatting (headings, bold, italic, strikethrough)
- Links
- Lists (ordered, unordered, nested)
- Code (inline and blocks)
- Blockquotes and horizontal rules
- Entity and character reference handling
- Edge cases (empty input, None, whitespace)
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from asana_to_markdown import asana_html_to_markdown


class TestHeadings:
    def test_h1(self):
        assert asana_html_to_markdown("<body><h1>Title</h1></body>") == "# Title"

    def test_h2(self):
        assert asana_html_to_markdown("<body><h2>Subtitle</h2></body>") == "## Subtitle"

    def test_heading_with_inline_formatting(self):
        result = asana_html_to_markdown("<body><h2><strong>Bold</strong> heading</h2></body>")
        assert result == "## **Bold** heading"


class TestInlineFormatting:
    def test_bold_strong(self):
        assert asana_html_to_markdown("<body><strong>bold</strong></body>") == "**bold**"

    def test_bold_b(self):
        assert asana_html_to_markdown("<body><b>bold</b></body>") == "**bold**"

    def test_italic_em(self):
        assert asana_html_to_markdown("<body><em>italic</em></body>") == "*italic*"

    def test_italic_i(self):
        assert asana_html_to_markdown("<body><i>italic</i></body>") == "*italic*"

    def test_strikethrough(self):
        assert asana_html_to_markdown("<body><s>struck</s></body>") == "~~struck~~"

    def test_nested_bold_italic(self):
        result = asana_html_to_markdown("<body><strong><em>both</em></strong></body>")
        assert result == "***both***"

    def test_mixed_inline(self):
        html = "<body><p>Some <strong>bold</strong> and <em>italic</em> text</p></body>"
        result = asana_html_to_markdown(html)
        assert result == "Some **bold** and *italic* text"


class TestLinks:
    def test_basic_link(self):
        html = '<body><a href="https://example.com">click here</a></body>'
        assert asana_html_to_markdown(html) == "[click here](https://example.com)"

    def test_link_with_formatting(self):
        html = '<body><a href="https://example.com"><strong>bold link</strong></a></body>'
        assert asana_html_to_markdown(html) == "[**bold link**](https://example.com)"

    def test_link_no_href(self):
        html = "<body><a>no href</a></body>"
        assert asana_html_to_markdown(html) == "[no href]()"


class TestUnorderedLists:
    def test_simple_list(self):
        html = "<body><ul><li>one</li><li>two</li><li>three</li></ul></body>"
        result = asana_html_to_markdown(html)
        assert result == "- one\n- two\n- three"

    def test_list_with_formatting(self):
        html = "<body><ul><li><strong>bold</strong> item</li></ul></body>"
        result = asana_html_to_markdown(html)
        assert result == "- **bold** item"


class TestOrderedLists:
    def test_simple_ordered(self):
        html = "<body><ol><li>first</li><li>second</li><li>third</li></ol></body>"
        result = asana_html_to_markdown(html)
        assert result == "1. first\n2. second\n3. third"


class TestNestedLists:
    def test_nested_unordered(self):
        html = "<body><ul><li>parent</li><li><ul><li>child a</li><li>child b</li></ul></li></ul></body>"
        result = asana_html_to_markdown(html)
        assert "  - child a" in result
        assert "  - child b" in result

    def test_nested_with_parent_text(self):
        """Nested list inside a li with text should render on separate lines."""
        html = "<body><ul><li>parent 1<ul><li>child a</li><li>child b</li></ul></li><li>parent 2</li></ul></body>"
        result = asana_html_to_markdown(html)
        assert "- parent 1\n" in result
        assert "  - child a\n" in result
        assert "  - child b" in result
        assert "- parent 2" in result

    def test_nested_mixed(self):
        html = "<body><ul><li>item<ol><li>sub 1</li><li>sub 2</li></ol></li></ul></body>"
        result = asana_html_to_markdown(html)
        assert "- item\n" in result
        assert "  1. sub 1" in result
        assert "  2. sub 2" in result

    def test_simple_list_unaffected(self):
        """Flat lists should not gain extra newlines."""
        html = "<body><ul><li>one</li><li>two</li><li>three</li></ul></body>"
        result = asana_html_to_markdown(html)
        assert result == "- one\n- two\n- three"


class TestCodeBlocks:
    def test_inline_code(self):
        html = "<body><p>Use <code>foo()</code> here</p></body>"
        assert asana_html_to_markdown(html) == "Use `foo()` here"

    def test_code_block(self):
        html = "<body><pre>def hello():\n  print('hi')</pre></body>"
        result = asana_html_to_markdown(html)
        assert result.startswith("```\n")
        assert result.endswith("\n```")
        assert "def hello():" in result

    def test_pre_with_code_tag(self):
        """Asana sometimes wraps code in <pre><code>...</code></pre>."""
        html = "<body><pre><code>x = 1</code></pre></body>"
        result = asana_html_to_markdown(html)
        assert "x = 1" in result
        # Should not double-backtick (no ` inside ```)
        assert "`x = 1`" not in result


class TestBlockquotes:
    def test_simple_blockquote(self):
        html = "<body><blockquote>quoted text</blockquote></body>"
        assert asana_html_to_markdown(html) == "> quoted text"


class TestHorizontalRule:
    def test_hr(self):
        html = "<body><p>above</p><hr/><p>below</p></body>"
        result = asana_html_to_markdown(html)
        assert "---" in result
        assert "above" in result
        assert "below" in result


class TestLineBreaks:
    def test_br_tag(self):
        html = "<body><p>line one<br/>line two</p></body>"
        result = asana_html_to_markdown(html)
        assert "line one\nline two" in result


class TestParagraphs:
    def test_multiple_paragraphs(self):
        html = "<body><p>First</p><p>Second</p></body>"
        result = asana_html_to_markdown(html)
        assert "First" in result
        assert "Second" in result
        # Should have blank line between paragraphs
        assert "First\n\nSecond" in result


class TestEntities:
    def test_named_entities(self):
        html = "<body><p>foo &amp; bar &lt; baz &gt; qux</p></body>"
        result = asana_html_to_markdown(html)
        assert "foo & bar < baz > qux" in result

    def test_numeric_char_ref(self):
        html = "<body><p>&#169; copyright</p></body>"
        result = asana_html_to_markdown(html)
        assert "\u00a9 copyright" in result

    def test_hex_char_ref(self):
        html = "<body><p>&#x2019; curly</p></body>"
        result = asana_html_to_markdown(html)
        assert "\u2019 curly" in result


class TestEdgeCases:
    def test_empty_string(self):
        assert asana_html_to_markdown("") == ""

    def test_none_input(self):
        assert asana_html_to_markdown(None) == ""

    def test_plain_text_no_tags(self):
        assert asana_html_to_markdown("just text") == "just text"

    def test_body_only(self):
        assert asana_html_to_markdown("<body></body>") == ""

    def test_excessive_newlines_collapsed(self):
        html = "<body><p>a</p><p></p><p></p><p>b</p></body>"
        result = asana_html_to_markdown(html)
        # Should not have more than 2 consecutive newlines
        assert "\n\n\n" not in result
