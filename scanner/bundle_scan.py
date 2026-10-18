"""Passive, bounded analysis of already-loaded same-origin JavaScript responses.

Does not request URLs. No raw scripts, response values or tokenized snippets
are persisted. Quoted routes are unverified, not observed API requests.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

from .network import _length, _mime
from .sanitize import SECRET_KEYS, safe_url

MAX_SCRIPTS = 10
MAX_BYTES = 131072
MAX_CANDIDATES = 30
MIMES = {"application/javascript", "text/javascript", "application/x-javascript"}
ROUTE = re.compile(r"^/(?:api(?:/[A-Za-z0-9_-]{1,48}){1,5}|graphql|gql)/?$")
QUOTED = re.compile(r"""(["'])([^"'\\\r\n]{1,300})\1""")


def _origin(url: str):
    try:
        p = urlsplit(url)
        if p.scheme.lower() not in {"http", "https"} or not p.hostname:
            return None
        return p.scheme.lower(), p.hostname.lower(), (p.port or (443 if p.scheme == "https" else 80))
    except (TypeError, ValueError):
        return None


def _route(value: str, origin):
    if value.startswith("/"):
        path = value.split("?", 1)[0].split("#", 1)[0]
    else:
        if _origin(value) != origin:
            return None
        path = urlsplit(value).path
    if not ROUTE.fullmatch(path):
        return None
    if any(SECRET_KEYS.search(segment) for segment in path.split("/")[1:]):
        return None
    return path


def _extract(code: str, origin):
    found = []
    for match in QUOTED.finditer(code):
        path = _route(match.group(2), origin)
        if path and path not in found:
            found.append(path)
            if len(found) >= 15:
                break
    return found


class BundleCollector:
    def __init__(self, result):
        self.result = result
        self.responses = {}
        self.finished = set()
        self.limited = False

    def attach(self, page):
        page.on("response", self.on_response)
        page.on("requestfinished", self.on_finished)
        page.on("requestfailed", self.on_failed)

    def on_response(self, response):
        request = response.request
        if request.resource_type != "script":
            return
        if len(self.responses) >= MAX_SCRIPTS:
            self.limited = True
            return
        if response.status != 200 or _mime(response.headers) not in MIMES:
            return
        size = _length(response.headers)
        if size is None or not 0 < size <= MAX_BYTES:
            return
        self.responses[request] = response

    def on_finished(self, request):
        if request in self.responses:
            self.finished.add(request)

    def on_failed(self, request):
        self.responses.pop(request, None)
        self.finished.discard(request)

    def finalize(self, page_url):
        result = self.result
        result["api"]["candidates"] = []
        meta = {"mode": "observed_script_responses_only", "scanned_scripts": 0,
                "candidate_count": 0, "skipped_cross_origin": 0,
                "skipped_incomplete": 0, "skipped_oversize_decoded": 0,
                "limited": self.limited}
        try:
            origin = _origin(page_url)
            if origin is None:
                return
            observed = {urlsplit(r.get("url", "")).path
                        for r in result["api"]["endpoints"]}
            seen = set()
            for request, response in list(self.responses.items()):
                if _origin(request.url) != origin or _origin(response.url) != origin:
                    meta["skipped_cross_origin"] += 1
                    continue
                if request not in self.finished:
                    meta["skipped_incomplete"] += 1
                    continue
                try:
                    body = response.body()
                    if len(body) > MAX_BYTES:
                        meta["skipped_oversize_decoded"] += 1
                        continue
                    code = body.decode("utf-8", errors="replace")
                except Exception:
                    continue
                meta["scanned_scripts"] += 1
                source = "script-%03d" % meta["scanned_scripts"]
                for path in _extract(code, origin):
                    if path in seen or path in observed:
                        continue
                    if len(result["api"]["candidates"]) >= MAX_CANDIDATES:
                        meta["limited"] = True
                        break
                    seen.add(path)
                    result["api"]["candidates"].append({
                        "path": path, "source_script_id": source,
                        "source_script": safe_url(response.url),
                        "discovered_by": "bundle_string",
                        "status": "unverified_string_literal",
                        "confidence": 0.2, "observed_request": False,
                        "evidence": "quoted_literal_in_loaded_same_origin_javascript",
                    })
            meta["candidate_count"] = len(result["api"]["candidates"])
        finally:
            self.responses.clear()
            self.finished.clear()
            result["runtime"]["bundle_scan"] = meta
            if meta["limited"]:
                result["warnings"].append("JS 번들 분석 상한: 일부 응답/후보 생략")
