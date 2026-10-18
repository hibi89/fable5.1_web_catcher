"""Local fake web service for offline tests: NOT a real public website."""
from __future__ import annotations

import base64
import hashlib
import json
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread


class FixtureHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        # Prevent logging query credentials even in the fixture process.
        return

    def _dynamic_response(self, body: bytes, mime: str, *, declared: bool = True):
        self.send_response(200)
        self.send_header("Content-Type", mime)
        if declared:
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _websocket_fixture(self):
        key = self.headers.get("Sec-WebSocket-Key", "")
        if not key:
            self.send_error(400)
            return
        accept = base64.b64encode(hashlib.sha1(
            (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()
        ).digest()).decode()
        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        try:
            for message in (b"FRAME_ONE_PRIVATE", b"FRAME_TWO_PRIVATE"):
                self.wfile.write(bytes((0x81, len(message))) + message)
                self.wfile.flush()
                time.sleep(0.08)
            # No frame inspection. Browser closes socket with isolated context.
            time.sleep(0.35)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            self.close_connection = True

    def _sse_fixture(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            self.wfile.write(b"data: SSE_CONTENT_PRIVATE\n\n")
            self.wfile.flush()
            # Stream deliberately remains open beyond the scan wait.
            time.sleep(2.0)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            self.close_connection = True

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path == "/graphql":
            # Deliberately ignore the request body; tests verify it is never persisted.
            body = json.dumps({"data": {"status": "GRAPHQL_DATA_PRIVATE"}}, separators=(",", ":")).encode()
            self._dynamic_response(body, "application/json; charset=utf-8")
            return
        self.send_error(404)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/ws":
            self._websocket_fixture()
            return
        if path == "/stream":
            self._sse_fixture()
            return
        if path == "/final-bundle.js":
            # This is deliberately a *loaded* script, not a site probe.
            code = (b'const hint="/api/unused?api_key=JS_LITERAL_PRIVATE";'
                    b'const observed="/api/chart";')
            self._dynamic_response(code, "application/javascript")
            return
        if path == "/runtime-final":
            page = """<!doctype html><html><body>
            <svg class="highcharts-root" width="300" height="100"></svg>
            <canvas width="80" height="40"></canvas>
            <script src="/final-bundle.js?token=SCRIPT_SRC_PRIVATE"></script>
            <script>
              setTimeout(() => {
                const w = new WebSocket('ws://127.0.0.1:__PORT__/ws?token=WS_URI_PRIVATE');
                w.addEventListener('open', () => w.send('WS_PAYLOAD_PRIVATE'));
                const stream = new EventSource('/stream?api_key=SSE_URI_PRIVATE');
                stream.addEventListener('message', () => {});
                Promise.all([
                  fetch('/api/chart?access_token=CHART_URI_PRIVATE'),
                  fetch('/api/noise?token=NOISE_URI_PRIVATE')
                ]).then(() => document.querySelector('svg')
                   .setAttribute('viewBox', '0 0 300 100'));
              }, 80);
            </script></body></html>""".replace("__PORT__", str(self.server.server_port))
            self._dynamic_response(page.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/runtime-css-bars":
            # CSS-only percent-height bars with no chart library, plus a
            # decorative tiny SVG. The hash must select the dashboard view.
            page = """<!doctype html><html><body>
            <svg width="18" height="18" viewBox="0 0 18 18">
              <path d="M1 1 L17 17"/><rect width="4" height="4"/>
            </svg>
            <script>
              if (location.hash === '#v-dash') {
                const bars=document.createElement('div');
                bars.className='bars';
                bars.style.cssText='display:flex;align-items:flex-end;width:440px;height:130px';
                for (const pct of [25,45,55,35,73,52,91,60]) {
                  const bar=document.createElement('div');
                  bar.className='bar';
                  bar.setAttribute('style','width:16px;height:'+pct+'%');
                  bars.appendChild(bar);
                }
                document.body.appendChild(bars);
              }
            </script></body></html>"""
            self._dynamic_response(page.encode(), "text/html; charset=utf-8")
            return
        if path == "/runtime-charts":
            # Explicit test-only library stubs, not real third-party distributions.
            page = """<!doctype html><html><body>
            <canvas id="generic" width="200" height="100"></canvas>
            <svg id="plain-svg" width="20" height="20"></svg>
            <script id="__NEXT_DATA__" type="application/json">{}</script>
            <script>
              window.Chart = function TestChart(){};
              window.Chart.version = "4.4.1";
              window.Chart.instances = { one: {} };
              window.Highcharts = {version:"11.3.0",charts:[{}]};
              window.d3 = {version:"7.9.0"};
              setTimeout(() => {
                const svg = document.createElementNS("http://www.w3.org/2000/svg","svg");
                svg.setAttribute("width","300");
                svg.setAttribute("height","160");
                document.body.appendChild(svg);
                setTimeout(() => {
                  svg.setAttribute("class", "highcharts-root");
                  svg.setAttribute("viewBox", "0 0 300 160");
                }, 70);
                const div = document.createElement("div");
                div.setAttribute("_echarts_instance_", "PRIVATE_INSTANCE_VALUE");
                const canvas = document.createElement("canvas");
                div.appendChild(canvas);
                document.body.appendChild(div);
              }, 40);
            </script></body></html>"""
            self._dynamic_response(page.encode(), "text/html; charset=utf-8")
            return
        if path == "/runtime-connections":
            page = """<!doctype html><html><body><script>
            setTimeout(() => {
              const socket = new WebSocket('ws://127.0.0.1:__PORT__/ws?access_token=WS_URL_PRIVATE');
              socket.addEventListener('open', () => socket.send('WS_SENT_PRIVATE'));
              const events = new EventSource('/stream?api_key=SSE_URL_PRIVATE');
              events.addEventListener('message', () => {});
            }, 30);
            </script></body></html>""".replace("__PORT__", str(self.server.server_port))
            self._dynamic_response(page.encode(), "text/html; charset=utf-8")
            return
        if path == "/runtime-network":
            page = """<!doctype html><html><body><div>API test fixture</div><script>
            setTimeout(() => {
              fetch('/api/chart?access_token=CHART_URL_PRIVATE');
              fetch('/api/noise?token=NOISE_URL_PRIVATE');
              fetch('/api/plain');
              fetch('/api/badjson');
              fetch('/api/large');
              fetch('/api/unknown');
              fetch('/graphql?api_key=GRAPHQL_URL_PRIVATE', {
                method:'POST', headers:{'content-type':'application/json'},
                body:JSON.stringify({query:'query { value }',variables:{token:'POST_BODY_PRIVATE'}})
              });
            }, 30);
            </script></body></html>"""
            self._dynamic_response(page.encode(), "text/html; charset=utf-8")
            return
        if path.startswith("/api/"):
            if path == "/api/chart":
                time.sleep(0.06)
                obj = {"data": [{"date": "DATE_VALUE_PRIVATE", "value": 312,
                                 "password": "PASSWORD_VALUE_PRIVATE"}],
                       "api_key": "KEY_VALUE_PRIVATE"}
                self._dynamic_response(json.dumps(obj).encode(), "application/json")
            elif path == "/api/noise":
                time.sleep(0.065)
                self._dynamic_response(b'{"logs":[{"message":"NOISE_VALUE_PRIVATE"}]}', "application/json")
            elif path == "/api/plain":
                self._dynamic_response(b"PLAIN_PRIVATE", "text/plain")
            elif path == "/api/badjson":
                self._dynamic_response(b"not valid json PRIVATE_BAD", "application/json")
            elif path == "/api/large":
                self._dynamic_response(b'{"data":"' + b"x" * 131100 + b'"}', "application/json")
            elif path == "/api/unknown":
                self._dynamic_response(b'{"value":"UNKNOWN_SIZE_PRIVATE"}', "application/json", declared=False)
            else:
                self.send_error(404)
            return
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
