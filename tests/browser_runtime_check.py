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
