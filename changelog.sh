#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python_cmd=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 8))'; then
    python_cmd="$candidate"
    break
  fi
done

if [ -z "$python_cmd" ]; then
  echo "Python 3.8 or newer is required to generate the changelog." >&2
  exit 1
fi

"$python_cmd" "$script_dir/generate_changelog.py" "$@"
