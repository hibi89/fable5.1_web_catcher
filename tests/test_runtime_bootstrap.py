"""Unit-one checks that do not require downloading a browser."""
from __future__ import annotations

import json

from scanner.runtime_scan import _bounded_wait, _script_urls


class FakePage:
    def __init__(self):
        self.waits = []
        self.evaluations = []

    def wait_for_timeout(self, ms):
        self.waits.append(ms)

    def evaluate(self, script):
        self.evaluations.append(script)


def test_wait_window_bounded_and_auto_scroll_read_only():
    page = FakePage()
    assert _bounded_wait(page, 0) == 0
    assert not page.waits
    assert _bounded_wait(page, 0.201) == 2
    assert sum(page.waits) == 201
    assert len(page.evaluations) == 2
    assert all('scrollBy' in call for call in page.evaluations)


def test_script_urls_sanitized_without_fetching():
    class Locator:
        def evaluate_all(self, script, attr):
            return ['https://example.test/app.js?access_token=VERY_SECRET',
                    'https://example.test/app.js?access_token=VERY_SECRET',
                    'data:text/javascript,x']

    class Page:
        def locator(self, query):
            assert query == 'script[src]'
            return Locator()

    urls = _script_urls(Page(), 'script[src]', 'src')
    assert len(urls) == 1
    assert 'VERY_SECRET' not in str(urls)
    assert 'REDACTED' in str(urls)


def test_runtime_cli_routing_and_static_unchanged(monkeypatch, tmp_path):
    from scan import scan

    def fake_runtime(url, result, *, timeout, wait, headed):
        assert 'PRIVATE' in url  # request URL stays in memory, not persisted
        assert wait == 0.1
        assert not headed
        result['target']['final_url'] = 'https://example.test/'
        result['target']['status_code'] = 200
        result['runtime'] = {'scope': 'navigation_only', 'wait_seconds': wait}
        return False

    monkeypatch.setattr('scanner.runtime_scan.scan_runtime_page', fake_runtime)
    path = tmp_path / 'runtime'
    assert scan('https://example.test/?token=PRIVATE', path, runtime=True, wait=0.1) == 0
    data = json.loads((path / 'result.json').read_text(encoding='utf-8'))
    assert data['scan_mode'] == 'runtime'
    assert data['api']['endpoints'] == []
    assert data['charts'] == []
    assert 'PRIVATE' not in (path / 'result.json').read_text(encoding='utf-8')
    assert 'PRIVATE' not in (path / 'report.md').read_text(encoding='utf-8')


def test_runtime_invalid_url_partial_result(tmp_path):
    from scan import scan
    out = tmp_path / 'bad'
    assert scan('file:///etc/passwd?token=PRIVATE', out, runtime=True) == 2
    data = json.loads((out / 'result.json').read_text(encoding='utf-8'))
    assert data['scan_mode'] == 'runtime'
    assert data['target']['status_code'] is None
    assert 'PRIVATE' not in (out / 'result.json').read_text(encoding='utf-8')


def test_runtime_browser_keeps_url_hash_without_persisting_it(tmp_path, monkeypatch):
    import json
    import scanner.runtime_scan as runtime_scan
    from scan import scan

    seen = []
    def capture(url, result, *, timeout, wait, headed):
        seen.append(url)
        result["runtime"] = {}
        result["target"]["final_url"] = "https://example.com/"
        return False

    monkeypatch.setattr(runtime_scan, "scan_runtime_page", capture)
    code = scan("https://example.com/#v-dash", tmp_path, runtime=True, wait=0.1)
    assert code == 0
    assert seen == ["https://example.com/#v-dash"]
    saved = (tmp_path / "result.json").read_text(encoding="utf-8") + (
        tmp_path / "report.md").read_text(encoding="utf-8")
    assert "#v-dash" not in saved
    assert json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))["scan_mode"] == "runtime"
