#!/usr/bin/env python3
"""Zed 浏览器 Markdown 实时预览（离线 KaTeX，零下载）。

用法:
    python3 md_preview.py <file.md>

原理:
    pandoc 把 markdown 转成带 KaTeX 的独立 HTML，本地 HTTP 伺服，
    页面轮询 /__mtime，文件一改就自动刷新。
"""
import glob
import mimetypes
import os
import subprocess
import sys
import threading
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MD = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ""

KATEX_CANDIDATES = [
    os.path.expanduser("~/.config/zed/vendor/katex"),
    os.path.expanduser(
        "~/.local/share/nvim/mason/packages/markdownlint-cli2/"
        "node_modules/markdownlint-cli2/node_modules/katex/dist"
    ),
]

MIME_EXTRA = {
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
}

AUTORELOAD = """<script>
(function () {
  var last = null;
  setInterval(function () {
    fetch('/__mtime', { cache: 'no-store' })
      .then(function (r) { return r.text(); })
      .then(function (t) {
        if (last !== null && last !== t) { location.reload(); }
        last = t;
      })
      .catch(function () {});
  }, 400);
})();
</script>
"""


def find_katex():
    for base in KATEX_CANDIDATES:
        if os.path.isfile(os.path.join(base, "katex.min.js")):
            return base
    for pattern in (
        "~/.config/zed/vendor/katex/katex.min.js",
        "~/.local/share/nvim/**/katex/dist/katex.min.js",
    ):
        hits = glob.glob(os.path.expanduser(pattern), recursive=True)
        if hits:
            return os.path.dirname(hits[0])
    return None


KATEX_DIR = find_katex()
PORT = 8700 + (zlib.crc32(MD.encode()) % 300)

_cache = {"mtime": None, "html": None}


def build_html():
    try:
        mtime = os.path.getmtime(MD)
    except OSError:
        return "<html><body><pre>File not found: %s</pre></body></html>" % MD, 0.0

    if _cache["mtime"] == mtime and _cache["html"]:
        return _cache["html"], mtime

    cmd = [
        "pandoc",
        "-f", "markdown+tex_math_dollars+tex_math_single_backslash"
              "+pipe_tables+footnotes+task_lists",
        "-t", "html",
        "-s",
        "--katex=/katex/",
        "--highlight-style=tango",
        "--metadata", "title=%s" % os.path.basename(MD),
        MD,
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        html = res.stdout or "<pre>%s</pre>" % (res.stderr or "pandoc failed")
    except FileNotFoundError:
        html = "<pre>pandoc not found</pre>"

    html = (html.replace("</head>", AUTORELOAD + "</head>", 1)
            if "</head>" in html else AUTORELOAD + html)

    _cache["mtime"], _cache["html"] = mtime, html
    return html, mtime


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, root, rel):
        if not root:
            return self._send(404, "not found", "text/plain")
        root = os.path.abspath(root)
        full = os.path.abspath(os.path.join(root, rel))
        if not full.startswith(root + os.sep) or not os.path.isfile(full):
            return self._send(404, "not found", "text/plain")
        ext = os.path.splitext(full)[1].lower()
        ctype = MIME_EXTRA.get(ext) or mimetypes.guess_type(full)[0] \
            or "application/octet-stream"
        with open(full, "rb") as f:
            self._send(200, f.read(), ctype)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            html, _ = build_html()
            return self._send(200, html)
        if path == "/__mtime":
            try:
                return self._send(200, str(os.path.getmtime(MD)), "text/plain")
            except OSError:
                return self._send(200, "0", "text/plain")
        if path.startswith("/katex/"):
            return self._serve_file(KATEX_DIR, path[len("/katex/"):])
        return self._serve_file(os.path.dirname(MD), path.lstrip("/"))

    def log_message(self, *args):
        pass


def open_browser(url):
    """拉起系统浏览器，彻底分离，不占用 stdout/stderr 管道。"""
    for cmd in (["xdg-open", url], ["gio", "open", url], ["open", url]):
        try:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
            return
        except FileNotFoundError:
            continue


def main():
    if not MD or not os.path.isfile(MD):
        print("usage: md_preview.py <file.md>", file=sys.stderr)
        sys.exit(1)
    if MD.lower().rsplit(".", 1)[-1] not in ("md", "markdown", "mdown", "mkd"):
        print("not a markdown file: %s" % MD, file=sys.stderr)
        sys.exit(1)
    if not KATEX_DIR:
        print("katex dist not found, aborting", file=sys.stderr)
        sys.exit(1)

    url = "http://127.0.0.1:%d/" % PORT
    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        open_browser(url)
        return

    threading.Thread(
        target=lambda: (time.sleep(0.5), open_browser(url)), daemon=True
    ).start()
    print("markdown preview: %s -> %s" % (MD, url), flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
