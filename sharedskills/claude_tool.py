"""Letta tool for invoking the Claude CLI (Claude Code) via subprocess."""

import subprocess


def call_claude(
    prompt: str,
    model: str = "sonnet",
    system_prompt: str = "",
    working_directory: str = "",
    allowed_tools: str = "",
    max_turns: int = 0,
    timeout: int = 120,
    output_format: str = "text",
) -> str:
    """Call the Claude CLI with a prompt and return the response.

    Args:
        prompt: The prompt/task to send to Claude.
        model: Model alias - "sonnet", "opus", or "haiku". Defaults to "sonnet".
        system_prompt: Optional system prompt to set context for Claude.
        working_directory: Optional working directory path (gives Claude project context).
        allowed_tools: Optional comma-separated tool restrictions (e.g. "Read,Grep,Glob" for read-only).
        max_turns: Max agentic turns. 0 means unlimited.
        timeout: Subprocess timeout in seconds. Defaults to 120.
        output_format: Output format - "text" or "json". Defaults to "text".

    Returns:
        Claude's text response, or an error message string on failure.
    """
    cmd = ["claude", "-p", "--model", model]

    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])

    if allowed_tools:
        cmd.extend(["--allowedTools", allowed_tools])

    if max_turns > 0:
        cmd.extend(["--max-turns", str(max_turns)])

    if output_format == "json":
        cmd.extend(["--output-format", "json"])

    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_directory or None,
        )
    except subprocess.TimeoutExpired:
        return f"Error: Claude CLI timed out after {timeout} seconds."
    except FileNotFoundError:
        return "Error: claude binary not found. Ensure Claude Code is installed and on PATH."

    if result.returncode != 0:
        stderr = result.stderr.strip()
        return f"Error: Claude CLI exited with code {result.returncode}. stderr: {stderr}"

    return result.stdout
