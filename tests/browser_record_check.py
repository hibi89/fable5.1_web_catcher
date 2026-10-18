"""Step 3 real headed Chromium fixture (run through xvfb-run on Linux).

Tests manually cause fixture interactions via the same Playwright thread, using
the test-only injected hook. Production Record never synthesizes user actions.
"""
from __future__ import annotations

import json
import threading
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
                print('RECORD_CHART_FIXTURE', page.evaluate('() => ({cls: document.querySelector("svg")?.getAttribute("class"), chartProbe: !!window.__fable51_chart_probe, observer: window.__fable51_chart_probe?.snapshot()})'))
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
    assert all(i['page_id'].startswith('page-') for i in record['interactions'])
    assert len({(p['page_id'], p['navigation_id']) for p in record['pages']}) == len(record['pages'])
    assert any(urlsplit(row['url']).path == '/api/chart' for row in result['api']['endpoints'])
    assert any(row['response_body_analysis'] == 'scope_or_auth_body_excluded'
               for row in result['api']['endpoints'])
    assert any(c['library'] == 'Highcharts' for c in result['charts']), result['charts']
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
