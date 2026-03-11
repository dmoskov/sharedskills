"""Letta tool for web search using Anthropic's built-in server-side search."""

import os


def web_search(
    query: str,
    max_uses: int = 5,
    allowed_domains: str = "",
    blocked_domains: str = "",
) -> str:
    """Search the web using Anthropic's built-in web search tool.

    Uses Claude Sonnet with server-side web search ($0.01/search). Returns
    formatted results with citations and source URLs.

    Args:
        query: The search query. Be specific for better results.
        max_uses: Maximum number of search requests Claude can make (1-10).
        allowed_domains: Comma-separated domains to restrict to
            (e.g. "arxiv.org,github.com"). Leave empty for all.
        blocked_domains: Comma-separated domains to exclude
            (e.g. "pinterest.com"). Leave empty for none.

    Returns:
        Formatted search results with citations and sources, or an error
        message string on failure.
    """
    try:
        import anthropic
    except ImportError:
        return "Error: anthropic package not installed. pip install anthropic"

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY environment variable not set."

    client = anthropic.Anthropic(api_key=api_key)

    tool_def: dict = {
        "type": "web_search_20260209",
        "name": "web_search",
        "max_uses": min(max(1, max_uses), 10),
    }

    if allowed_domains and allowed_domains.strip():
        tool_def["allowed_domains"] = [
            d.strip() for d in allowed_domains.split(",") if d.strip()
        ]
    elif blocked_domains and blocked_domains.strip():
        tool_def["blocked_domains"] = [
            d.strip() for d in blocked_domains.split(",") if d.strip()
        ]

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            tools=[tool_def],
            messages=[{"role": "user", "content": query}],
        )
    except Exception as e:
        return f"Error calling Anthropic API: {e}"

    parts: list[str] = []
    sources: list[tuple[str, str, str]] = []

    for block in response.content:
        block_type = getattr(block, "type", None)

        if block_type == "text":
            parts.append(block.text)
            if hasattr(block, "citations") and block.citations:
                for cite in block.citations:
                    url = getattr(cite, "url", "")
                    title = getattr(cite, "title", "")
                    cited = getattr(cite, "cited_text", "")
                    if url and url not in [s[1] for s in sources]:
                        sources.append((title, url, cited[:200]))

        elif block_type == "web_search_tool_result":
            content = getattr(block, "content", [])
            if isinstance(content, list):
                for r in content:
                    if getattr(r, "type", "") == "web_search_result":
                        url = getattr(r, "url", "")
                        title = getattr(r, "title", "")
                        age = getattr(r, "page_age", "")
                        if url and url not in [s[1] for s in sources]:
                            sources.append(
                                (title, url, f"Published: {age}" if age else "")
                            )

    result = "\n\n".join(parts) if parts else "No results found."

    if sources:
        result += "\n\n## Sources\n"
        for title, url, snippet in sources[:10]:
            result += f"- [{title}]({url})"
            if snippet:
                result += f": {snippet}"
            result += "\n"

    usage = response.usage
    search_count = 0
    if hasattr(usage, "server_tool_use") and usage.server_tool_use:
        search_count = getattr(usage.server_tool_use, "web_search_requests", 0)
    result += (
        f"\n_Searches: {search_count} | "
        f"Tokens: {usage.input_tokens}in/{usage.output_tokens}out_"
    )

    return result
