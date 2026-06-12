# Destructive Bash Guard

Claude Code `PreToolUse` hook that blocks destructive Bash commands before they run.

## Install

```bash
bash hooks/install.sh
```

Add this hook to your Claude Code settings for the `PreToolUse` event and the `Bash` tool.
Replace `/home/you` with your absolute home directory:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "/home/you/.claude/hooks/destructive_bash_guard.py"
          }
        ]
      }
    ]
  }
}
```

The hook reads Claude Code hook JSON from stdin, inspects `tool_input.command`,
and exits with code `2` when it blocks a command. Claude Code receives the stderr
message explaining why the command was blocked.

## Blocked Patterns

- `rm -rf`: recursive force deletion can permanently remove project files.
- `DROP TABLE`: schema deletion can destroy database data.
- `git push --force` and `git push --force-with-lease`: force pushes can overwrite shared history.
- `TRUNCATE`: table truncation erases rows immediately.
- `DELETE FROM` without a `WHERE` clause: unrestricted deletes can erase every row.

Every blocked attempt is appended to `~/.claude/hooks/blocked.log` as JSON with
timestamp, attempted command, project path, and matched rule.

Normal Bash commands and non-Bash tools exit `0` and continue unchanged.
