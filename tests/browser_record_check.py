"""Step 3 real headed Chromium fixture (run through xvfb-run on Linux).

Tests manually cause fixture interactions via the same Playwright thread, using
the test-only injected hook. Production Record never synthesizes user actions.
"""
from __future__ import annotations

import json
import gzip
import threading
import time
import subprocess
import sys
from pathlib import Path
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlsplit

from scan import scan
from scanner.models import blank_result
from scanner.record_scan import run_record
from tests.fixture_server import FixtureHandler


class RecordHandler(FixtureHandler):
    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path == '/gz-prefix':
            # Repeated small rows produce >128KiB decoded JSON, yet the first
            # complete row is early enough for a bounded 32KiB prefix hint.
            obj = {'date': 'PRIVATE_DATE_VALUE', 'value': 14,
                   'token': 'BODY_SECRET_VALUE', 'quality': True}
            data = {'items': [obj] * 12000}
            compressed = gzip.compress(json.dumps(data).encode())
            self.protocol_version = 'HTTP/1.1'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Encoding', 'gzip')
            self.send_header('Transfer-Encoding', 'chunked')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            for pos in range(0, len(compressed), 256):
                block = compressed[pos:pos + 256]
                self.wfile.write(f'{len(block):X}\r\n'.encode() + block + b'\r\n')
            self.wfile.write(b'0\r\n\r\n')
            self.wfile.flush()
            return
        if path in ('/gz-small', '/gz-large'):
            if path == '/gz-small':
                data = {'points': [{'date': 'PRIVATE_DATE', 'value': 14,
                                    'password': 'BODY_SECRET'}]}
            else:
                data = {'points': ['X' * 400000]}
            compressed = gzip.compress(json.dumps(data).encode())
            self.protocol_version = 'HTTP/1.1'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Encoding', 'gzip')
            self.send_header('Transfer-Encoding', 'chunked')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            for pos in range(0, len(compressed), 256):
                block = compressed[pos:pos+256]
                self.wfile.write(f'{len(block):X}\r\n'.encode() + block + b'\r\n')
            self.wfile.write(b'0\r\n\r\n')
            self.wfile.flush()
            return
        if path in ('/cross-api-chunked', '/cross-api-chunked-large'):
            # Real HTTP chunked JSON: deliberately omit Content-Length.
            note = ('SENSITIVE_UNSAVED' if path == '/cross-api-chunked'
                    else 'S' * 140000)
            obj = json.dumps({'points': [{'date': 'PRIVATE_DATE', 'value': 9,
                                           'note': note}]}).encode()
            # Only this particular response uses HTTP/1.1 chunk framing.
            # The rest of the fixture keeps its original HTTP/1.0 lifecycle.
            self.protocol_version = 'HTTP/1.1'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Transfer-Encoding', 'chunked')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            for start in range(0, len(obj), 4096):
                piece = obj[start:start+4096]
                self.wfile.write(f'{len(piece):X}\r\n'.encode() + piece + b'\r\n')
            self.wfile.write(b'0\r\n\r\n')
            self.wfile.flush()
            return
        if path == '/cross-api':
            obj = json.dumps({'points': [{'date': 'EXTERNAL_DATE_SECRET',
                                           'value': 12, 'password': 'EXTERNAL_BODY_SECRET'}]}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(obj)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(obj)
            return
        if path == '/record-generic-changes':
            body = b"""<!doctype html><html><body>
            <button id='hover'>Cosmetic change</button>
            <button id='update'>Geometry change</button>
            <svg width='260' height='140' viewBox='0 0 260 140'>
              <g><path d='M 0 0 L 30 20'/><path d='M 4 8 L 40 35'/></g>
            </svg>
            <section style='width:300px;height:160px'>
              <div class='bar' style='width:10%;height:16px'></div>
              <div class='bar' style='width:20%;height:16px'></div>
              <div class='bar' style='width:30%;height:16px'></div>
              <div class='bar' style='width:40%;height:16px'></div>
              <div class='bar' style='width:50%;height:16px'></div>
            </section>
            <script>
              const svg = document.querySelector('svg');
              const bars = document.querySelectorAll('.bar');
              document.getElementById('hover').onclick = () => {
                svg.setAttribute('class', 'theme-hover');
              };
              document.getElementById('update').onclick = () => {
                svg.querySelector('path').setAttribute('d', 'M 0 0 L 99 99');
                bars[0].style.width = '75%';
                bars[1].style.width = '60%';
              };
            </script></body></html>"""
            return self._dynamic_response(body, 'text/html')
        if path == '/record-spa':
            body = b"""<!doctype html><html><body>
            <button id='change'>Change</button>
            <svg class='highcharts-root' width='250' height='150'><path d='M 0 0'/><path d='M 1 1'/></svg>
            <svg class='highcharts-root' width='250' height='150'><path d='M 2 2'/><path d='M 3 3'/></svg>
            <script>
            let counter = 0;
            document.getElementById('change').onclick=() => {
              counter++;
              history.pushState({counter}, '', '/record-spa?route='+counter+'&token=SECRET_ROUTE#v-'+counter);
              fetch('/api/chart?token=SECRET_API');
            };
            </script></body></html>"""
            return self._dynamic_response(body, 'text/html')
        if path == '/record':
            body = b"""<!doctype html><html><body>
            <input id='password' type='password' value='LOGIN_VALUE_PRIVATE'>
            <button id='login'>Login</button>
            <button id='pop'>Popup</button>
            <select id='filter'><option value='a'>A</option><option value='b'>B</option></select>
            <script>
            document.getElementById('login').onclick = () => {
              fetch('/api/login?token=LOGIN_QUERY_PRIVATE', {
                method:'POST', body:'password=LOGIN_BODY_PRIVATE'
              }).then(() => { location.href='/view'; });
            };
            document.getElementById('pop').onclick = () => window.open('/popup', '_blank');
            document.getElementById('filter').onchange = () => fetch('/api/chart?name=PRIVATE_NAME');
            </script></body></html>"""
            return self._dynamic_response(body, 'text/html')
        if path == '/view':
            body = b"""<!doctype html><html><body>
            <select id='filter'><option value='a'>A</option><option value='b'>B</option></select>
            <div id='chart'><svg width='250' height='150'><path d='M 0 0'/><path d='M 1 1'/></svg></div>
            <script>
            const c = document.querySelector('svg');
            document.getElementById('filter').onchange=()=>
              fetch('/api/chart?name=PRIVATE_NAME').then(()=>
                setTimeout(()=>{c.setAttribute('class','highcharts-root');c.setAttribute('viewBox','0 0 250 150');},60));
            </script></body></html>"""
            return self._dynamic_response(body, 'text/html')
        if path == '/api/slow':
            time.sleep(2.0)
            return self._dynamic_response(b'{"items":[{"date":"PRIVATE_DATE","value":5}]}', 'application/json')
        if path == '/popup':
            body = b"<html><body><script>fetch('/api/popup?token=POP_PRIVATE')</script></body></html>"
            return self._dynamic_response(body, 'text/html')
        if path in ('/api/chart', '/api/popup', '/api/late'):
            obj = {'points': [{'date': 'PRIVATE_DATE', 'value': 14,
                               'password': 'BODY_PRIVATE'}]}
            return self._dynamic_response(json.dumps(obj).encode(), 'application/json')
        if path == '/outside':
            body = b"""<html><body><button id='external'>Secret</button>
            <script>document.getElementById('external').onclick=()=>
              fetch('/api/chart?token=OUTSIDE_PRIVATE')</script></body></html>"""
            return self._dynamic_response(body, 'text/html')
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith('/api/login'):
            return self._dynamic_response(b'{"access_token":"LOGIN_RESULT_PRIVATE"}', 'application/json')
        return super().do_POST()


@contextmanager
def serve_record():
    server = ThreadingHTTPServer(('127.0.0.1', 0), RecordHandler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield 'http://127.0.0.1:' + str(server.server_port)
    finally:
        server.shutdown()
        worker.join(timeout=3)
        server.server_close()


def test_real_headed_record_login_navigation_popup_filter_and_excluded_origin(tmp_path):
    stages = set()
    with serve_record() as url, serve_record() as external:
        result = blank_result(url)
        result['scan_mode'] = 'record'
        signal = threading.Event()
        def hook(context, states, elapsed, stop):
            page = context.pages[0]
            if 'login' not in stages:
                stages.add('login')
                page.locator('#login').click()
                page.wait_for_url('**/view')
                return
            if 'filter' not in stages:
                stages.add('filter')
                page.locator('#filter').select_option('b')
                page.wait_for_timeout(250)
                return
            if 'popup' not in stages:
                stages.add('popup')
                page.goto(url + '/record')
                with page.expect_popup() as pop:
                    page.locator('#pop').click()
                pop.value.wait_for_load_state('domcontentloaded')
                return
            if 'external' not in stages:
                stages.add('external')
                context.pages[-1].goto(external + '/outside')
                context.pages[-1].locator('#external').click()
                stop.set()
        code = run_record(url + '/record?name=START_SECRET#test', result,
                          timeout=8, max_duration=20, stop_event=signal, test_hook=hook)
    assert code is False, result['warnings']
    record = result['record']
    assert record['stop_reason'] == 'stop_signal', record
    assert len(record['pages']) >= 3, record['pages']
    assert any(not p['allowed'] for p in record['pages'])
    assert any(i['type'] == 'change' for i in record['interactions'])
    assert any(i['type'] == 'click' for i in record['interactions'])
    assert all(i['page_id'].startswith('page-') for i in record['interactions'])
    assert len({(p['page_id'], p['navigation_id']) for p in record['pages']}) == len(record['pages'])
    assert any(urlsplit(row['url']).path == '/api/chart' for row in result['api']['endpoints'])
    assert any(row['response_body_analysis'] == 'scope_or_auth_body_excluded'
               for row in result['api']['endpoints'])
    assert any(c['library'] == 'Highcharts' for c in result['charts']), result['charts']
    assert result['api']['chart_candidates'], (result['charts'], result['api']['endpoints'])
    assert all(link['status'] == 'candidate_only' for link in result['api']['chart_candidates'])
    assert all(c['page_id'].startswith('page-') for c in result['charts'])
    assert all('PRIVATE' not in json.dumps(c) for c in result['charts'])
    saved = json.dumps(result, ensure_ascii=False)
    for secret in ('START_SECRET', 'LOGIN_VALUE_PRIVATE', 'LOGIN_BODY_PRIVATE',
                   'LOGIN_RESULT_PRIVATE', 'PRIVATE_NAME', 'PRIVATE_DATE',
                   'BODY_PRIVATE', 'OUTSIDE_PRIVATE', 'POP_PRIVATE'):
        assert secret not in saved, secret


def test_real_headed_record_time_limit_and_browser_closed(tmp_path):
    with serve_record() as url:
        data = blank_result(url)
        assert run_record(url+'/record', data, timeout=5, max_duration=0.6,
                          stop_event=threading.Event()) is False
        assert data['record']['stop_reason'] == 'max_duration'
        data2 = blank_result(url)
        closed = set()
        def hook(context, states, elapsed, stop):
            if not closed:
                closed.add(True)
                for page in list(context.pages):
                    page.close()
        assert run_record(url+'/record', data2, timeout=5, max_duration=10,
                          stop_event=threading.Event(), test_hook=hook) is False
        assert data2['record']['stop_reason'] == 'browser_closed'


def test_real_headed_record_enter_creates_reports_via_cli(tmp_path):
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / 'enter-cli'
    with serve_record() as url:
        finished = subprocess.run(
            [sys.executable, '-u', str(root / 'scan.py'), url + '/record',
             '--record', '--runtime', '--max-duration', '10', '--out', str(output)],
            input='\n', capture_output=True, text=True, timeout=25, cwd=root)
    assert finished.returncode == 0, finished.stdout + finished.stderr
    data = json.loads((output / 'result.json').read_text(encoding='utf-8'))
    report = (output / 'report.md').read_text(encoding='utf-8')
    assert data['scan_mode'] == 'record'
    assert data['record']['stop_reason'] == 'enter'
    assert data['record']['record_ended_at']
    assert 'Record 수집 구간 및 범위' in report
    assert 'LOGIN_VALUE_PRIVATE' not in report


def test_real_headed_record_ctrlc_signal_and_inflight_response_limit(monkeypatch):
    import scanner.record_scan as record_mod
    with serve_record() as url:
        data = blank_result(url)
        def interrupt(context, states, elapsed, stop):
            raise KeyboardInterrupt()
        assert run_record(url+'/record', data, timeout=5, max_duration=10,
                          stop_event=threading.Event(), test_hook=interrupt) is False
        assert data['record']['stop_reason'] == 'ctrl_c'

        monkeypatch.setattr(record_mod, 'MAX_DETAIL', 2)
        limited = blank_result(url)
        states = set()
        start = time.monotonic()
        def issue_many(context, pages, elapsed, stop):
            if not states:
                states.add('sent')
                page = context.pages[0]
                page.evaluate("""() => {
                  fetch('/api/slow?token=INFLIGHT_PRIVATE');
                  for(let i=0;i<8;i++) fetch('/api/chart?token=OVERFLOW_PRIVATE&n='+i);
                }""")
                page.wait_for_timeout(400)
                stop.set()
        assert run_record(url+'/record', limited, timeout=5, max_duration=10,
                          stop_event=threading.Event(), test_hook=issue_many) is False
        assert time.monotonic() - start < 9
        assert limited['record']['omitted_events']['network'] >= 5
        assert len(limited['api']['endpoints']) <= 2
        assert any('상한' in warning or '미수집' in warning for warning in limited['warnings'])
        dumped = json.dumps(limited, ensure_ascii=False)
        assert 'INFLIGHT_PRIVATE' not in dumped
        assert 'OVERFLOW_PRIVATE' not in dumped


def test_real_headed_spa_hash_and_history_not_fake_documents(tmp_path):
    # SPA pushState/fragment changes the address, not the document identity.
    # Full page navigation still creates a separate document and new markers.
    stages = set()
    with serve_record() as url:
        data = blank_result(url)
        def operate(context, pages, elapsed, stop):
            pg = context.pages[0]
            if 'spa' not in stages:
                stages.add('spa')
                pg.locator('#change').click()
                pg.locator('#change').click()
                pg.evaluate("""() => history.pushState({}, '', '/record-spa?token=HIDDEN#route')""")
                pg.wait_for_timeout(350)
                return
            if 'reload' not in stages:
                stages.add('reload')
                pg.goto(url + '/record-spa')
                pg.locator('#change').click()
                pg.wait_for_timeout(150)
                stop.set()
        assert run_record(url + '/record-spa#first', data, timeout=8,
                          max_duration=15, stop_event=threading.Event(),
                          test_hook=operate) is False
    rec = data['record']
    assert rec['stop_reason'] == 'stop_signal'
    assert len(rec['pages']) == 2, rec['pages']
    assert len({(p['page_id'], p['navigation_id']) for p in rec['pages']}) == 2
    markers = [m for m in rec['interactions'] if m['tag'] == 'button']
    assert len(markers) == 3, markers
    assert len({(m['navigation_id'], m['at_ms']) for m in markers}) == 3
    assert markers[0]['navigation_id'] == markers[1]['navigation_id']
    assert markers[2]['navigation_id'] != markers[1]['navigation_id']
    chart_ids = [chart['id'] for chart in data['charts']]
    assert len(chart_ids) == len(set(chart_ids)), chart_ids
    assert data['target']['final_url'] is not None
    output = json.dumps(data, ensure_ascii=False)
    for secret in ('SECRET_ROUTE', 'SECRET_API', 'HIDDEN', '#first', '#route'):
        assert secret not in output


def test_real_headed_closed_browser_keeps_redacted_final_url(tmp_path):
    with serve_record() as url:
        data = blank_result(url + '/record?token=ORIGINAL_SECRET')
        closed = set()
        def close_early(context, pages, elapsed, stop):
            if not closed:
                closed.add(True)
                context.pages[0].close()
        assert run_record(url+'/record?token=LAST_SECRET', data,
                          timeout=5, max_duration=10,
                          stop_event=threading.Event(), test_hook=close_early) is False
    assert data['record']['stop_reason'] == 'browser_closed'
    assert data['target']['final_url'] == url + '/record'
    output = json.dumps(data)
    assert 'LAST_SECRET' not in output
    assert 'ORIGINAL_SECRET' not in output


def test_real_headed_external_json_requires_explicit_allow_origin():
    with serve_record() as dashboard, serve_record() as external:
        records = []
        for allow in ([], [external]):
            result = blank_result(dashboard)
            fired = set()
            def hook(context, pages, elapsed, stop):
                if not fired:
                    fired.add(True)
                    pg = context.pages[0]
                    pg.evaluate("""base => fetch(base + '/cross-api?token=EXTERNAL_QUERY_SECRET').catch(() => {})""", external)
                    pg.wait_for_timeout(300)
                    stop.set()
            assert run_record(dashboard+'/record', result, timeout=8, max_duration=12,
                              allow_origin=allow, stop_event=threading.Event(),
                              test_hook=hook) is False
            endpoint = next(row for row in result['api']['endpoints']
                            if '/cross-api' in row['url'])
            assert endpoint['url'] == external + '/cross-api'
            records.append(endpoint)
            serialized = json.dumps(result, ensure_ascii=False)
            for secret in ('EXTERNAL_DATE_SECRET', 'EXTERNAL_BODY_SECRET', 'EXTERNAL_QUERY_SECRET'):
                assert secret not in serialized
        assert records[0]['response_body_analysis'] == 'scope_or_auth_body_excluded'
        assert records[0]['json_structure'] is None
        assert records[1]['response_body_analysis'] == 'structure_only'
        assert records[1]['json_structure'] == {
            'points': [{'date': 'string', 'value': 'number',
                        '[REDACTED_KEY]': 'string'}]}


def test_real_headed_headerless_chunked_json_authorization_and_size_bound():
    with serve_record() as dashboard, serve_record() as external:
        for path, permit, expected in [
            ('/cross-api-chunked', False, 'scope_or_auth_body_excluded'),
            ('/cross-api-chunked', True, 'structure_only'),
            ('/cross-api-chunked-large', True, 'too_large'),
        ]:
            output = blank_result(dashboard)
            fired = set()
            def hook(context, pages, elapsed, stop):
                if not fired:
                    fired.add(True)
                    pg = context.pages[0]
                    pg.evaluate("""url => fetch(url).catch(() => {})""",
                                external + path + '?password=QUERY_SECRET')
                    pg.wait_for_timeout(400)
                    stop.set()
            assert run_record(dashboard + '/record', output, timeout=8,
                              max_duration=15, allow_origin=[external] if permit else [],
                              stop_event=threading.Event(), test_hook=hook) is False
            matches = [row for row in output['api']['endpoints'] if row['url'].endswith(path)]
            assert len(matches) == 1, output['api']['endpoints']
            row = matches[0]
            assert row['response_body_analysis'] == expected, row
            if expected == 'structure_only':
                assert row['json_structure'] == {
                    'points': [{'date': 'string', 'value': 'number', 'note': 'string'}]}
            else:
                assert row['json_structure'] is None
            assert 'QUERY_SECRET' not in json.dumps(output)
            assert 'SENSITIVE_UNSAVED' not in json.dumps(output)
            assert 'PRIVATE_DATE' not in json.dumps(output)


def test_real_headed_generic_svg_css_bar_geometry_evidence_without_raw_values():
    from scanner.runtime_detect import collect_runtime_charts
    observed = set()
    with serve_record() as url:
        result = blank_result(url)
        def hook(context, pages, elapsed, stop):
            if 'checked' in observed:
                return
            observed.add('checked')
            page = context.pages[0]
            local = {'charts': [], 'runtime': {}, 'frontend': [], 'evidence': []}
            collect_runtime_charts(page, local)
            baseline = {c['detection_level']: c for c in local['charts']}
            assert baseline['css_bar_pattern_candidate']['last_observed_update_ms'] is None
            assert baseline['generic_markup_candidate']['last_observed_update_ms'] is None
            page.locator('#hover').click()
            page.wait_for_timeout(100)
            collect_runtime_charts(page, local)
            hover = next(c for c in local['charts']
                         if c['detection_level'] == 'generic_markup_candidate')
            assert hover['last_observed_update_ms'] is None, hover
            page.locator('#update').click()
            page.wait_for_timeout(160)
            collect_runtime_charts(page, local)
            updates = {c['detection_level']: c for c in local['charts']}
            assert updates['generic_markup_candidate']['change_evidence'] == 'svg_geometry_changed'
            assert updates['css_bar_pattern_candidate']['change_evidence'] == 'css_bar_geometry_changed'
            assert all(c['last_observed_update_ms'] for c in updates.values())
            stop.set()
        assert run_record(url+'/record-generic-changes', result, timeout=8,
                          max_duration=15, stop_event=threading.Event(), test_hook=hook) is False
    charts = {c['detection_level']: c for c in result['charts']}
    assert len(charts) == 2, result['charts']
    assert charts['generic_markup_candidate']['change_evidence'] == 'svg_geometry_changed'
    assert charts['css_bar_pattern_candidate']['change_evidence'] == 'css_bar_geometry_changed'
    assert all(type(c['last_observed_update_ms']) is int for c in charts.values())
    assert result['api'].get('chart_candidates', []) == []
    serialized = json.dumps(result, ensure_ascii=False)
    for value in ('75%', '60%', '99 99', 'M 0 0', 'theme-hover'):
        assert value not in serialized


def test_real_headed_approved_gzip_without_length_bounded_by_decoded_bytes():
    from scanner.network import MAX_JSON_BYTES
    # Same manual Record scope; all network actions originate from local fixture.
    for endpoint, permitted, expected in [
        ('/gz-small', False, 'scope_or_auth_body_excluded'),
        ('/gz-small', True, 'structure_only'),
        ('/gz-large', True, 'decoded_too_large'),
    ]:
        with serve_record() as dashboard, serve_record() as external:
            output = blank_result(dashboard)
            fired = set()
            def hook(context, pages, elapsed, stop):
                if fired:
                    return
                fired.add(True)
                pg = context.pages[0]
                pg.evaluate('u => fetch(u).then(r => r.json()).then(x => !!x)',
                            external + endpoint + '?access_token=REDACT_ME')
                pg.wait_for_timeout(250)
                stop.set()

            assert run_record(dashboard + '/record', output, timeout=8,
                              max_duration=15,
                              allow_origin=[external] if permitted else [],
                              stop_event=threading.Event(), test_hook=hook) is False
            rows = [r for r in output['api']['endpoints']
                    if r['url'].endswith(endpoint)]
            assert len(rows) == 1, output['api']['endpoints']
            row = rows[0]
            actual = row['response_body_analysis']
            # CDP dataLength delivery is best-effort for very short gzip
            # replies. If Chromium did not provide complete decoded length,
            # rejecting the body is a *valid fail-closed safety outcome*.
            # Never call this a successful JSON structure extraction.
            if permitted and actual == 'compressed_decoded_unavailable':
                assert row['json_structure'] is None
                assert row.get('json_prefix_structure') is None
                assert row.get('cdp_decoded_diagnostic') in (
                    'request_unmatched', 'request_ambiguous', 'loading_failed',
                    'invalid_data_length', 'loading_incomplete',
                    'no_data_events', 'nonpositive_decoded_length',
                    'diagnostic_unavailable')
            else:
                assert actual == expected, row
                if expected == 'structure_only':
                    assert row['json_structure'] == {
                        'points': [{'date': 'string', 'value': 'number',
                                    '[REDACTED_KEY]': 'string'}]}
                else:
                    assert row['json_structure'] is None
            saved = json.dumps(output)
            for secret in ('REDACT_ME', 'PRIVATE_DATE', 'BODY_SECRET'):
                assert secret not in saved


def test_headed_oversized_gzip_records_partial_field_hints_or_safely_abstains():
    with serve_record() as dashboard, serve_record() as external:
        output = blank_result(dashboard)
        called = set()
        def interact(context, pages, elapsed, stop):
            if called:
                return
            called.add(1)
            pg = context.pages[0]
            pg.evaluate('u => fetch(u).then(r => r.json()).then(x => x.items.length)',
                        external + '/gz-prefix?access_token=QUERY_SECRET_VALUE')
            pg.wait_for_timeout(350)
            stop.set()
        assert run_record(dashboard+'/record', output, timeout=8,
                          allow_origin=[external], max_duration=14,
                          stop_event=threading.Event(), test_hook=interact) is False
    api = next(r for r in output['api']['endpoints'] if r['url'].endswith('/gz-prefix'))
    status = api['response_body_analysis']
    assert status in ('decoded_too_large', 'compressed_decoded_unavailable'), api
    assert api['json_structure'] is None
    if status == 'compressed_decoded_unavailable':
        # CDP may omit the decoded-length request event entirely; no body is
        # allowed to be read or inferred in that case.
        assert api.get('json_prefix_structure') is None
        assert api['cdp_decoded_diagnostic'] in (
            'request_unmatched', 'request_ambiguous', 'loading_failed',
            'invalid_data_length', 'loading_incomplete', 'no_data_events',
            'nonpositive_decoded_length', 'diagnostic_unavailable')
    else:
        sample = api.get('json_prefix_structure')
        assert sample is not None, api
        assert sample['completeness'] == 'partial_prefix_only'
        assert sample['sample_kind'] == 'first_complete_object'
        assert sample['fields'] == {
            'date': 'string', 'value': 'number',
            '[REDACTED_KEY]': 'string', 'quality': 'boolean'
        }
    assert output['api'].get('chart_candidates', []) == []
    dumped = json.dumps(output, ensure_ascii=False)
    for secret in ('PRIVATE_DATE_VALUE', 'BODY_SECRET_VALUE', 'QUERY_SECRET_VALUE'):
        assert secret not in dumped
