#!/usr/bin/env python3
"""Smoke tests for destructive_bash_guard.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HOOK = ROOT / "destructive_bash_guard.py"


def run_hook(command: str, tmp_home: Path) -> subprocess.CompletedProcess[str]:
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": str(ROOT),
    }
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "HOME": str(tmp_home), "USERPROFILE": str(tmp_home)},
        check=False,
    )


def assert_blocked(command: str, tmp_home: Path) -> None:
    result = run_hook(command, tmp_home)
    assert result.returncode == 2, (command, result.returncode, result.stderr)
    assert "Blocked destructive Bash command" in result.stderr


def assert_allowed(command: str, tmp_home: Path) -> None:
    result = run_hook(command, tmp_home)
    assert result.returncode == 0, (command, result.returncode, result.stderr)


def main() -> int:
    with tempfile.TemporaryDirectory() as home:
        tmp_home = Path(home)
        for command in (
            "rm -rf build",
            "npm test && rm -rf build",
            "npm test || rm -rf build",
            "psql -c 'DROP TABLE users'",
            "git push --force origin main",
            "git push --force-with-lease=main origin main",
            "sqlite3 app.db 'TRUNCATE sessions'",
            "sqlite3 app.db 'DELETE FROM users;'",
        ):
            assert_blocked(command, tmp_home)

        for command in (
            "rm -r build",
            "git push origin main",
            "sqlite3 app.db 'DELETE FROM users WHERE id = 1;'",
            "npm test",
        ):
            assert_allowed(command, tmp_home)

        log_path = tmp_home / ".claude" / "hooks" / "blocked.log"
        entries = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
        assert len(entries) == 8
        assert all("timestamp" in entry and "project_path" in entry and "command" in entry for entry in entries)

        invalid_json = subprocess.run(
            [sys.executable, str(HOOK)],
            input="{",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "HOME": str(tmp_home), "USERPROFILE": str(tmp_home)},
            check=False,
        )
        assert invalid_json.returncode == 2
        assert "could not be parsed" in invalid_json.stderr

    print("destructive_bash_guard smoke tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
