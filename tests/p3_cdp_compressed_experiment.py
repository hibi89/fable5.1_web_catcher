"""One-off CDP experiment, local fixture only. Must never merge into main.

Compares Chrome Network.streamResourceContent for chunked gzip JSON without
Content-Length against a severely compressed oversized payload. No real
website visited. Only boolean/size summaries printed, never response values.
"""
from __future__ import annotations
import base64
import gzip
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

CAP = 131_072


class LocalFixture(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            data = b"<html><body>Fixture</body></html>"
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path not in ("/small", "/large"):
            self.send_error(404)
            return
        if path == "/small":
            payload = {"items": [{"date": "PRIVATE_DATE", "value": i}
                                 for i in range(30)]}
        else:
            payload = {"items": ["X" * 400_000]}
        encoded = gzip.compress(json.dumps(payload).encode("utf-8"))
        self.protocol_version = "HTTP/1.1"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Encoding", "gzip")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        for start in range(0, len(encoded), 256):
            chunk = encoded[start:start + 256]
            self.wfile.write(("%X\r\n" % len(chunk)).encode() + chunk + b"\r\n")
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), LocalFixture)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = "http://127.0.0.1:" + str(server.server_port)
    states = {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context()
            page = ctx.new_page()
            session = ctx.new_cdp_session(page)
            session.send("Network.enable")

            def append(identifier, text):
                state = states.get(identifier)
                if state is None or state["over"] or not text:
                    return
                # Reject oversized base64 *before decoding and allocation*.
                left = CAP - len(state["received"])
                if len(text) > (left * 4 // 3 + 8):
                    state["over"] = True
                    return
                try:
                    chunk = base64.b64decode(text, validate=True)
                except Exception:
                    state["invalid"] = True
                    return
                if len(chunk) > left:
                    state["over"] = True
                    return
                state["received"].extend(chunk)
                state["chunks"] += 1

            def on_request(event):
                request_url = event.get("request", {}).get("url", "")
                if request_url in (url + "/small", url + "/large"):
                    states[event["requestId"]] = {
                        "path": request_url.rsplit("/", 1)[-1],
                        "received": bytearray(), "over": False,
                        "invalid": False, "enabled": False, "error": None,
                        "finished": False, "chunks": 0, "data_events": 0,
                    }

            def on_response(event):
                ident = event["requestId"]
                state = states.get(ident)
                if state is None:
                    return
                try:
                    answer = session.send(
                        "Network.streamResourceContent", {"requestId": ident})
                    state["enabled"] = True
                    append(ident, answer.get("bufferedData"))
                except Exception as exc:
                    state["error"] = type(exc).__name__

            def on_data(event):
                ident = event["requestId"]
                if ident in states:
                    states[ident]["data_events"] += 1
                    append(ident, event.get("data", ""))

            def on_finished(event):
                state = states.get(event["requestId"])
                if state:
                    state["finished"] = True

            session.on("Network.requestWillBeSent", on_request)
            session.on("Network.responseReceived", on_response)
            session.on("Network.dataReceived", on_data)
            session.on("Network.loadingFinished", on_finished)
            page.goto(url + "/", wait_until="domcontentloaded")
            for path in ("small", "large"):
                page.evaluate("u => fetch(u).then(r => r.json()).then(x => x.items.length)",
                              url + "/" + path)
                page.wait_for_timeout(250)
            rows = {}
            for s in states.values():
                data = bytes(s["received"])
                valid = False
                if not s["over"] and data.startswith(b"{"):
                    try:
                        parsed = json.loads(data)
                        valid = isinstance(parsed.get("items"), list)
                    except (ValueError, UnicodeError):
                        pass
                rows[s["path"]] = {
                    "enabled": s["enabled"], "error": s["error"],
                    "received_bytes": len(data), "chunks": s["chunks"],
                    "data_events": s["data_events"], "over": s["over"],
                    "finished": s["finished"], "invalid": s["invalid"],
                    "starts_json": data.startswith(b"{"), "valid_shape": valid,
                }
            print("CDP_GZIP_STREAM_FIXTURE " + json.dumps(rows, sort_keys=True), flush=True)
            browser.close()
        assert set(rows) == {"small", "large"}, "Did not observe both fixtures"
        assert rows["small"]["enabled"] and rows["small"]["finished"]
        assert rows["small"]["valid_shape"], "CDP did not stream decoded JSON"
        assert rows["large"]["over"], "Overcompressed response not truncated"
        assert rows["large"]["received_bytes"] <= CAP
        print("CDP_GZIP_STREAM_PROTOTYPE_PASS", flush=True)
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


if __name__ == "__main__":
    main()
