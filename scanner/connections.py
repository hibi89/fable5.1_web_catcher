"""Read-only WebSocket and SSE connection metadata collection.

Raw WebSocket frames and SSE response bodies are never read or persisted.
Callbacks ignore any payload provided by Playwright.
"""
from __future__ import annotations

import time
from urllib.parse import urlsplit

from .network import _mime
from .sanitize import safe_url

MAX_CONNECTIONS = 60
MAX_COUNT = 1_000_000


def _clock_ms() -> int:
    return int(time.time() * 1000)


class ConnectionCollector:
    def __init__(self, result: dict):
        self.records = result["api"]["connections"]
        self.warnings = result["warnings"]
        self.over_limit = False

    def attach(self, page) -> None:
        page.on("websocket", self.on_websocket)
        page.on("response", self.on_response)

    def _append(self, kind: str, url: str, **fields):
        if len(self.records) >= MAX_CONNECTIONS:
            self.over_limit = True
            return None
        row = {
            "id": f"conn-{len(self.records)+1:04d}",
            "kind": kind,
            "url": safe_url(url),
            "observed_at_ms": _clock_ms(),
        }
        row.update(fields)
        self.records.append(row)
        return row

    @staticmethod
    def _count(row, name):
        if row[name] < MAX_COUNT:
            row[name] += 1

    def on_websocket(self, websocket) -> None:
        url = websocket.url
        if urlsplit(url).scheme not in ("ws", "wss"):
            return
        row = self._append(
            "websocket", url,
            frames_sent=0, frames_received=0,
            closed_at_ms=None, socket_error_observed=False,
        )
        if row is None:
            return
        # The raw frame/error objects are intentionally not inspected.
        websocket.on("framesent", lambda _frame: self._count(row, "frames_sent"))
        websocket.on("framereceived", lambda _frame: self._count(row, "frames_received"))
        websocket.on("close", lambda *_ignored: row.__setitem__("closed_at_ms", _clock_ms()))
        websocket.on("socketerror", lambda *_ignored: row.__setitem__("socket_error_observed", True))

    def on_response(self, response) -> None:
        # SSE headers arrive before the stream ends: never access its body.
        if _mime(response.headers) != "text/event-stream":
            return
        url = response.url
        if urlsplit(url).scheme not in ("http", "https"):
            return
        self._append(
            "sse", url,
            status=response.status,
            content_type="text/event-stream",
            frames_sent=None,
            frames_received=None,
        )

    def finalize(self) -> None:
        if self.over_limit:
            self.warnings.append(f"WebSocket/SSE 연결 수집 상한 {MAX_CONNECTIONS}건 적용")
