#!/usr/bin/env python3
"""
Unit tests for markdown_to_asana.py (the forward converter).

Tests cover:
- Core inline/block formatting (headings, bold, lists, code, links)
- Tables -> real Asana <table> (header row bolded; Asana rejects <th>)
- Bare-URL autolinking (so Asana can resolve app.asana.com links to chips)
- Round-trip stability with asana_to_markdown
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from markdown_to_asana import markdown_to_asana_html
from asana_to_markdown import asana_html_to_markdown


def body(inner: str) -> str:
    return f"<body>{inner}</body>"


class TestCoreFormatting:
    def test_h1(self):
        assert markdown_to_asana_html("# Title") == body("<h1>Title</h1>")

    def test_h2(self):
        assert markdown_to_asana_html("## Sub") == body("<h2>Sub</h2>")

    def test_heading_levels_above_two_become_h2(self):
        assert markdown_to_asana_html("#### Deep") == body("<h2>Deep</h2>")

    def test_bold(self):
        assert markdown_to_asana_html("**bold**") == body("<strong>bold</strong>")

    def test_italic(self):
        assert markdown_to_asana_html("*it*") == body("<em>it</em>")

    def test_strikethrough(self):
        assert markdown_to_asana_html("~~no~~") == body("<s>no</s>")

    def test_inline_code(self):
        assert markdown_to_asana_html("`x`") == body("<code>x</code>")

    def test_unordered_list(self):
        assert markdown_to_asana_html("- a\n- b") == body("<ul><li>a</li><li>b</li></ul>")

    def test_escaped_newlines_normalized(self):
        # LLMs often emit literal backslash-n; it should act as a real newline.
        assert markdown_to_asana_html("a\\nb") == body("a\nb")


class TestLinks:
    def test_markdown_link_http(self):
        out = markdown_to_asana_html("[text](https://example.com)")
        assert out == body('<a href="https://example.com">text</a>')

    def test_bare_url_is_autolinked(self):
        # The whole point of TODO #2: a pasted URL must become an <a>, so Asana
        # can upgrade app.asana.com hrefs into rich object chips.
        out = markdown_to_asana_html("see https://app.asana.com/0/0/123 ok")
        assert '<a href="https://app.asana.com/0/0/123">' in out
        assert out == body(
            'see <a href="https://app.asana.com/0/0/123">'
            'https://app.asana.com/0/0/123</a> ok'
        )

    def test_non_http_link_falls_back_to_text(self):
        out = markdown_to_asana_html("[x](ftp://h/f)")
        assert out == body("x (ftp://h/f)")


class TestTables:
    def test_basic_table_renders_html(self):
        md = "| Name | Age |\n| --- | --- |\n| Bob | 30 |"
        assert markdown_to_asana_html(md) == body(
            "<table>"
            "<tr><td><strong>Name</strong></td><td><strong>Age</strong></td></tr>"
            "<tr><td>Bob</td><td>30</td></tr>"
            "</table>"
        )

    def test_no_th_tag_emitted(self):
        # Asana returns "XML is invalid" for <th>; headers must be bolded <td>.
        out = markdown_to_asana_html("| A |\n| --- |\n| 1 |")
        assert "<th>" not in out
        assert "<td><strong>A</strong></td>" in out

    def test_cell_inline_formatting_preserved(self):
        md = "| H |\n| --- |\n| **bold** and `code` |"
        out = markdown_to_asana_html(md)
        assert "<td><strong>bold</strong> and <code>code</code></td>" in out

    def test_link_in_cell_preserved(self):
        md = "| H |\n| --- |\n| [y](https://app.asana.com/0/0/1) |"
        out = markdown_to_asana_html(md)
        assert '<td><a href="https://app.asana.com/0/0/1">y</a></td>' in out

    def test_table_between_paragraphs(self):
        md = "Intro\n\n| H |\n| --- |\n| a |\n\nOutro"
        out = markdown_to_asana_html(md)
        assert "Intro" in out and "Outro" in out
        assert "<table><tr><td><strong>H</strong></td></tr><tr><td>a</td></tr></table>" in out


class TestRoundTrip:
    def test_table_round_trips(self):
        md = "| Name | Age |\n| --- | --- |\n| Bob | 30 |"
        html = markdown_to_asana_html(md)
        back = asana_html_to_markdown(html)
        # Header bold survives the round trip (we bold headers going out).
        assert back == "| **Name** | **Age** |\n| --- | --- |\n| Bob | 30 |"

    def test_table_with_formatting_round_trips(self):
        md = "| A | B |\n| --- | --- |\n| **x** | [y](https://app.asana.com/0/0/1) |"
        html = markdown_to_asana_html(md)
        back = asana_html_to_markdown(html)
        assert back == (
            "| **A** | **B** |\n| --- | --- |\n"
            "| **x** | [y](https://app.asana.com/0/0/1) |"
        )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
