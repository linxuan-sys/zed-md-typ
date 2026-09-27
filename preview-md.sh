#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <markdown-file>" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$1"

if [[ ! -f "$TARGET" ]]; then
  echo "Markdown file not found: $TARGET" >&2
  exit 1
fi

exec python3 "$SCRIPT_DIR/md_preview.py" "$TARGET"
