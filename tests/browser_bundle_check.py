"""Real Chromium fixture for passive same-origin JS bundle analysis."""
from __future__ import annotations

import json
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlsplit

from scan import scan


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def do_GET(self):
        path = urlsplit(self.path).path
        self.server.hits.append(path)
        if path == "/page":
            body = (b'<!doctype html><html><body>'
                    b'<script src="/app.js?token=BUNDLE_SRC_PRIVATE"></script>'
                    b'<script src="/huge.js"></script>'
                    b'</body></html>')
            mime = "text/html"
        elif path == "/app.js":
            body = (b'const a="/api/unused?api_key=BUNDLE_CONTENT_PRIVATE";'
                    b'const b="/api/unused";'
                    b'const c="/api/observed";'
                    b'const d="/api/auth/token";'
                    b'fetch("/api/observed?token=RUNTIME_API_PRIVATE");')
            mime = "text/javascript"
        elif path == "/huge.js":
            body = b'const a="/api/hidden";' + (b" " * 132000)
            mime = "text/javascript"
        elif path == "/api/observed":
            body = b'{"message":"OBSERVED_BODY_PRIVATE"}'
            mime = "application/json"
        elif path == "/empty":
            body = b"<html><body><script src='/plain.js'></script></body></html>"
            mime = "text/html"
        elif path == "/plain.js":
            body = b'const x=1;'
            mime = "application/javascript"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@contextmanager
def bundle_fixture():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.hits = []
    task = Thread(target=server.serve_forever, daemon=True)
    task.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port), server.hits
    finally:
        server.shutdown()
        task.join(timeout=3)
        server.server_close()


def test_real_chromium_loaded_js_candidates_are_not_observed_requests(tmp_path):
    with bundle_fixture() as (url, hits):
        code = scan(url + "/page?token=PAGE_PRIVATE", tmp_path,
                    runtime=True, wait=0.6, timeout=10)
    result = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert code == 0, result["warnings"]
    assert "/app.js" in hits and "/huge.js" in hits and "/api/observed" in hits
    assert "/api/unused" not in hits and "/api/hidden" not in hits
    endpoints = result["api"]["endpoints"]
    assert any("/api/observed" in row["url"] for row in endpoints)
    candidates = result["api"]["candidates"]
    assert [item["path"] for item in candidates] == ["/api/unused"]
    assert candidates[0]["observed_request"] is False
    assert candidates[0]["discovered_by"] == "bundle_string"
    assert "BUNDLE_SRC_PRIVATE" not in candidates[0]["source_script"]
    assert candidates[0]["status"] == "unverified_string_literal"
    assert result["runtime"]["bundle_scan"]["scanned_scripts"] == 1
    assert "미검증" in report
    output = (tmp_path / "result.json").read_text(encoding="utf-8") + report
    for value in ("BUNDLE_SRC_PRIVATE", "PAGE_PRIVATE", "BUNDLE_CONTENT_PRIVATE",
                  "RUNTIME_API_PRIVATE", "OBSERVED_BODY_PRIVATE", "/api/hidden"):
        assert value not in output


def test_real_chromium_no_api_literals_returns_empty(tmp_path):
    with bundle_fixture() as (url, hits):
        code = scan(url + "/empty", tmp_path, runtime=True, wait=0.1)
    result = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert code == 0, result["warnings"]
    assert result["api"]["candidates"] == []
    assert result["runtime"]["bundle_scan"]["scanned_scripts"] == 1
    assert "/plain.js" in hits
