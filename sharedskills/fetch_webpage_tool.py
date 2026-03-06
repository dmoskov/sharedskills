"""Letta tool for fetching and parsing webpages to markdown."""

import re


def fetch_webpage(
    url: str,
    timeout: int = 30,
    max_length: int = 50000,
) -> str:
    """Fetch a webpage and convert its HTML content to readable markdown.

    Useful for reading documentation, blog posts, articles, or any public
    web page. Returns the page content as clean markdown text.

    Args:
        url: The URL to fetch. Must be a valid HTTP or HTTPS URL.
        timeout: Request timeout in seconds. Defaults to 30.
        max_length: Maximum character length of returned content. Defaults to
            50000. Content is truncated with a notice if it exceeds this limit.

    Returns:
        The webpage content as markdown text, or an error message string
        on failure.
    """
    try:
        import requests
    except ImportError:
        return "Error: requests package not installed. pip install requests"

    if not url or not url.strip():
        return "Error: URL is required."

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; LettaAgent/1.0; "
            "+https://github.com/letta-ai/letta)"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return f"Error: Request timed out after {timeout} seconds."
    except requests.exceptions.ConnectionError as e:
        return f"Error: Could not connect to {url}: {e}"
    except requests.exceptions.HTTPError as e:
        return f"Error: HTTP {resp.status_code} for {url}: {e}"
    except Exception as e:
        return f"Error fetching {url}: {e}"

    content_type = resp.headers.get("Content-Type", "")
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        return f"Content-Type is {content_type}, not HTML. Raw content:\n{resp.text[:max_length]}"

    html = resp.text
    markdown = _html_to_markdown(html)

    if len(markdown) > max_length:
        markdown = markdown[:max_length] + f"\n\n... [truncated at {max_length} chars]"

    return markdown


def _html_to_markdown(html: str) -> str:
    """Convert HTML to readable markdown using basic regex transforms.

    This is a lightweight converter that handles common HTML elements without
    requiring external dependencies like beautifulsoup4 or markdownify.
    """
    # Remove script and style blocks
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.I)
    text = re.sub(r"<nav[^>]*>.*?</nav>", "", text, flags=re.DOTALL | re.I)
    text = re.sub(r"<footer[^>]*>.*?</footer>", "", text, flags=re.DOTALL | re.I)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # Headers
    for i in range(1, 7):
        text = re.sub(
            rf"<h{i}[^>]*>(.*?)</h{i}>",
            lambda m, level=i: f"\n{'#' * level} {m.group(1).strip()}\n",
            text,
            flags=re.DOTALL | re.I,
        )

    # Links
    text = re.sub(
        r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        r"[\2](\1)",
        text,
        flags=re.DOTALL | re.I,
    )

    # Bold/italic
    text = re.sub(
        r"<(strong|b)[^>]*>(.*?)</\1>", r"**\2**", text, flags=re.DOTALL | re.I
    )
    text = re.sub(r"<(em|i)[^>]*>(.*?)</\1>", r"*\2*", text, flags=re.DOTALL | re.I)

    # Code blocks
    text = re.sub(
        r"<pre[^>]*>(.*?)</pre>", r"\n```\n\1\n```\n", text, flags=re.DOTALL | re.I
    )
    text = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", text, flags=re.DOTALL | re.I)

    # Lists
    text = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", text, flags=re.DOTALL | re.I)

    # Paragraphs and line breaks
    text = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\1\n", text, flags=re.DOTALL | re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<hr\s*/?>", "\n---\n", text, flags=re.I)

    # Remove remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Decode common HTML entities
    _entities = {
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&#39;": "'",
        "&apos;": "'",
        "&nbsp;": " ",
        "&mdash;": "\u2014",
        "&ndash;": "\u2013",
        "&hellip;": "\u2026",
    }
    for entity, char in _entities.items():
        text = text.replace(entity, char)

    # Clean up whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
