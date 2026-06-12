#!/usr/bin/env python3
"""Generate CHANGELOG.md from git history."""

from __future__ import annotations

import datetime as dt
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def latest_tag() -> Optional[str]:
    result = git("describe", "--tags", "--abbrev=0", check=False)
    tag = result.stdout.strip()
    return tag or None


def commit_subjects(commit_range: str) -> List[str]:
    result = git("log", "--no-merges", "--pretty=format:%s", commit_range)
    return [line for line in result.stdout.splitlines() if line.strip()]


def categorize(subject: str) -> str:
    lowered = subject.lower()
    added_prefixes = ("feat:", "add:", "added:", "add ", "adds ", "added ", "implement ", "implements ")
    fixed_prefixes = ("fix:", "bug:", "bugfix:", "fix ", "fixes ", "fixed ", "bug ")
    removed_prefixes = ("remove:", "removed:", "delete:", "deleted:", "remove ", "removes ", "removed ", "delete ", "deletes ")

    if starts_with_any(lowered, added_prefixes) or contains_any(lowered, (" add ", " adds ", " added ", " implement ", " implements ")):
        return "Added"
    if starts_with_any(lowered, fixed_prefixes) or contains_any(lowered, (" fix ", " fixes ", " fixed ", " bug ")):
        return "Fixed"
    if starts_with_any(lowered, removed_prefixes) or contains_any(lowered, (" remove ", " removes ", " removed ", " delete ", " deletes ")):
        return "Removed"
    return "Changed"


def starts_with_any(value: str, prefixes: tuple) -> bool:
    return value.startswith(prefixes)


def contains_any(value: str, markers: tuple) -> bool:
    return any(marker in value for marker in markers)


def section(title: str, entries: List[str]) -> str:
    lines = [f"### {title}", ""]
    if entries:
        lines.extend(f"- {entry}" for entry in entries)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    inside_work_tree = git("rev-parse", "--is-inside-work-tree", check=False)
    if inside_work_tree.returncode != 0:
        print("generate_changelog.py must be run inside a git repository.", file=sys.stderr)
        return 1

    output_path = Path(sys.argv[1] if len(sys.argv) > 1 else "CHANGELOG.md")
    tag = latest_tag()
    commit_range = f"{tag}..HEAD" if tag else "HEAD"
    range_label = f"since {tag}" if tag else "for all commits"

    buckets: Dict[str, List[str]] = {
        "Added": [],
        "Fixed": [],
        "Changed": [],
        "Removed": [],
    }

    subjects = commit_subjects(commit_range)
    for subject in subjects:
        buckets[categorize(subject)].append(subject)

    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    changelog = [
        "# Changelog",
        "",
        f"Generated from git history {range_label} on {today}.",
        "",
        section("Added", buckets["Added"]),
        section("Fixed", buckets["Fixed"]),
        section("Changed", buckets["Changed"]),
        section("Removed", buckets["Removed"]),
    ]
    output_path.write_text("\n".join(changelog), encoding="utf-8")
    print(f"Wrote {output_path} with {len(subjects)} commit(s) {range_label}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
