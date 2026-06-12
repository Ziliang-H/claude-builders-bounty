#!/usr/bin/env bash
set -euo pipefail

hook_dir="${HOME}/.claude/hooks"
mkdir -p "$hook_dir"
cp "$(dirname "$0")/destructive_bash_guard.py" "$hook_dir/destructive_bash_guard.py"
chmod +x "$hook_dir/destructive_bash_guard.py"

echo "Installed destructive_bash_guard.py to $hook_dir"
echo "Add it to your Claude Code PreToolUse hooks for the Bash tool."
