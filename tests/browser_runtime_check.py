"""Explicit real Chromium integration check (not part of ordinary pytest collection)."""
from __future__ import annotations

import json

from scan import scan
from tests.fixture_server import fixture_server


def test_real_chromium_local_fixture(tmp_path):
    with fixture_server() as url:
        code = scan(url + '/next?access_token=RUNTIME_INPUT_PRIVATE', tmp_path,
                    timeout=15, runtime=True, wait=0.2)
    data = json.loads((tmp_path / 'result.json').read_text(encoding='utf-8'))
    rendered = (tmp_path / 'report.md').read_text(encoding='utf-8')
    assert code == 0, data['warnings']
    assert data['scan_mode'] == 'runtime'
    assert data['target']['status_code'] == 200
    assert data['runtime']['domcontentloaded_observed'] is True
    assert data['runtime']['scroll_steps'] <= 2
    assert data['api'] == {'endpoints': [], 'candidates': [], 'connections': [], 'chart_candidates': []}
    assert data['charts'] == []
    assert data['target']['scripts']
    assert 'RUNTIME_INPUT_PRIVATE' not in (tmp_path / 'result.json').read_text(encoding='utf-8') + rendered
    assert 'SCRIPT_PRIVATE' not in (tmp_path / 'result.json').read_text(encoding='utf-8') + rendered


def test_real_chromium_cli_flags_on_local_fixture(tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    out = tmp_path / 'cli'
    with fixture_server() as url:
        finished = subprocess.run(
            [sys.executable, str(root / 'scan.py'), url + '/plain',
             '--runtime', '--wait', '0.1', '--out', str(out)],
            cwd=root, capture_output=True, text=True, timeout=30,
        )
    assert finished.returncode == 0, finished.stdout + finished.stderr
    data = json.loads((out / 'result.json').read_text(encoding='utf-8'))
    assert data['scan_mode'] == 'runtime'
    assert data['target']['status_code'] == 200
    assert data['runtime']['domcontentloaded_observed'] is True


def test_real_chromium_observed_network_metadata(tmp_path):
    from urllib.parse import urlsplit

    with fixture_server() as url:
        code = scan(url + '/runtime-network?token=PAGE_URL_PRIVATE',
                    tmp_path, timeout=15, runtime=True, wait=1.5)
    data = json.loads((tmp_path / 'result.json').read_text(encoding='utf-8'))
    report = (tmp_path / 'report.md').read_text(encoding='utf-8')
    assert code == 0, data['warnings']
    assert data['scan_mode'] == 'runtime'
    assert data['runtime']['scope'] == 'network_and_connections_metadata'
    endpoints = data['api']['endpoints']
    assert len(endpoints) >= 7, endpoints
    rows = {urlsplit(item['url']).path: item for item in endpoints}
    for path in ('/api/chart', '/api/noise', '/api/plain', '/api/badjson',
                 '/api/large', '/api/unknown', '/graphql'):
        assert path in rows
        assert rows[path]['status'] == 200
        assert rows[path]['request_started_at_ms'] <= rows[path]['response_received_at_ms']
    assert rows['/api/chart']['json_structure'] == {
        'data': [{'date': 'string', 'value': 'number', '[REDACTED_KEY]': 'string'}],
        '[REDACTED_KEY]': 'string'}
    assert rows['/api/noise']['json_structure'] == {'logs': [{'message': 'string'}]}
    assert rows['/api/plain']['response_body_analysis'] == 'non_json'
    assert rows['/api/badjson']['response_body_analysis'] == 'invalid_json'
    assert rows['/api/large']['response_body_analysis'] == 'too_large'
    assert rows['/api/unknown']['response_body_analysis'] == 'size_unknown'
    assert rows['/graphql']['method'] == 'POST'
    assert rows['/graphql']['graphql_candidate'] is True
    assert data['api']['candidates'] == [] and data['api']['connections'] == []
    assert data['charts'] == []
    saved = (tmp_path / 'result.json').read_text(encoding='utf-8') + report
    for secret in ('PAGE_URL_PRIVATE', 'CHART_URL_PRIVATE', 'NOISE_URL_PRIVATE',
                   'GRAPHQL_URL_PRIVATE', 'POST_BODY_PRIVATE', 'DATE_VALUE_PRIVATE',
                   'PASSWORD_VALUE_PRIVATE', 'KEY_VALUE_PRIVATE', 'NOISE_VALUE_PRIVATE',
                   'UNKNOWN_SIZE_PRIVATE', 'GRAPHQL_DATA_PRIVATE'):
        assert secret not in saved


def test_real_chromium_websocket_and_unfinished_sse(tmp_path):
    """Observe only metadata; unfinished SSE must not delay runtime shutdown."""
    import time
    from urllib.parse import urlsplit

    start = time.monotonic()
    with fixture_server() as url:
        code = scan(url + '/runtime-connections?token=PAGE_PRIVATE',
                    tmp_path, timeout=8, runtime=True, wait=0.8)
    elapsed = time.monotonic() - start
    assert elapsed < 8, f"SSE prevented timely shutdown: {elapsed}"
    data = json.loads((tmp_path / 'result.json').read_text(encoding='utf-8'))
    report = (tmp_path / 'report.md').read_text(encoding='utf-8')
    assert code == 0, data['warnings']
    assert data['runtime']['scope'] == 'network_and_connections_metadata'
    records = data['api']['connections']
    assert len(records) == 2, records
    by_kind = {row['kind']: row for row in records}
    websocket, sse = by_kind['websocket'], by_kind['sse']
    assert urlsplit(websocket['url']).path == '/ws'
    assert websocket['url'].startswith('ws://')
    assert websocket['frames_sent'] >= 1
    assert websocket['frames_received'] >= 1
    assert websocket['observed_at_ms'] > 0
    assert urlsplit(sse['url']).path == '/stream'
    assert sse['status'] == 200
    assert sse['content_type'] == 'text/event-stream'
    assert sse['observed_at_ms'] > 0
    assert data['api']['candidates'] == []
    assert data['charts'] == []
    saved = (tmp_path / 'result.json').read_text(encoding='utf-8') + report
    for value in ('PAGE_PRIVATE', 'WS_URL_PRIVATE', 'SSE_URL_PRIVATE',
                  'FRAME_ONE_PRIVATE', 'FRAME_TWO_PRIVATE', 'WS_SENT_PRIVATE',
                  'SSE_CONTENT_PRIVATE'):
        assert value not in saved
    assert '[REDACTED]' in saved


def test_real_chromium_runtime_libraries_dom_mutations_and_no_false_chart(tmp_path):
    """Explicit JS stubs, distinct from actual chart-library integration."""
    with fixture_server() as url:
        code = scan(url + "/runtime-charts?access_token=PAGE_CHART_PRIVATE",
                    tmp_path, timeout=10, runtime=True, wait=0.7)
    data = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert code == 0, data["warnings"]
    assert data["scan_mode"] == "runtime"
    assert data["runtime"]["chart_observer"]["observer_initialized"] is True
    tech = {item["name"]: item for item in data["runtime"]["technologies"]}
    assert tech["Highcharts"]["version"] == "11.3.0"
    assert tech["Highcharts"]["instances_observed"] == 1
    assert tech["Chart.js"]["version"] == "4.4.1"
    assert tech["Chart.js"]["instances_observed"] == 1
    assert tech["D3"]["instances_observed"] == 0
    assert "Next.js" in tech
    assert "D3" in {item["name"] for item in data["frontend"]}
    charts = data["charts"]
    assert len(charts) >= 3, charts
    marked = [c for c in charts if c["library"] == "Highcharts"]
    assert marked and marked[0]["last_observed_update_ms"] is not None
    assert marked[0]["last_observed_update_ms"] >= marked[0]["first_seen_ms"]
    assert any(c["library"] == "ECharts" for c in charts), charts
    generic = [c for c in charts if c["library"] == "unknown"]
    assert len(generic) >= 1
    assert all(c["detection_level"] == "generic_markup_candidate" for c in generic)
    assert all(c["data_sources"] == [] for c in charts)
    assert all(c["detection_confidence"] <= 0.2 for c in generic)
    assert not data["api"]["candidates"]
    assert not data["api"]["endpoints"]
    assert not data["api"]["connections"]
    saved = (tmp_path / "result.json").read_text(encoding="utf-8") + report
    assert "PAGE_CHART_PRIVATE" not in saved
    assert "PRIVATE_INSTANCE_VALUE" not in saved
    assert "## 런타임 기술 근거 및 차트 DOM 후보" in report



def test_real_chromium_css_bar_chart_and_hash_router_without_icon_false_positive(tmp_path):
    with fixture_server() as url:
        code = scan(url + "/runtime-css-bars#v-dash", tmp_path, timeout=15,
                    runtime=True, wait=0.35)
    data = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    rendered = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert code == 0, data["warnings"]
    assert data["target"]["status_code"] == 200
    charts = data["charts"]
    css = [chart for chart in charts if chart["detection_level"] == "css_bar_pattern_candidate"]
    assert len(css) == 1, charts
    assert css[0]["library"] == "unknown"
    assert css[0]["library_evidence"] == ["css_bar_group_pattern"]
    assert css[0]["first_seen_ms"] is not None
    assert css[0]["last_observed_update_ms"] is None
    assert css[0]["data_sources"] == []
    assert 0 < css[0]["detection_confidence"] <= 0.5
    assert len(charts) == 1, charts  # tiny decorative SVG is excluded
    assert "#v-dash" not in (tmp_path / "result.json").read_text(encoding="utf-8") + rendered
    assert data["api"]["chart_candidates"] == []
