#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if command -v python3 >/dev/null 2>&1 && python3 --version >/dev/null 2>&1; then
  python3 "$script_dir/generate_changelog.py" "$@"
else
  python "$script_dir/generate_changelog.py" "$@"
fi
