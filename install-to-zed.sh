#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZED_DIR="$HOME/.config/zed"
TS="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$ZED_DIR"

cp "$SCRIPT_DIR/md_preview.py" "$ZED_DIR/md_preview.py"
cp "$SCRIPT_DIR/preview-typst.sh" "$ZED_DIR/typst_preview.sh"
chmod +x "$ZED_DIR/typst_preview.sh" "$ZED_DIR/md_preview.py"

mkdir -p "$ZED_DIR/vendor"
rm -rf "$ZED_DIR/vendor/katex" "$ZED_DIR/vendor/bin" "$ZED_DIR/vendor/tinymist"
cp -R "$SCRIPT_DIR/vendor/katex" "$ZED_DIR/vendor/katex"
cp -R "$SCRIPT_DIR/vendor/bin" "$ZED_DIR/vendor/bin"
cp "$SCRIPT_DIR/vendor/tinymist" "$ZED_DIR/vendor/tinymist"
chmod +x "$ZED_DIR/vendor/tinymist" "$ZED_DIR/vendor/bin/pandoc" 2>/dev/null || true

for FILE in tasks.json keymap.json; do
  if [[ -f "$ZED_DIR/$FILE" ]]; then
    cp "$ZED_DIR/$FILE" "$ZED_DIR/$FILE.bak.$TS"
  fi
done

python3 "$SCRIPT_DIR/merge-zed-config.py" --type tasks --target "$ZED_DIR/tasks.json" --snippet "$SCRIPT_DIR/zed/tasks.json"
python3 "$SCRIPT_DIR/merge-zed-config.py" --type keymap --target "$ZED_DIR/keymap.json" --snippet "$SCRIPT_DIR/zed/keymap.json"

echo "Installed to $ZED_DIR"
echo "Backups: $ZED_DIR/tasks.json.bak.$TS / $ZED_DIR/keymap.json.bak.$TS (if originals existed)"
