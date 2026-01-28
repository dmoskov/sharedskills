#!/usr/bin/env python3
"""
Markdown to Asana Rich Text Converter

Converts markdown to Asana's AsanaText HTML format using AST parsing.

Asana uses white-space: pre-wrap CSS, so literal \n characters create line breaks.

Supported markdown features:
- Headings: # H1, ## H2 (H3-H6 converted to H2)
- Bold: **text** or __text__
- Italic: *text* or _text_
- Strikethrough: ~~text~~
- Inline code: `code`
- Code blocks: ```code```
- Links: [text](url)
- Unordered lists: - item or * item
- Ordered lists: 1. item
- Blockquotes: > quote
- Horizontal rules: --- or ***

Output format follows Asana's AsanaText specification:
https://developers.asana.com/docs/rich-text#writing-rich-text

Usage as module:
    from markdown_to_asana import markdown_to_asana_html
    html = markdown_to_asana_html("# Hello **world**")

Usage as CLI:
    python markdown_to_asana.py "# Hello **world**"
    echo "# Hello" | python markdown_to_asana.py
"""

import html as html_module
import sys
from typing import Optional

try:
    import mistune
except ImportError:
    mistune = None


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return html_module.escape(text, quote=True)


class AsanaRenderer(mistune.HTMLRenderer):
    """
    Mistune HTML renderer customized for Asana's AsanaText format.

    Inherits from HTMLRenderer and overrides specific methods to match
    Asana's supported HTML subset.
    """

    def __init__(self) -> None:
        # escape=False because we handle escaping ourselves where needed
        super().__init__(escape=False)

    # ========== Override for Asana-specific behavior ==========

    def heading(self, text: str, level: int, **attrs) -> str:
        """Headings: Asana only supports H1 and H2."""
        tag_level = 1 if level == 1 else 2
        return f"<h{tag_level}>{text}</h{tag_level}>"

    def paragraph(self, text: str) -> str:
        """Paragraph - no wrapping tags, just text with newlines."""
        return text + "\n"

    def link(self, text: str, url: str, title: Optional[str] = None) -> str:
        """Links: Asana only supports http/https protocols."""
        lower_url = url.lower()
        if lower_url.startswith("http://") or lower_url.startswith("https://"):
            return f'<a href="{escape_html(url)}">{text}</a>'
        else:
            # Render as plain text: link text (url)
            return f"{text} ({escape_html(url)})"

    def image(self, text: str, url: str, title: Optional[str] = None) -> str:
        """Images - Asana doesn't support inline images, render as link."""
        return self.link(text or "image", url, title)

    def block_code(self, code: str, info: Optional[str] = None) -> str:
        """Code block: use <pre> without language class."""
        return f"<pre>{escape_html(code)}</pre>"

    def codespan(self, text: str) -> str:
        """Inline code."""
        return f"<code>{escape_html(text)}</code>"

    def strikethrough(self, text: str) -> str:
        """Strikethrough: use <s> tag for Asana."""
        return f"<s>{text}</s>"

    def thematic_break(self) -> str:
        """Horizontal rule."""
        return "<hr />"

    def block_quote(self, text: str) -> str:
        """Blockquote."""
        # Clean up extra newlines inside blockquotes
        text = text.strip()
        return f"<blockquote>{text}</blockquote>"

    def list(self, text: str, ordered: bool, **attrs) -> str:
        """List container."""
        tag = "ol" if ordered else "ul"
        return f"<{tag}>{text}</{tag}>"

    def list_item(self, text: str, **attrs) -> str:
        """List item."""
        # Strip trailing newlines from list item content
        text = text.strip()
        return f"<li>{text}</li>"

    # Disable features not supported by Asana
    def block_html(self, html: str) -> str:
        """Block HTML - escape it."""
        return escape_html(html)

    def inline_html(self, html: str) -> str:
        """Inline HTML - escape it."""
        return escape_html(html)


def _create_markdown_parser():
    """Create a mistune Markdown parser with GFM plugins."""
    if mistune is None:
        raise ImportError(
            "mistune package required for markdown conversion. "
            "Install with: pip install mistune"
        )

    renderer = AsanaRenderer()
    md = mistune.create_markdown(
        renderer=renderer,
        plugins=["strikethrough", "table"],
    )
    return md


def markdown_to_asana_html(markdown: str) -> str:
    """
    Convert markdown to Asana's AsanaText HTML format.

    Args:
        markdown: Markdown text to convert

    Returns:
        HTML string wrapped in <body> tags, ready for Asana's html_notes field

    Raises:
        ImportError: If mistune is not installed

    Example:
        >>> markdown_to_asana_html("# Hello **world**")
        '<body><h1>Hello <strong>world</strong></h1></body>'
    """
    # Normalize escaped newlines from LLMs (\\n -> \n)
    normalized = markdown.replace("\\n", "\n")

    md = _create_markdown_parser()
    body = md(normalized)

    # Strip trailing newlines that mistune adds
    body = body.rstrip("\n")

    return f"<body>{body}</body>"


def main():
    """CLI entry point for testing/debugging."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert markdown to Asana's AsanaText HTML format"
    )
    parser.add_argument(
        "markdown",
        nargs="?",
        help="Markdown text to convert (reads from stdin if not provided)"
    )
    parser.add_argument(
        "--unwrap",
        action="store_true",
        help="Output without <body> wrapper tags"
    )

    args = parser.parse_args()

    # Get input from argument or stdin
    if args.markdown:
        text = args.markdown
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        parser.print_help()
        sys.exit(1)

    try:
        result = markdown_to_asana_html(text)
        if args.unwrap:
            # Remove <body> wrapper
            result = result[6:-7]  # Strip <body> and </body>
        print(result)
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
