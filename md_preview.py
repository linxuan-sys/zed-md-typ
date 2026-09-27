#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import http.server
import json
import os
import shutil
import socketserver
import subprocess
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path


class MarkdownState:
    def __init__(self, markdown_path: Path, project_root: Path) -> None:
        self.markdown_path = markdown_path
        self.project_root = project_root
        self.vendor_katex = project_root / "vendor" / "katex"
        self.pandoc_path = project_root / "bin" / "pandoc"
        self.version = 0
        self._mtime = -1.0
        self._content = ""
        self._lock = threading.Lock()
        self.refresh_if_needed(force=True)

    def refresh_if_needed(self, force: bool = False) -> None:
        try:
            mtime = self.markdown_path.stat().st_mtime
        except FileNotFoundError:
            rendered = "<p><strong>File was removed.</strong></p>"
            mtime = -1.0
        else:
            if not force and mtime == self._mtime:
                return
            rendered = self._render_markdown()

        with self._lock:
            if force or mtime != self._mtime or rendered != self._content:
                self._mtime = mtime
                self._content = rendered
                self.version += 1

    def snapshot(self) -> tuple[int, str]:
        with self._lock:
            return self.version, self._content

    def _render_markdown(self) -> str:
        command = None
        if self.pandoc_path.exists() and os.access(self.pandoc_path, os.X_OK):
            command = [str(self.pandoc_path)]
        elif shutil.which("pandoc"):
            command = ["pandoc"]

        if command:
            command.extend([
                "--from",
                "markdown+tex_math_dollars+tex_math_single_backslash",
                "--to",
                "html",
                str(self.markdown_path),
            ])
            try:
                completed = subprocess.run(
                    command,
                    check=True,
                    capture_output=True,
                    text=True,
                    cwd=str(self.markdown_path.parent),
                )
            except subprocess.CalledProcessError as exc:
                escaped = html.escape(exc.stderr.strip() or "pandoc failed")
                return f"<pre>{escaped}</pre>"
            return completed.stdout

        escaped = html.escape(self.markdown_path.read_text(encoding="utf-8"))
        return f"<pre>{escaped}</pre>"


class PreviewHandler(http.server.BaseHTTPRequestHandler):
    state: MarkdownState

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        self.state.refresh_if_needed()
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)

        if path == "/":
            self._send_html(self._page_template())
            return

        if path == "/api/state":
            version, _ = self.state.snapshot()
            self._send_json({"version": version})
            return

        if path == "/api/content":
            _, content = self.state.snapshot()
            self._send_html(content)
            return

        if path.startswith("/katex/"):
            local = self.state.vendor_katex / path.removeprefix("/katex/")
            self._send_static(local)
            return

        source_file = (self.state.markdown_path.parent / path.lstrip("/")).resolve()
        if self._is_in_directory(source_file, self.state.markdown_path.parent):
            self._send_static(source_file)
            return

        self.send_error(404, "Not found")

    def _page_template(self) -> str:
        katex_available = (self.state.vendor_katex / "katex.min.js").exists()
        katex_blocks = ""
        render_call = ""
        if katex_available:
            katex_blocks = """
<link rel=\"stylesheet\" href=\"/katex/katex.min.css\" />
<script defer src=\"/katex/katex.min.js\"></script>
<script defer src=\"/katex/contrib/auto-render.min.js\"></script>
"""
            render_call = """
if (window.renderMathInElement) {
  window.renderMathInElement(root, {
    delimiters: [
      {left: '$$', right: '$$', display: true},
      {left: '$', right: '$', display: false},
      {left: '\\(', right: '\\)', display: false},
      {left: '\\[', right: '\\]', display: true}
    ]
  });
}
"""

        return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{html.escape(self.state.markdown_path.name)}</title>
  {katex_blocks}
  <style>
    body {{ margin: 0; background: #fafafa; color: #222; font: 16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    main {{ max-width: 960px; margin: 0 auto; padding: 24px; background: white; min-height: 100vh; box-sizing: border-box; }}
    pre {{ overflow: auto; }}
    code {{ background: #f2f2f2; padding: 0.1em 0.25em; border-radius: 4px; }}
  </style>
</head>
<body>
  <main id=\"content\">Loading...</main>
  <script>
    const root = document.getElementById('content');
    let version = -1;

    async function refresh(force = false) {{
      const state = await fetch('/api/state', {{ cache: 'no-store' }}).then(r => r.json());
      if (!force && state.version === version) return;
      version = state.version;
      const content = await fetch('/api/content', {{ cache: 'no-store' }}).then(r => r.text());
      root.innerHTML = content;
      {render_call}
    }}

    refresh(true);
    setInterval(() => refresh(false).catch(() => {{}}), 1000);
  </script>
</body>
</html>
"""

    def _send_json(self, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_html(self, html_text: str) -> None:
        data = html_text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_static(self, path: Path) -> None:
        try:
            if not path.is_file():
                raise FileNotFoundError
            data = path.read_bytes()
        except FileNotFoundError:
            self.send_error(404, "Not found")
            return

        ctype = self.guess_type(str(path))
        self.send_response(200)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8" if ctype.startswith("text/") else ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def guess_type(self, path: str) -> str:
        return http.server.SimpleHTTPRequestHandler.extensions_map.get(Path(path).suffix.lower(), "application/octet-stream")

    @staticmethod
    def _is_in_directory(path: Path, base: Path) -> bool:
        try:
            path.relative_to(base)
            return True
        except ValueError:
            return False


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline Markdown preview server")
    parser.add_argument("markdown_file", help="Path to markdown file")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0, help="0 means auto-select")
    parser.add_argument("--no-open", action="store_true", help="Do not open browser automatically")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    markdown_path = Path(args.markdown_file).expanduser().resolve()
    if not markdown_path.is_file():
        print(f"Markdown file not found: {markdown_path}")
        return 1

    project_root = Path(__file__).resolve().parent
    PreviewHandler.state = MarkdownState(markdown_path, project_root)

    with ThreadingHTTPServer((args.host, args.port), PreviewHandler) as server:
        host, port = server.server_address
        url = f"http://{host}:{port}/"
        print(f"Previewing: {markdown_path}")
        print(f"Open in browser: {url}")

        if not args.no_open:
            try:
                if shutil.which("xdg-open"):
                    subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    webbrowser.open(url)
            except Exception:
                pass

        try:
            server.serve_forever(poll_interval=0.5)
        except KeyboardInterrupt:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
