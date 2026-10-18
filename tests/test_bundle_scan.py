"""Step 2 bundle collection security and bounds without Chromium."""
from __future__ import annotations

import json

from scanner.bundle_scan import BundleCollector, _extract, _origin, _route
from scanner.models import blank_result


class Request:
    resource_type = "script"
    def __init__(self, url):
        self.url = url


class Response:
    status = 200
    def __init__(self, req, body, mime="text/javascript", declared=True):
        self.request = req
        self.url = req.url
        self.data = body
        self.calls = 0
        self.headers = {"content-type": mime}
        if declared:
            self.headers["content-length"] = str(len(body))

    def body(self):
        self.calls += 1
        return self.data


def result():
    r = blank_result("https://example.test")
    r["scan_mode"] = "runtime"
    r["runtime"] = {}
    return r


def test_only_literal_routes_without_queries_or_secret_segments():
    origin = _origin("https://example.test/a")
    assert _route("/api/nail/trends?token=PRIVATE", origin) == "/api/nail/trends"
    assert _route("https://example.test/api/v1/stats?password=PRIVATE", origin) == "/api/v1/stats"
    for value in ("https://different.test/api/v1/stats", "/api/auth/login",
                  "/api/v1/token", "/api/../private", "/users", "/api/a.b/c"):
        assert _route(value, origin) is None
    assert _extract('const a="/api/nail/trends?token=PRIVATE";', origin) == ["/api/nail/trends"]


def test_cross_origin_unfinished_and_secrets_are_not_persisted():
    r = result()
    c = BundleCollector(r)
    local = Request("https://example.test/main.js?token=URL_PRIVATE")
    remote = Request("https://cdn.test/remote.js")
    one = Response(local, b'const a="/api/trends?api_key=BODY_PRIVATE";')
    two = Response(remote, b'const b="/api/remote";')
    c.on_response(one)
    c.on_response(two)
    c.on_finished(local)
    c.on_finished(remote)
    c.finalize("https://example.test/index")
    assert one.calls == 1 and two.calls == 0
    candidates = r["api"]["candidates"]
    assert len(candidates) == 1
    assert candidates[0]["path"] == "/api/trends"
    assert candidates[0]["observed_request"] is False
    assert candidates[0]["discovered_by"] == "bundle_string"
    assert "URL_PRIVATE" not in candidates[0]["source_script"]
    saved = json.dumps(r)
    for secret in ("URL_PRIVATE", "BODY_PRIVATE", "/api/remote"):
        assert secret not in saved
    assert r["runtime"]["bundle_scan"]["skipped_cross_origin"] == 1


def test_unfinished_unknown_size_oversized_and_wrong_mime_not_read():
    for body, mime, declared, finished in [
        (b'const a="/api/a";', "text/javascript", True, False),
        (b'const a="/api/a";', "text/javascript", False, True),
        (b'const a="/api/a";', "text/html", True, True),
        (b"x" * 131073, "application/javascript", True, True)
    ]:
        r = result()
        c = BundleCollector(r)
        req = Request("https://example.test/app.js")
        response = Response(req, body, mime=mime, declared=declared)
        c.on_response(response)
        if finished:
            c.on_finished(req)
        c.finalize("https://example.test/")
        assert response.calls == 0
        assert r["api"]["candidates"] == []


def test_observed_api_is_excluded_and_repeat_paths_deduped():
    r = result()
    r["api"]["endpoints"] = [{"url": "https://example.test/api/observed?token=PRIVATE"}]
    c = BundleCollector(r)
    req = Request("https://example.test/assets/main.js")
    resp = Response(req, b'const a="/api/observed"; const b="/api/new"; const c="/api/new";')
    c.on_response(resp)
    c.on_finished(req)
    c.finalize("https://example.test/")
    assert [x["path"] for x in r["api"]["candidates"]] == ["/api/new"]
    assert r["api"]["endpoints"][0]["url"].endswith("PRIVATE")


def test_static_result_schema_unchanged():
    r = blank_result("https://example.test")
    assert set(r["api"]) == {"endpoints", "candidates", "connections"}


def test_at_most_ten_loaded_js_responses_and_limit_warning():
    from scanner.bundle_scan import MAX_SCRIPTS

    assert MAX_SCRIPTS == 10
    r = result()
    c = BundleCollector(r)
    for i in range(11):
        req = Request(f"https://example.test/assets/{i}.js")
        body = f'const hint="/api/candidate_{i}";'.encode()
        response = Response(req, body)
        c.on_response(response)
        c.on_finished(req)
    c.finalize("https://example.test/")
    assert r["runtime"]["bundle_scan"]["scanned_scripts"] == 10
    assert r["runtime"]["bundle_scan"]["limited"] is True
    assert len(r["api"]["candidates"]) == 10
    assert any("상한" in message for message in r["warnings"])
