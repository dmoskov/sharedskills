#!/usr/bin/env python3
"""
Asana Rich Text (HTML) to Markdown Converter

Converts Asana's AsanaText HTML format back to standard markdown.
This is the reverse of markdown_to_asana.py.

Handles Asana's supported HTML subset:
- <h1>, <h2> → # / ##
- <strong>, <b> → **bold**
- <em>, <i> → *italic*
- <s> → ~~strikethrough~~
- <code> → `code`
- <pre> → ```code block```
- <a href="url"> → [text](url)
- <ul>/<ol> + <li> → - item / 1. item
- <hr> → ---
- <blockquote> → > quote

Usage as module:
    from asana_to_markdown import asana_html_to_markdown
    md = asana_html_to_markdown("<body><h2>Hello</h2></body>")

Usage as CLI:
    python asana_to_markdown.py '<body><h2>Hello</h2></body>'
    echo '<body>...' | python asana_to_markdown.py
"""

import re
import sys
from html.parser import HTMLParser


class AsanaToMarkdownConverter(HTMLParser):
    """Convert Asana's HTML rich text to markdown."""

    def __init__(self):
        super().__init__()
        self.output = []
        self.tag_stack = []
        self.list_stack = []  # Track nested list types: 'ul' or 'ol'
        self.ol_counters = []  # Track ordered list item numbers
        self.in_pre = False

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs_dict = dict(attrs)
        self.tag_stack.append((tag, attrs_dict))

        if tag == "body":
            pass
        elif tag in ("h1", "h2"):
            level = int(tag[1])
            self.output.append("#" * level + " ")
        elif tag in ("strong", "b"):
            self.output.append("**")
        elif tag in ("em", "i"):
            self.output.append("*")
        elif tag == "s":
            self.output.append("~~")
        elif tag == "code" and not self.in_pre:
            self.output.append("`")
        elif tag == "pre":
            self.in_pre = True
            self.output.append("```\n")
        elif tag == "a":
            self.output.append("[")
        elif tag == "ul":
            if self.list_stack:
                self.output.append("\n")
            self.list_stack.append("ul")
        elif tag == "ol":
            if self.list_stack:
                self.output.append("\n")
            self.list_stack.append("ol")
            self.ol_counters.append(0)
        elif tag == "li":
            indent = "  " * max(0, len(self.list_stack) - 1)
            if self.list_stack and self.list_stack[-1] == "ol":
                self.ol_counters[-1] += 1
                self.output.append(f"{indent}{self.ol_counters[-1]}. ")
            else:
                self.output.append(f"{indent}- ")
        elif tag == "hr":
            self.output.append("\n---\n")
        elif tag == "blockquote":
            self.output.append("> ")
        elif tag == "br":
            self.output.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()

        if tag == "body":
            pass
        elif tag in ("h1", "h2"):
            self.output.append("\n\n")
        elif tag in ("strong", "b"):
            self.output.append("**")
        elif tag in ("em", "i"):
            self.output.append("*")
        elif tag == "s":
            self.output.append("~~")
        elif tag == "code" and not self.in_pre:
            self.output.append("`")
        elif tag == "pre":
            self.in_pre = False
            # Strip trailing newline inside the code block
            if self.output and self.output[-1].endswith("\n"):
                self.output[-1] = self.output[-1][:-1]
            self.output.append("\n```\n\n")
        elif tag == "a":
            # Find the matching start tag to get href
            href = ""
            for i in range(len(self.tag_stack) - 1, -1, -1):
                if self.tag_stack[i][0] == "a":
                    href = self.tag_stack[i][1].get("href", "")
                    break
            self.output.append(f"]({href})")
        elif tag == "li":
            self.output.append("\n")
        elif tag == "ul":
            if self.list_stack:
                self.list_stack.pop()
            self.output.append("\n")
        elif tag == "ol":
            if self.list_stack:
                self.list_stack.pop()
            if self.ol_counters:
                self.ol_counters.pop()
            self.output.append("\n")
        elif tag == "blockquote":
            self.output.append("\n")
        elif tag == "p":
            self.output.append("\n\n")

        # Pop matching tag from stack
        for i in range(len(self.tag_stack) - 1, -1, -1):
            if self.tag_stack[i][0] == tag:
                self.tag_stack.pop(i)
                break

    def handle_data(self, data):
        self.output.append(data)

    def handle_entityref(self, name):
        entities = {"amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'"}
        self.output.append(entities.get(name, f"&{name};"))

    def handle_charref(self, name):
        if name.startswith("x"):
            char = chr(int(name[1:], 16))
        else:
            char = chr(int(name))
        self.output.append(char)

    def get_markdown(self) -> str:
        result = "".join(self.output)
        # Clean up excessive newlines
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip()


def asana_html_to_markdown(html: str) -> str:
    """
    Convert Asana's AsanaText HTML to markdown.

    Args:
        html: Asana HTML string (typically wrapped in <body> tags)

    Returns:
        Markdown string
    """
    if not html:
        return ""

    converter = AsanaToMarkdownConverter()
    converter.feed(html)
    return converter.get_markdown()


def main():
    """CLI entry point for testing/debugging."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert Asana's AsanaText HTML to markdown"
    )
    parser.add_argument(
        "html",
        nargs="?",
        help="Asana HTML text to convert (reads from stdin if not provided)",
    )

    args = parser.parse_args()

    if args.html:
        text = args.html
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        parser.print_help()
        sys.exit(1)

    print(asana_html_to_markdown(text))


if __name__ == "__main__":
    main()
