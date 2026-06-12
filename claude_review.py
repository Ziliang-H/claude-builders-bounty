#!/usr/bin/env python3
"""Generate a structured Markdown review for a GitHub pull request."""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterable, List


PR_RE = re.compile(r"^https://github\.com/([^/]+)/([^/]+)/pull/(\d+)(?:[/?#].*)?$")
FILE_RE = re.compile(r"^\+\+\+ b/(.+)$")
HUNK_RE = re.compile(r"^@@")


@dataclass
class DiffStats:
    files: List[str]
    additions: int
    deletions: int
    hunks: int
    has_tests: bool
    has_docs: bool
    has_workflows: bool
    has_lockfile: bool
    has_deletions: bool


def parse_pr_url(url: str) -> tuple[str, str, str]:
    match = PR_RE.match(url)
    if not match:
        raise ValueError("Expected a GitHub PR URL like https://github.com/owner/repo/pull/123")
    return match.group(1), match.group(2), match.group(3)


def fetch_diff(owner: str, repo: str, number: str) -> str:
    url = f"https://github.com/{owner}/{repo}/pull/{number}.diff"
    request = urllib.request.Request(url, headers={"User-Agent": "claude-review"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub returned HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not fetch PR diff from {url}: {exc.reason}") from exc


def analyze_diff(diff: str) -> DiffStats:
    files: List[str] = []
    additions = 0
    deletions = 0
    hunks = 0

    for line in diff.splitlines():
        file_match = FILE_RE.match(line)
        if file_match and file_match.group(1) != "/dev/null":
            files.append(file_match.group(1))
        elif line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1
        elif HUNK_RE.match(line):
            hunks += 1

    normalized = [path.lower() for path in files]
    return DiffStats(
        files=files,
        additions=additions,
        deletions=deletions,
        hunks=hunks,
        has_tests=any("test" in path or "spec" in path for path in normalized),
        has_docs=any(path.endswith((".md", ".mdx", ".rst")) or "docs/" in path for path in normalized),
        has_workflows=any(path.startswith(".github/workflows/") for path in normalized),
        has_lockfile=any(path.endswith(("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock")) for path in normalized),
        has_deletions=deletions > additions * 2 and deletions > 20,
    )


def bullet_list(items: Iterable[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def risks(stats: DiffStats) -> List[str]:
    found: List[str] = []
    if len(stats.files) > 12 or stats.hunks > 30:
        found.append("Large diff surface: review behavior by feature area and consider splitting follow-up changes.")
    if not stats.has_tests and not stats.has_docs:
        found.append("No obvious tests or docs changed, so behavior may be harder to verify from the PR alone.")
    if stats.has_workflows:
        found.append("Workflow changes can affect CI permissions, secrets exposure, and contributor trust boundaries.")
    if stats.has_lockfile:
        found.append("Lockfile changes may introduce transitive dependency updates that deserve a dependency review.")
    if stats.has_deletions:
        found.append("Deletion-heavy change: check for removed compatibility paths, migrations, or public APIs.")
    if not found:
        found.append("No high-risk pattern is obvious from the diff statistics; still review domain behavior manually.")
    return found


def suggestions(stats: DiffStats) -> List[str]:
    found: List[str] = []
    if not stats.has_tests:
        found.append("Add or link focused tests for the changed behavior, especially edge cases and failure paths.")
    if stats.has_docs:
        found.append("Verify the documentation matches current commands and setup paths by following it once locally.")
    if len(stats.files) > 1:
        found.append("Review each changed file for ownership boundaries so unrelated cleanup does not hide behavior changes.")
    found.append("Confirm the PR description states user impact, validation performed, and any known limitations.")
    return found


def confidence(stats: DiffStats) -> str:
    if stats.has_tests and len(stats.files) <= 8 and stats.hunks <= 20:
        return "High"
    if stats.has_tests or stats.has_docs:
        return "Medium"
    return "Low"


def render_review(owner: str, repo: str, number: str, stats: DiffStats) -> str:
    files_preview = ", ".join(stats.files[:6])
    if len(stats.files) > 6:
        files_preview += f", and {len(stats.files) - 6} more"

    summary = (
        f"This PR changes {len(stats.files)} file(s) in `{owner}/{repo}`, with "
        f"{stats.additions} added line(s), {stats.deletions} removed line(s), and {stats.hunks} diff hunk(s). "
        f"The main touched paths are: {files_preview or 'no files detected from diff'}."
    )
    validation = (
        "The diff appears to include test coverage." if stats.has_tests else
        "The diff does not obviously include tests, so external validation evidence is important."
    )

    return "\n".join(
        [
            "## Claude Review",
            "",
            "### Summary",
            f"{summary} {validation}",
            "",
            "### Identified Risks",
            bullet_list(risks(stats)),
            "",
            "### Improvement Suggestions",
            bullet_list(suggestions(stats)),
            "",
            f"### Confidence Score: {confidence(stats)}",
            "",
            "_Generated by `claude-review` from the public GitHub diff._",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Review a GitHub pull request diff.")
    parser.add_argument("--pr", required=True, help="GitHub PR URL, e.g. https://github.com/owner/repo/pull/123")
    args = parser.parse_args()

    try:
        owner, repo, number = parse_pr_url(args.pr)
        diff = fetch_diff(owner, repo, number)
        stats = analyze_diff(diff)
        print(render_review(owner, repo, number, stats))
    except (RuntimeError, ValueError) as exc:
        print(f"claude-review: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
