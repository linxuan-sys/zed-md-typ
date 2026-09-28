#!/usr/bin/env python3
"""Zed 浏览器 HTML 实时预览（零依赖）。

用法:
    python3 html_preview.py <file.html>

原理:
    本地 HTTP 伺服 HTML 文件所在目录（相对引用的 css/js/图片都能加载），
    页面轮询 /__mtime，目录里任何文件一改就自动刷新。
"""
import mimetypes
import os
import subprocess
import sys
import threading
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HTML = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ""
ROOT = os.path.dirname(HTML) or "."

MIME_EXTRA = {
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".wasm": "application/wasm",
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

PORT = 8700 + (zlib.crc32(HTML.encode()) % 300)


def dir_stamp():
    """目录内所有文件 mtime 的最大值，作为刷新令牌。"""
    latest = 0.0
    try:
        for base, _dirs, files in os.walk(ROOT):
            if os.sep + "." in base:
                continue
            for name in files:
                try:
                    m = os.path.getmtime(os.path.join(base, name))
                    if m > latest:
                        latest = m
                except OSError:
                    pass
    except OSError:
        pass
    return latest


def build_html():
    try:
        with open(HTML, "r", encoding="utf-8", errors="replace") as f:
            html = f.read()
    except OSError:
        return "<html><body><pre>File not found: %s</pre></body></html>" % HTML

    if "</body>" in html:
        html = html.replace("</body>", AUTORELOAD + "</body>", 1)
    else:
        html += AUTORELOAD
    return html


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

    def _serve_file(self, rel):
        root = os.path.abspath(ROOT)
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
        if path in ("/", "/index.html", "/" + os.path.basename(HTML)):
            return self._send(200, build_html())
        if path == "/__mtime":
            return self._send(200, "%.6f" % dir_stamp(), "text/plain")
        return self._serve_file(path.lstrip("/"))

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
    if not HTML or not os.path.isfile(HTML):
        print("usage: html_preview.py <file.html>", file=sys.stderr)
        sys.exit(1)
    if HTML.lower().rsplit(".", 1)[-1] not in ("html", "htm"):
        print("not an html file: %s" % HTML, file=sys.stderr)
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
    print("html preview: %s -> %s" % (HTML, url), flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
