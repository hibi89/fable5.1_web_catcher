"""Local fake web service for offline tests: NOT a real public website."""
from __future__ import annotations

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread


class FixtureHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        # Prevent logging query credentials even in the fixture process.
        return

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/next?access_token=REDIRECT_PRIVATE&mode=test")
            self.end_headers()
            return
        if path == "/redirect-loop":
            self.send_response(302)
            self.send_header("Location", "/redirect-loop?access_token=LOOP_PRIVATE")
            self.end_headers()
            return
        if path == "/redirect-invalid":
            self.send_response(302)
            self.send_header("Location", "file:///etc/passwd?token=REDIRECT_SCHEME_PRIVATE")
            self.end_headers()
            return
        if path == "/blocked":
            body = b"<html><title>Access Denied</title></html>"
            self.send_response(403)
        elif path == "/rate":
            body = b"<html><title>Request blocked</title></html>"
            self.send_response(429)
        elif path == "/next":
            body = (b'<html><head><meta name="generator" content="Test Fixture">'
                    b'<script id="__NEXT_DATA__" type="application/json">{}</script>'
                    b'<script src="/_next/static/chunks/main.js?api_key=SCRIPT_PRIVATE"></script>'
                    b'<link rel="stylesheet" href="/assets/app.css?token=STYLE_PRIVATE">'
                    b'</head><body><div id="__next">next mock</div></body></html>')
            self.send_response(200)
            self.send_header("x-vercel-id", "test-vercel-id")
        elif path == "/servlet":
            body = b"<html><body>Servlet mock</body></html>"
            self.send_response(200)
            self.send_header("Set-Cookie", "JSESSIONID=SESSION_PRIVATE; HttpOnly; Path=/")
            self.send_header("Server", "Apache/2.4.58")
        elif path == "/plain":
            body = b"<html><body>React Vue Django Express Spring Boot Angular</body></html>"
            self.send_response(200)
        elif path == "/secret":
            body = (b'<html><head><script src="/safe.js?token=SCRIPT_PRIVATE"></script>'
                    b'<link rel="stylesheet" href="/file.css?api_key=STYLE_PRIVATE">'
                    b'</head><body>nothing</body></html>')
            self.send_response(200)
            self.send_header("Set-Cookie", "sessionid=COOKIE_PRIVATE; HttpOnly")
            self.send_header("Set-Cookie", "csrftoken=CSRF_PRIVATE; SameSite=Lax")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src https://cdn.example.net")
            self.send_header("X-Powered-By", "Express")
        elif path == "/huge":
            body = b"x" * 2000
            self.send_response(200)
        elif path == "/not-html":
            body = b'{"a":"b"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-Powered-By", "Express")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        else:
            body = b"<html><body>not found</body></html>"
            self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@contextmanager
def fixture_server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    worker = Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        worker.join(timeout=3)
        httpd.server_close()
