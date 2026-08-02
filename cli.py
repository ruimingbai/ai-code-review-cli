#!/usr/bin/env python3
"""
ai-code-review-cli — Lightweight CLI for Automated PR Code Review.

A command-line tool designed for open-source maintainers to streamline
pull request reviews using AI-powered code analysis.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VERSION = "0.1.0"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.3

REVIEW_SYSTEM_PROMPT = """\
You are an expert code reviewer for open-source projects. Your task is to review
the provided git diff and produce a structured code review.

Follow these rules strictly:
1. Identify bugs, logic errors, security vulnerabilities, and performance issues.
2. Flag style inconsistencies, unclear naming, and missing documentation.
3. Suggest concrete, actionable improvements with code snippets where helpful.
4. Acknowledge good patterns and well-written code.
5. Classify each finding by severity: critical, warning, or suggestion.
6. Keep comments concise and respectful.

Output your review as valid JSON with the following schema:
{
  "summary": "<one-paragraph overall assessment>",
  "findings": [
    {
      "file": "<relative file path>",
      "line": <line number or null>,
      "severity": "critical | warning | suggestion",
      "category": "bug | security | performance | style | documentation | logic | other",
      "message": "<clear description of the issue>",
      "suggestion": "<optional concrete fix or code snippet>"
    }
  ],
  "approved": <true | false>
}
"""

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    file: str
    line: Optional[int]
    severity: str
    category: str
    message: str
    suggestion: Optional[str] = None


@dataclass
class ReviewResult:
    summary: str
    findings: list[Finding] = field(default_factory=list)
    approved: bool = True


# ---------------------------------------------------------------------------
# Diff helpers
# ---------------------------------------------------------------------------


def get_git_diff(base: str, head: str, cwd: Optional[Path] = None) -> str:
    """Fetch the unified diff between two git refs."""
    cmd = ["git", "diff", f"{base}...{head}"]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            cwd=str(cwd) if cwd else None,
        )
    except subprocess.CalledProcessError as exc:
        print(f"Error running git diff: {exc.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def estimate_diff_size(diff: str) -> int:
    """Rough token-count estimate (4 chars ≈ 1 token)."""
    return len(diff) // 4


def truncate_diff(diff: str, max_tokens: int) -> str:
    """Truncate diff to stay within token budget."""
    max_chars = max_tokens * 4
    if len(diff) <= max_chars:
        return diff
    lines = diff.splitlines()
    truncated: list[str] = []
    current = 0
    for line in lines:
        if current + len(line) + 1 > max_chars:
            truncated.append(f"... (truncated {len(lines) - len(truncated)} lines)")
            break
        truncated.append(line)
        current += len(line) + 1
    return "\n".join(truncated)


# ---------------------------------------------------------------------------
# OpenAI client wrapper
# ---------------------------------------------------------------------------


def call_openai(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
    base_url: Optional[str] = None,
) -> dict[str, Any]:
    """Send a chat-completion request to OpenAI-compatible API and return parsed JSON."""
    try:
        from openai import OpenAI
    except ImportError:
        print(
            "Missing 'openai' package. Install with: pip install openai",
            file=sys.stderr,
        )
        sys.exit(1)

    client_kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )

    raw = response.choices[0].message.content or "{}"

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"Failed to parse model response as JSON:\n{raw}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------


def format_markdown(result: ReviewResult) -> str:
    """Render review result as GitHub-flavoured Markdown."""
    lines: list[str] = [
        "## 🤖 AI Code Review",
        "",
        f"**Summary:** {result.summary}",
        "",
        f"**Verdict:** {'✅ Approved' if result.approved else '❌ Changes Requested'}",
        "",
        "---",
        "",
    ]

    if not result.findings:
        lines.append("_No findings — great work!_")
        return "\n".join(lines)

    sev_icon = {"critical": "🔴", "warning": "🟡", "suggestion": "🔵"}

    for i, f in enumerate(result.findings, 1):
        icon = sev_icon.get(f.severity, "⚪")
        loc = f"`{f.file}`" + (f":L{f.line}" if f.line is not None else "")
        lines.append(f"### {icon} Finding {i}: [{f.severity.upper()}] {f.category}")
        lines.append(f"**Location:** {loc}")
        lines.append(f"**Issue:** {f.message}")
        if f.suggestion:
            lines.append(f"**Suggestion:** {f.suggestion}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def format_terminal(result: ReviewResult) -> str:
    """Compact terminal output."""
    lines: list[str] = []
    lines.append(f"Summary: {result.summary}")
    lines.append(f"Verdict: {'APPROVED' if result.approved else 'CHANGES REQUESTED'}")
    lines.append("-" * 60)
    for f in result.findings:
        loc = f"{f.file}" + (f":{f.line}" if f.line is not None else "")
        lines.append(f"  [{f.severity[0].upper()}][{f.category}] {loc} — {f.message}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-code-review",
        description="AI-powered CLI code review tool for GitHub pull requests.",
    )

    parser.add_argument(
        "--base",
        default="main",
        help="Base git ref (default: main).",
    )
    parser.add_argument(
        "--head",
        default="HEAD",
        help="Head git ref (default: HEAD).",
    )
    parser.add_argument(
        "--diff-file",
        type=Path,
        help="Path to a pre-generated diff file (skips git diff).",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model name (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help=f"Max tokens for the review response (default: {DEFAULT_MAX_TOKENS}).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help=f"Sampling temperature (default: {DEFAULT_TEMPERATURE}).",
    )
    parser.add_argument(
        "--format",
        choices=["terminal", "markdown", "json"],
        default="terminal",
        help="Output format (default: terminal).",
    )
    parser.add_argument(
        "--api-key",
        help="OpenAI API key. Reads from OPENAI_API_KEY env var if omitted.",
    )
    parser.add_argument(
        "--base-url",
        help="Custom API base URL (for proxies or compatible backends).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"ai-code-review-cli {VERSION}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write output to file instead of stdout.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Resolve API key
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print(
            "Error: OpenAI API key required. Set OPENAI_API_KEY env var or use --api-key.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Obtain diff
    if args.diff_file:
        diff = args.diff_file.read_text(encoding="utf-8")
    else:
        diff = get_git_diff(args.base, args.head)
        if not diff.strip():
            print(
                f"No diff found between {args.base} and {args.head}. "
                "Is this a git repository with changes?",
                file=sys.stderr,
            )
            sys.exit(1)

    # Manage token budget
    model_max = 128_000 if "gpt-4" in args.model else 64_000
    estimated = estimate_diff_size(diff)
    if estimated > model_max // 2:
        diff = truncate_diff(diff, model_max // 2)

    user_prompt = f"Review the following git diff:\n\n```diff\n{diff}\n```"

    # Call AI
    raw = call_openai(
        api_key=api_key,
        model=args.model,
        system_prompt=REVIEW_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        base_url=args.base_url,
    )

    # Parse into dataclass
    findings = [
        Finding(
            file=f.get("file", ""),
            line=f.get("line"),
            severity=f.get("severity", "suggestion"),
            category=f.get("category", "other"),
            message=f.get("message", ""),
            suggestion=f.get("suggestion"),
        )
        for f in raw.get("findings", [])
    ]
    result = ReviewResult(
        summary=raw.get("summary", "No summary provided."),
        findings=findings,
        approved=raw.get("approved", True),
    )

    # Format & output
    if args.format == "markdown":
        output = format_markdown(result)
    elif args.format == "json":
        output = json.dumps(raw, indent=2, ensure_ascii=False)
    else:
        output = format_terminal(result)

    if args.output:
        args.output.write_text(output, encoding="utf-8")
        print(f"Review written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
