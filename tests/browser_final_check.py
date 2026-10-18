"""Final Step 2 integrated acceptance on a local, actual Chromium page.

The fixture combines all six runtime units without secrets, accounts,
arbitrary endpoint probing, network proxies or external third-party services.
"""
from __future__ import annotations

import json
import time
from urllib.parse import urlsplit

from scan import scan
from tests.fixture_server import fixture_server


def _load(out):
    json_text = (out / "result.json").read_text(encoding="utf-8")
    report = (out / "report.md").read_text(encoding="utf-8")
    return json.loads(json_text), json_text + report, report


def test_full_runtime_one_page_all_six_mechanisms(tmp_path):
    with fixture_server() as base:
        code = scan(base + "/runtime-final?access_token=PAGE_FINAL_PRIVATE",
                    tmp_path, runtime=True, timeout=15, wait=1.3)
    data, saved, report = _load(tmp_path)
    assert code == 0, data["warnings"]
    assert data["scan_mode"] == "runtime"
    assert data["target"]["status_code"] == 200
    assert data["runtime"]["domcontentloaded_observed"] is True
    assert data["runtime"]["scroll_steps"] <= 2
    assert data["runtime"]["chart_observer"]["observer_initialized"] is True

    # Actual requests, not guessed bundle paths.
    observed = {urlsplit(row["url"]).path: row for row in data["api"]["endpoints"]}
    assert "/api/chart" in observed and "/api/noise" in observed
    assert observed["/api/chart"]["status"] == 200
    assert observed["/api/chart"]["json_structure"]["data"][0]["value"] == "number"

    # Explicit chart marker + response->DOM update, not a generic canvas.
    charts = data["charts"]
    marked = [item for item in charts if item["library"] == "Highcharts"]
    assert marked and marked[0]["last_observed_update_ms"] is not None
    assert not any(item["library"] == "unknown" and
                   item["detection_level"] == "generic_markup_candidate" for item in charts), charts
    hypotheses = data["api"]["chart_candidates"]
    assert len(hypotheses) == 1, (hypotheses, data["api"]["endpoints"])
    chosen = hypotheses[0]
    assert observed["/api/chart"]["id"] == chosen["endpoint_id"]
    assert chosen["status"] == "candidate_only"
    assert marked[0]["data_sources"] == [chosen["endpoint_id"]]
    assert all(not item["data_sources"] for item in charts if item["library"] == "unknown")

    # A WebSocket stream and an intentionally incomplete SSE remain bounded.
    connections = {item["kind"]: item for item in data["api"]["connections"]}
    assert set(connections) == {"websocket", "sse"}
    assert connections["websocket"]["frames_received"] >= 1
    assert connections["websocket"]["frames_sent"] >= 1
    assert connections["sse"]["content_type"] == "text/event-stream"

    # Only an already loaded same-origin JS string, never an API call.
    bundles = data["api"]["candidates"]
    assert [c["path"] for c in bundles] == ["/api/unused"]
    assert bundles[0]["observed_request"] is False
    assert bundles[0]["discovered_by"] == "bundle_string"
    assert bundles[0]["status"] == "unverified_string_literal"
    assert data["runtime"]["bundle_scan"]["scanned_scripts"] == 1

    # Evidence references remain internally consistent.
    evidence = {row["id"] for row in data["evidence"]}
    for group in ("frontend", "backend_inferred", "infra"):
        for item in data[group]:
            assert all(ref in evidence for ref in item["evidence_ids"])

    for secret in (
        "PAGE_FINAL_PRIVATE", "SCRIPT_SRC_PRIVATE", "JS_LITERAL_PRIVATE",
        "WS_URI_PRIVATE", "WS_PAYLOAD_PRIVATE", "SSE_URI_PRIVATE",
        "CHART_URI_PRIVATE", "NOISE_URI_PRIVATE", "DATE_VALUE_PRIVATE",
        "PASSWORD_VALUE_PRIVATE", "KEY_VALUE_PRIVATE", "NOISE_VALUE_PRIVATE",
        "FRAME_ONE_PRIVATE", "FRAME_TWO_PRIVATE", "SSE_CONTENT_PRIVATE",
    ):
        assert secret not in saved, secret
    assert "## 차트↔API 연관 후보" in report
    assert "## 로드된 JS 문자열 기반 미검증 API 후보" in report
    assert "아직 미구현" not in report


def test_runtime_http_404_keeps_partial_json_and_report(tmp_path):
    started = time.monotonic()
    with fixture_server() as base:
        code = scan(base + "/404-final?access_token=PAGE_404_PRIVATE",
                    tmp_path, runtime=True, timeout=8, wait=0.2)
    elapsed = time.monotonic() - started
    result, saved, _ = _load(tmp_path)
    assert code == 2
    assert elapsed < 8
    assert result["scan_mode"] == "runtime"
    assert result["target"]["status_code"] == 404
    assert any("HTTP 404" in message for message in result["warnings"])
    assert result["api"]["candidates"] == []
    assert "PAGE_404_PRIVATE" not in saved
