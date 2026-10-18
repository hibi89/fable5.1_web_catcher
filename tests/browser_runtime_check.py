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
    assert data['api'] == {'endpoints': [], 'candidates': [], 'connections': []}
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
    assert data['runtime']['scope'] == 'network_metadata_only'
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
