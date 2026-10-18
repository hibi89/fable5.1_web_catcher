"""WebSocket/SSE passive collector unit tests (no browser needed)."""
from __future__ import annotations

import json

from scanner.connections import ConnectionCollector, MAX_CONNECTIONS, MAX_COUNT
from scanner.models import blank_result


class EventEmitter:
    def __init__(self):
        self.events = {}

    def on(self, kind, callback):
        self.events.setdefault(kind, []).append(callback)

    def emit(self, kind, value=None):
        for callback in self.events.get(kind, []):
            callback(value)


class WebSocket(EventEmitter):
    def __init__(self, url):
        super().__init__()
        self.url = url


class Response:
    def __init__(self, url, mime, status=200):
        self.url = url
        self.headers = {"content-type": mime}
        self.status = status


def test_websocket_counts_only_no_frame_content_or_token():
    data = blank_result("https://example.test")
    collector = ConnectionCollector(data)
    page = EventEmitter()
    collector.attach(page)
    socket = WebSocket("wss://example.test/socket?token=SOCKET_QUERY_PRIVATE")
    page.emit("websocket", socket)
    socket.emit("framesent", "WS_SENT_FRAME_PRIVATE")
    socket.emit("framereceived", b"WS_RECEIVED_FRAME_PRIVATE")
    socket.emit("framereceived", b"WS_RECEIVED_FRAME_PRIVATE2")
    socket.emit("socketerror", "SOCKET_ERROR_PRIVATE")
    socket.emit("close")
    collector.finalize()
    row = data["api"]["connections"][0]
    assert row["kind"] == "websocket"
    assert row["frames_sent"] == 1 and row["frames_received"] == 2
    assert row["closed_at_ms"] >= row["observed_at_ms"]
    assert row["socket_error_observed"] is True
    saved = json.dumps(data, ensure_ascii=False)
    for token in ("SOCKET_QUERY_PRIVATE", "WS_SENT_FRAME_PRIVATE", "WS_RECEIVED_FRAME_PRIVATE",
                  "SOCKET_ERROR_PRIVATE"):
        assert token not in saved


def test_sse_header_only_and_no_body_access():
    data = blank_result("https://example.test")
    collector = ConnectionCollector(data)
    page = EventEmitter()
    collector.attach(page)
    response = Response("https://example.test/stream?api_key=SSE_URL_PRIVATE",
                        "text/event-stream; charset=utf-8")
    page.emit("response", response)
    row = data["api"]["connections"][0]
    assert row["kind"] == "sse"
    assert row["status"] == 200
    assert row["content_type"] == "text/event-stream"
    assert row["frames_sent"] is None
    assert "SSE_URL_PRIVATE" not in json.dumps(data)
    page.emit("response", Response("https://example.test/normal", "text/html"))
    assert len(data["api"]["connections"]) == 1


def test_connection_limit_is_bounded():
    data = blank_result("https://example.test")
    collector = ConnectionCollector(data)
    for n in range(MAX_CONNECTIONS + 4):
        collector.on_websocket(WebSocket(f"wss://example.test/ws/{n}"))
    collector.finalize()
    assert len(data["api"]["connections"]) == MAX_CONNECTIONS
    assert any("상한" in w for w in data["warnings"])


def test_frame_counter_saturates():
    collector = ConnectionCollector(blank_result("https://example.test"))
    socket = WebSocket("wss://example.test/socket")
    collector.on_websocket(socket)
    row = collector.records[0]
    row["frames_received"] = MAX_COUNT
    socket.emit("framereceived", "FRAME_DO_NOT_PERSIST")
    assert row["frames_received"] == MAX_COUNT
