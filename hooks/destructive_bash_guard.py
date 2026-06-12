#!/usr/bin/env python3
"""Claude Code PreToolUse hook that blocks destructive Bash commands."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

LOG_PATH = Path.home() / ".claude" / "hooks" / "blocked.log"

BLOCK_RULES: Tuple[Tuple[str, re.Pattern[str], str], ...] = (
    (
        "recursive force delete",
        re.compile(r"(?is)(?:^|[;&|]{1,2}\s*)rm\s+(?=[^;&|]*-[^\s;&|]*r)(?=[^;&|]*-[^\s;&|]*f)\S*(?:\s|$)"),
        "rm -rf can permanently delete files.",
    ),
    (
        "drop table",
        re.compile(r"(?is)\bdrop\s+table\b"),
        "DROP TABLE can remove database schema and data.",
    ),
    (
        "force push",
        re.compile(r"(?is)\bgit\s+push\b[^\n;&|]*(?:--force(?:-with-lease)?(?:=\S+)?|-f)(?:\s|$)"),
        "git push --force can overwrite shared history.",
    ),
    (
        "truncate",
        re.compile(r"(?is)\btruncate(?:\s+table)?\b"),
        "TRUNCATE can erase table contents immediately.",
    ),
)

DELETE_FROM_RE = re.compile(r"(?is)\bdelete\s+from\b")
WHERE_RE = re.compile(r"(?is)\bwhere\b")


def load_payload() -> Dict[str, Any]:
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        log_parse_failure(str(exc))
        print(f"Blocked because the PreToolUse hook JSON could not be parsed: {exc}", file=sys.stderr)
        raise SystemExit(2)


def bash_command(payload: Dict[str, Any]) -> Optional[str]:
    if payload.get("tool_name") != "Bash":
        return None

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None

    command = tool_input.get("command")
    return command if isinstance(command, str) else None


def first_violation(command: str) -> Optional[Tuple[str, str]]:
    for rule_name, pattern, reason in BLOCK_RULES:
        if pattern.search(command):
            return rule_name, reason
    if has_delete_without_where(command):
        return "delete without where", "DELETE FROM without a WHERE clause can erase every row."
    return None


def has_delete_without_where(command: str) -> bool:
    for match in DELETE_FROM_RE.finditer(command):
        statement = command[match.start() :].split(";", 1)[0]
        if not WHERE_RE.search(statement):
            return True
    return False


def project_path(payload: Dict[str, Any]) -> str:
    for key in ("cwd", "workspace_path", "project_path"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return os.getcwd()


def log_block(payload: Dict[str, Any], command: str, rule_name: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    record = {
        "timestamp": timestamp,
        "project_path": project_path(payload),
        "rule": rule_name,
        "command": command,
    }
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_parse_failure(error: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    record = {
        "timestamp": timestamp,
        "project_path": os.getcwd(),
        "rule": "invalid hook json",
        "command": "",
        "error": error,
    }
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> int:
    payload = load_payload()
    command = bash_command(payload)
    if command is None:
        return 0

    violation = first_violation(command)
    if violation is None:
        return 0

    rule_name, reason = violation
    log_block(payload, command, rule_name)
    print(
        "Blocked destructive Bash command before execution.\n"
        f"Reason: {reason}\n"
        "Use a narrower, reversible command or ask the user for explicit approval.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
