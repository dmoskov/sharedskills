#!/usr/bin/env python3
"""
Gemini Self-Critique

Uses Google's Gemini model to provide external critique of completed work.
Implements the "confessions" pattern for AI honesty and error detection:
an independent model reviews what was just built, so the author model's
blind spots don't go unchallenged.

Usage:
    # Critique specific files with task description
    python gemini_critique.py --task "Implemented auth" --files src/auth.py

    # Critique recent git changes
    python gemini_critique.py --git-diff HEAD~1

    # Critique with custom prompt
    python gemini_critique.py --task "Added caching" --files cache.py --focus security

API Key Setup:
    Option 1: Environment variable GEMINI_API_KEY
    Option 2: File at ~/.config/ai-dev-tools/gemini_api_key

Model:
    Pinned to a specific Gemini model ID; override with the GEMINI_MODEL
    environment variable. Pin exact IDs — floating aliases can silently
    change behavior under you.

Stdlib-only: no dependencies beyond Python 3.8+.
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import urllib.request
import urllib.error

DEFAULT_MODEL = "gemini-3.5-flash"


@dataclass
class CritiqueIssue:
    """A single issue found during critique."""

    category: str  # correctness, security, performance, maintainability, completeness
    severity: str  # critical, high, medium, low
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class CritiqueResult:
    """Result of a critique session."""

    task_description: str
    files_reviewed: List[str]
    issues: List[CritiqueIssue]
    summary: str
    confidence: float  # 0-1, how confident Gemini is in the critique
    timestamp: str


def get_api_key() -> Optional[str]:
    """Get Gemini API key from environment or config file."""
    # Try environment first
    if api_key := os.environ.get("GEMINI_API_KEY"):
        return api_key

    # Try config file (legacy location honored for older installs)
    for config_path in (
        Path.home() / ".config" / "ai-dev-tools" / "gemini_api_key",
        Path.home() / ".config" / "claude-code-scaffold" / "gemini_api_key",
    ):
        if config_path.exists():
            return config_path.read_text().strip()

    return None


def read_files(file_paths: List[str]) -> dict:
    """Read contents of specified files."""
    contents = {}
    for path in file_paths:
        try:
            with open(path, "r") as f:
                contents[path] = f.read()
        except Exception as e:
            contents[path] = f"[Error reading file: {e}]"
    return contents


def get_git_diff(ref: str = "HEAD~1") -> str:
    """Get git diff for recent changes."""
    try:
        result = subprocess.run(
            ["git", "diff", ref, "--", "*.py", "*.rs", "*.ts", "*.tsx", "*.js"],
            capture_output=True,
            text=True,
        )
        return result.stdout or "No changes found"
    except Exception as e:
        return f"Error getting git diff: {e}"


def call_gemini(prompt: str, api_key: str) -> dict:
    """Call Gemini API with the critique prompt."""
    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 4096,
        },
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise Exception(f"Gemini API error {e.code}: {error_body}")


def build_critique_prompt(
    task: str, code_content: str, focus: Optional[str] = None
) -> str:
    """Build the critique prompt for Gemini."""
    focus_instruction = ""
    if focus:
        focus_instruction = f"\n\nPay special attention to {focus} issues."

    return f"""You are a senior code reviewer performing a thorough critique of recently completed work.

TASK DESCRIPTION:
{task}

CODE TO REVIEW:
{code_content}

{focus_instruction}

Please analyze this code critically and identify potential issues. Be honest and thorough - it's better to flag a potential issue than to miss a real bug.

For each issue found, provide:
1. Category: correctness, security, performance, maintainability, or completeness
2. Severity: critical (will cause bugs/security issues), high (likely problems), medium (should fix), low (suggestions)
3. Description of the issue
4. File and line number if applicable
5. Suggested fix

Also provide:
- A summary of overall code quality
- Your confidence level (0-1) in this critique

Respond in this exact JSON format:
{{
    "issues": [
        {{
            "category": "correctness",
            "severity": "high",
            "description": "Description of the issue",
            "file_path": "path/to/file.py",
            "line_number": 42,
            "suggestion": "How to fix it"
        }}
    ],
    "summary": "Overall assessment of the code quality",
    "confidence": 0.85
}}

If no issues are found, return an empty issues array but still provide a summary.
Be specific and actionable. Focus on real problems, not style preferences."""


def parse_gemini_response(response: dict) -> tuple:
    """Parse Gemini response into issues and summary."""
    try:
        text = response["candidates"][0]["content"]["parts"][0]["text"]

        # Try to extract JSON from the response
        # Handle markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        data = json.loads(text.strip())

        issues = [CritiqueIssue(**issue) for issue in data.get("issues", [])]
        summary = data.get("summary", "No summary provided")
        confidence = data.get("confidence", 0.5)

        return issues, summary, confidence
    except Exception as e:
        print(f"Warning: Could not parse Gemini response: {e}")
        return [], "Failed to parse critique response", 0.0


def run_critique(
    task: str,
    files: Optional[List[str]] = None,
    git_diff: Optional[str] = None,
    focus: Optional[str] = None,
    output_json: bool = False,
) -> CritiqueResult:
    """Run a critique session."""
    api_key = get_api_key()
    if not api_key:
        print("Error: No Gemini API key found.")
        print("Set GEMINI_API_KEY environment variable or create:")
        print("  ~/.config/ai-dev-tools/gemini_api_key")
        sys.exit(1)

    # Gather code content
    if git_diff:
        code_content = f"GIT DIFF:\n{get_git_diff(git_diff)}"
        files_reviewed = ["git diff"]
    elif files:
        file_contents = read_files(files)
        code_content = "\n\n".join(
            f"=== {path} ===\n{content}" for path, content in file_contents.items()
        )
        files_reviewed = files
    else:
        print("Error: Must provide --files or --git-diff")
        sys.exit(1)

    # Build and send prompt
    prompt = build_critique_prompt(task, code_content, focus)

    print("Sending to Gemini for critique...")
    response = call_gemini(prompt, api_key)

    # Parse response
    issues, summary, confidence = parse_gemini_response(response)

    result = CritiqueResult(
        task_description=task,
        files_reviewed=files_reviewed,
        issues=issues,
        summary=summary,
        confidence=confidence,
        timestamp=datetime.now().isoformat(),
    )

    return result


def print_result(result: CritiqueResult, output_json: bool = False):
    """Print critique result."""
    if output_json:
        print(json.dumps(asdict(result), indent=2, default=str))
        return

    print("\n" + "=" * 60)
    print("CRITIQUE RESULT")
    print("=" * 60)
    print(f"Task: {result.task_description}")
    print(f"Files: {', '.join(result.files_reviewed)}")
    print(f"Confidence: {result.confidence:.0%}")
    print(f"\nSummary: {result.summary}")

    if result.issues:
        print(f"\n{len(result.issues)} Issues Found:")
        print("-" * 40)

        for i, issue in enumerate(result.issues, 1):
            severity_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
            }.get(issue.severity, "⚪")

            print(f"\n{i}. {severity_icon} [{issue.severity.upper()}] {issue.category}")
            print(f"   {issue.description}")
            if issue.file_path:
                loc = f"{issue.file_path}"
                if issue.line_number:
                    loc += f":{issue.line_number}"
                print(f"   Location: {loc}")
            if issue.suggestion:
                print(f"   Fix: {issue.suggestion}")
    else:
        print("\n✅ No issues found!")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Gemini-powered self-critique for completed work",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --task "Added user auth" --files src/auth.py src/middleware.py
  %(prog)s --git-diff HEAD~1 --task "Recent changes"
  %(prog)s --task "Caching layer" --files cache.py --focus security
        """,
    )

    parser.add_argument(
        "--task", "-t", required=True, help="Description of the task that was completed"
    )
    parser.add_argument("--files", "-f", nargs="+", help="Files to review")
    parser.add_argument(
        "--git-diff",
        "-g",
        metavar="REF",
        help="Review git diff against reference (e.g., HEAD~1)",
    )
    parser.add_argument(
        "--focus",
        choices=["security", "performance", "correctness", "maintainability"],
        help="Focus critique on specific category",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if not args.files and not args.git_diff:
        parser.error("Must provide --files or --git-diff")

    result = run_critique(
        task=args.task,
        files=args.files,
        git_diff=args.git_diff,
        focus=args.focus,
        output_json=args.json,
    )

    print_result(result, output_json=args.json)

    # Exit with error code if critical issues found
    critical_count = sum(1 for i in result.issues if i.severity == "critical")
    if critical_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
