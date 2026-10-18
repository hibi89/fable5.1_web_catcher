"""Real Chromium chart/API association fixture; no external network calls."""
from __future__ import annotations

import json
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlsplit

from scan import scan


class ChartMappingHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def _reply(self, text: str, mime: str):
        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ("/chart", "/chart-multiple"):
            multiple = "true" if path == "/chart-multiple" else "false"
            page = """<!doctype html><html><body>
            <canvas width="10" height="10"></canvas>
            <svg class="highcharts-root" width="200" height="100"></svg>
            <script>
              setTimeout(() => {
                const chart = document.querySelector('svg');
                const tasks = [
                  fetch('/data?token=CHART_QUERY_PRIVATE'),
                  fetch('/noise?token=NOISE_QUERY_PRIVATE')
                ];
                if (__MULTIPLE__)
                  tasks.push(fetch('/other?api_key=OTHER_QUERY_PRIVATE'));
                Promise.all(tasks).then(() => {
                  chart.setAttribute('viewBox', '0 0 200 100');
                });
              }, 40);
            </script></body></html>""".replace("__MULTIPLE__", multiple)
            self._reply(page, "text/html; charset=utf-8")
            return
        if path in ("/data", "/other"):
            time.sleep(0.06)
            self._reply(json.dumps({"data": [{"date": "DATA_VALUE_PRIVATE", "value": 9}]}),
                        "application/json")
            return
        if path == "/noise":
            time.sleep(0.07)
            self._reply(json.dumps({"logs": [{"message": "NOISE_VALUE_PRIVATE"}]}),
                        "application/json")
            return
        self.send_error(404)


@contextmanager
def mapping_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), ChartMappingHandler)
    runner = Thread(target=server.serve_forever, daemon=True)
    runner.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port)
    finally:
        server.shutdown()
        runner.join(timeout=3)
        server.server_close()


def test_chart_mapping_unique_numeric_api_not_nearby_text_noise(tmp_path):
    with mapping_server() as base:
        result = scan(base + "/chart?token=PAGE_QUERY_PRIVATE",
                      tmp_path, timeout=12, wait=1.0, runtime=True)
    data = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert result == 0, data["warnings"]
    lookup = {r["id"]: urlsplit(r["url"]).path for r in data["api"]["endpoints"]}
    assert "/data" in lookup.values() and "/noise" in lookup.values()
    links = data["api"]["chart_candidates"]
    assert len(links) == 1, (links, data["charts"], data["api"]["endpoints"])
    link = links[0]
    assert lookup[link["endpoint_id"]] == "/data"
    assert link["status"] == "candidate_only"
    assert 0.55 <= link["confidence"] <= 0.65
    marked = next(c for c in data["charts"] if c["id"] == link["chart_id"])
    assert marked["library"] == "Highcharts"
    assert marked["data_sources"] == [link["endpoint_id"]]
    assert all(not c["data_sources"] for c in data["charts"] if c["library"] == "unknown")
    assert data["runtime"]["mapping_analysis"]["repeated_consistency_checked"] is False
    assert "차트↔API 연관 후보" in (tmp_path / "report.md").read_text(encoding="utf-8")
    output = (tmp_path / "result.json").read_text(encoding="utf-8")
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    for secret in ("PAGE_QUERY_PRIVATE", "CHART_QUERY_PRIVATE",
                   "NOISE_QUERY_PRIVATE", "DATA_VALUE_PRIVATE", "NOISE_VALUE_PRIVATE"):
        assert secret not in output + report


def test_chart_mapping_competing_timeseries_apis_abstains(tmp_path):
    with mapping_server() as base:
        code = scan(base + "/chart-multiple", tmp_path, timeout=12,
                    wait=1.0, runtime=True)
    data = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert code == 0, data["warnings"]
    assert data["api"]["chart_candidates"] == []
    assert data["runtime"]["mapping_analysis"]["ambiguous_charts_unlinked"] >= 1
    assert all(c["data_sources"] == [] for c in data["charts"])
