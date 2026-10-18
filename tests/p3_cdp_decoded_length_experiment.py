"""One-off alternative CDP experiment. Only localhost fixture, no real URLs.

Measure Network.dataReceived.dataLength before any response.body() call. The
encodedDataLength is not sufficient for compressed JSON; a compressed bomb
with tiny wire bytes must be rejected by decoded length. Do not merge.
"""
from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from tests.p3_cdp_compressed_experiment import LocalFixture, CAP


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), LocalFixture)
    worker = threading.Thread(target=srv.serve_forever, daemon=True)
    worker.start()
    base = "http://127.0.0.1:" + str(srv.server_port)
    states = {}
    response_for_url = {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            session = context.new_cdp_session(page)
            session.send("Network.enable")
            paths = {base + "/small": "small", base + "/large": "large"}

            def requested(event):
                path = paths.get(event.get("request", {}).get("url"))
                if path:
                    states[event["requestId"]] = {
                        "path": path, "decoded": 0, "encoded": 0,
                        "events": 0, "finished": False, "oversize": False,
                    }

            def received_data(event):
                state = states.get(event["requestId"])
                if not state:
                    return
                decoded = event.get("dataLength")
                encoded = event.get("encodedDataLength")
                if type(decoded) is not int or decoded < 0:
                    state["invalid"] = True
                    return
                state["decoded"] += decoded
                if type(encoded) is int:
                    state["encoded"] += encoded
                state["events"] += 1
                if state["decoded"] > CAP:
                    state["oversize"] = True

            def finished(event):
                state = states.get(event["requestId"])
                if state:
                    state["finished"] = True

            def observed_response(response):
                if response.url in paths:
                    response_for_url[response.url] = response

            session.on("Network.requestWillBeSent", requested)
            session.on("Network.dataReceived", received_data)
            session.on("Network.loadingFinished", finished)
            page.on("response", observed_response)
            page.goto(base + "/", wait_until="domcontentloaded")
            for path in ("small", "large"):
                page.evaluate(
                    "u => fetch(u).then(r => r.json()).then(x => x.items.length)",
                    base + "/" + path)
                page.wait_for_timeout(250)

            results = {}
            for state in states.values():
                path = state["path"]
                safe = (state["finished"] and state["events"] > 0
                        and not state.get("invalid")
                        and not state["oversize"] and state["decoded"] <= CAP)
                body_read = False
                valid_json = False
                if safe:
                    response = response_for_url.get(base + "/" + path)
                    if response is not None:
                        # Bounded by observed decoded-byte count; double-check.
                        body = response.body()
                        body_read = True
                        if len(body) <= CAP:
                            obj = json.loads(body)
                            valid_json = isinstance(obj.get("items"), list)
                results[path] = {
                    **state, "body_read": body_read, "valid_json": valid_json,
                }

            print("CDP_DECODED_LENGTH_FIXTURE " + json.dumps(results, sort_keys=True), flush=True)
            browser.close()
        assert set(results) == {"small", "large"}
        assert results["small"]["finished"] and results["small"]["events"] > 0
        assert results["small"]["valid_json"]
        assert results["large"]["oversize"] and not results["large"]["body_read"]
        assert results["large"]["decoded"] > CAP
        print("CDP_DECODED_LENGTH_PASS", flush=True)
    finally:
        srv.shutdown()
        srv.server_close()
        worker.join(timeout=2)


if __name__ == "__main__":
    main()
