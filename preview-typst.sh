#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <typst-file>" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TINYMIST="$SCRIPT_DIR/vendor/tinymist"
TARGET="$(python3 -c 'import os,sys;print(os.path.abspath(sys.argv[1]))' "$1")"

if [[ ! -f "$TARGET" ]]; then
  echo "Typst file not found: $TARGET" >&2
  exit 1
fi

if [[ ! -x "$TINYMIST" ]]; then
  echo "Missing executable: $TINYMIST" >&2
  exit 1
fi

for PORT in 23625 23626; do
  if command -v fuser >/dev/null 2>&1; then
    fuser -k "${PORT}/tcp" >/dev/null 2>&1 || true
  fi
done

"$TINYMIST" preview "$TARGET" --host 127.0.0.1 --port 23625 &
TINY_PID=$!

sleep 1
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://127.0.0.1:23625" >/dev/null 2>&1 || true
fi

wait "$TINY_PID"
