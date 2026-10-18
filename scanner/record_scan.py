"""Step 3 local, consent-based headed Record session.

No user input, credential, DOM text, raw payload, HAR, screenshots, or
persistent browser profile is stored. All Playwright API calls stay on the
thread which created the sync Playwright instance.
"""
from __future__ import annotations

import json
import re
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

from .bundle_scan import BundleCollector, _origin
from .cdp_decoded_size import DecodedLengthTracker
from .json_prefix_hints import MAX_PREFIX_HINTS
from .chart_mapping import map_chart_api_candidates
from .connections import ConnectionCollector
from .network import NetworkCollector
from .runtime_detect import CHART_OBSERVER_SCRIPT, collect_runtime_charts
from .sanitize import request_url

MAX_EVENTS = 10_000
MAX_DETAIL = 1_000
MAX_INTERACTIONS = 2_000
MAX_DOCUMENTS = 100
PUMP_MS = 200
_AUTH_PATH = re.compile(r"/(?:login|signin|oauth|authorize|callback|token|refresh|session|password|credential|mfa|otp)(?:/|$)", re.I)
_SAFE_SEGMENT = re.compile(r"[a-z][a-z0-9_-]{0,24}\Z")

INTERACTION_SCRIPT = r"""
(() => {
  'use strict';
  const data = [], MAX = 2000;
  let dropped = 0;
  const now = () => Math.round(performance.timeOrigin + performance.now());
  function selector(el) {
    const parts = [];
    for (let n=el, d=0; n && n.nodeType===1 && d<5; n=n.parentElement, d++) {
      const tag=n.localName.toLowerCase();
      if (!/^[a-z][a-z0-9-]*$/.test(tag)) break;
      let index=1, sib=n;
      while ((sib=sib.previousElementSibling)) if (sib.localName===n.localName) index++;
      parts.unshift(tag+':nth-of-type('+Math.min(index,999)+')');
      if (n===document.body) break;
    }
    return parts.join(' > ').slice(0,250);
  }
  function marker(event) {
    const el=event.target;
    if (!el || !el.localName) return;
    if (el.localName.toLowerCase()==='input' && el.type==='password') return;
    if (data.length>=MAX) { dropped++; return; }
    const item = {seq:data.length+1, type:event.type, at_ms:now(),
      tag:el.localName.toLowerCase(), selector:selector(el)};
    data.push(item);
    try { if (typeof window.__fable51_record_marker === 'function')
      void window.__fable51_record_marker(item); } catch (_) {}
  }
  document.addEventListener('click', marker, true);
  document.addEventListener('change', marker, true);
  Object.defineProperty(window, '__fable51_interactions', {
    value: {snapshot: () => ({items:data.slice(), dropped})},
    enumerable:false, configurable:false
  });
})();
"""


def origin_string(url: str) -> str | None:
    origin = _origin(url)
    if origin is None:
        return None
    scheme, host, port = origin
    bracket = '[' + host + ']' if ':' in host else host
    default = 443 if scheme == 'https' else 80
    return f'{scheme}://{bracket}' + (f':{port}' if port != default else '')


def allowed_origins(url: str, extra: list[str] | None) -> set[str]:
    base = origin_string(url)
    if base is None:
        raise ValueError('Record 대상은 HTTP/HTTPS URL이어야 합니다.')
    origins = {base}
    for raw in extra or []:
        parsed = urlsplit(raw)
        if (parsed.username or parsed.password or '*' in (parsed.hostname or '')
                or parsed.path not in ('', '/')
                or parsed.query or parsed.fragment or origin_string(raw) is None):
            raise ValueError('--allow-origin은 경로·쿼리 없는 정확한 HTTP/HTTPS origin만 허용합니다.')
        origins.add(origin_string(raw))
    return origins


def record_safe_url(url: str) -> str:
    """Conservatively redact all query/fragment values and dynamic path segments."""
    try:
        p = urlsplit(url)
        origin = origin_string(url)
        if origin is None:
            return '[INVALID URL]'
        segments = []
        for seg in p.path.split('/'):
            if not seg:
                segments.append('')
            elif _SAFE_SEGMENT.fullmatch(seg):
                segments.append(seg)
            else:
                segments.append('[REDACTED]')
        path = '/'.join(segments)
        # No query values or fragment are persisted, even for innocent-looking names.
        return (origin + path)[:600]
    except (ValueError, TypeError):
        return '[INVALID URL]'


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _guarded(script: str, origins: set[str]) -> str:
    return '(() => { if (!' + json.dumps(sorted(origins)) + '.includes(location.origin)) return;\n' + script + '\n})();'


class ScopedNetworkCollector(NetworkCollector):
    """Reuse Step 2's event collector, restricting JSON bodies to permitted origins."""

    def __init__(self, result, origins, pages):
        super().__init__(result, allow_unknown_length=True)
        self.origins = origins
        self.pages = pages
        self.event_count = 0
        self.omitted = 0
        permitted = lambda url: (origin_string(url) in self.origins
                                and not _AUTH_PATH.search(urlsplit(url).path))
        self.decoded_tracker = DecodedLengthTracker(permitted, capture_prefix=True)
        self._prefix_hints = 0

    def on_request(self, request):
        if request.resource_type not in ('xhr', 'fetch'):
            return
        self.event_count += 1
        if self.event_count > MAX_EVENTS:
            self.omitted += 1
            return
        try:
            frame = request.frame
            page = frame.page
            state = self.pages.get(page)
            if (not state or frame != page.main_frame
                    or origin_string(frame.url) not in self.origins):
                self.omitted += 1
                return
        except Exception:
            self.omitted += 1
            return
        if len(self.records) >= MAX_DETAIL:
            self._over_limit = True
            self.omitted += 1
            return
        # Step 2's limit is an instance override, not a separate parsing engine.
        self.max_endpoints = MAX_DETAIL
        super().on_request(request)
        row = self._request_rows.get(request)
        if row:
            row['page_id'] = state['page_id']
            row['navigation_id'] = state['navigation_id']
            row['frame_id'] = state['frame_id']
            row['url'] = record_safe_url(request.url)

    def on_response(self, response):
        super().on_response(response)
        row = self._request_rows.get(response.request)
        if row is None:
            return
        if origin_string(response.url) not in self.origins or _AUTH_PATH.search(urlsplit(response.url).path):
            self._body_queue.pop(response.request, None)
            row['json_structure'] = None
            row['response_body_analysis'] = 'scope_or_auth_body_excluded'
            return
        # An unknown wire length plus gzip/br does not bound decoded memory.
        # Wait for passive CDP decoded-byte metadata; never read blindly.
        if row['response_body_analysis'] == 'waiting_for_finished_size_check':
            encoding = response.headers.get('content-encoding', '').strip().lower()
            if encoding and encoding != 'identity':
                row['response_body_analysis'] = 'cdp_decoded_waiting_finish'

    def on_finished(self, request):
        row = self._request_rows.get(request)
        if row and row['response_body_analysis'] == 'cdp_decoded_waiting_finish':
            row['response_body_analysis'] = 'cdp_decoded_pending'
            return
        super().on_finished(request)

    def flush_completed(self):
        for request, response in list(self._body_queue.items()):
            row = self._request_rows.get(request)
            if row is None or row['response_body_analysis'] != 'cdp_decoded_pending':
                continue
            verdict, expected = self.decoded_tracker.decide(request)
            if verdict == 'pending':
                continue
            if verdict == 'ready':
                self._expected_decoded_bytes[request] = expected
                row['response_body_analysis'] = 'ready'
            else:
                row['response_body_analysis'] = (
                    'decoded_too_large' if verdict == 'decoded_too_large'
                    else 'compressed_decoded_unavailable')
                if verdict != 'decoded_too_large':
                    row['cdp_decoded_diagnostic'] = (
                        self.decoded_tracker.refusal_reason(request))
                self._body_queue.pop(request, None)
        super().flush_completed()
        # Do not promote sampled prefix structure into full JSON structure.
        # Only mark oversized, explicitly approved JSON responses and only
        # if their CDP stream completed. No raw response values are stored.
        for request, row in list(self._request_rows.items()):
            if self._prefix_hints >= MAX_PREFIX_HINTS:
                break
            if (row['response_body_analysis'] != 'decoded_too_large'
                    or row.get('json_prefix_structure') is not None
                    or row.get('status') != 200
                    or not row.get('content_type', '').endswith(('json', '+json'))):
                continue
            hint = self.decoded_tracker.hint_for(request)
            if hint is not None:
                row['json_prefix_structure'] = hint
                self._prefix_hints += 1

    def finalize(self):
        self.flush_completed()
        # Requests still lacking completion-length evidence stay unread.
        for request, response in list(self._body_queue.items()):
            row = self._request_rows.get(request)
            if row and row['response_body_analysis'] in (
                    'cdp_decoded_pending', 'cdp_decoded_waiting_finish'):
                row['response_body_analysis'] = 'compressed_decoded_unavailable'
                row['cdp_decoded_diagnostic'] = (
                    self.decoded_tracker.refusal_reason(request))
                self._body_queue.pop(request, None)
        super().finalize()
        self.decoded_tracker.clear()
        if self.omitted:
            self.result['warnings'].append(
                f'Record 요청 상세 미수집 {self.omitted}건(범위/프레임/상한, 일부 이벤트 제외)'
            )


class ScopedConnectionCollector(ConnectionCollector):
    def __init__(self, result, origins, pages):
        super().__init__(result)
        self.origins = origins
        self.pages = pages

    def attach_page(self, page):
        page.on('websocket', lambda ws: self._ws(page, ws))

    def _ws(self, page, ws):
        state = self.pages.get(page)
        if not state or origin_string(page.url) not in self.origins:
            return
        before = len(self.records)
        super().on_websocket(ws)
        if len(self.records) > before:
            self.records[-1].update(page_id=state['page_id'],
                                    navigation_id=state['navigation_id'],
                                    frame_id=state['frame_id'])
            self.records[-1]['url'] = record_safe_url(ws.url.replace('wss:', 'https:', 1).replace('ws:', 'http:', 1)).replace('https:', 'wss:', 1).replace('http:', 'ws:', 1)

    def on_response(self, response):
        try:
            frame = response.request.frame
            page = frame.page
            state = self.pages.get(page)
            if not state or frame != page.main_frame or origin_string(frame.url) not in self.origins:
                return
        except Exception:
            return
        before = len(self.records)
        super().on_response(response)
        if len(self.records) > before:
            self.records[-1].update(page_id=state['page_id'],
                                    navigation_id=state['navigation_id'],
                                    frame_id=state['frame_id'])
            self.records[-1]['url'] = record_safe_url(response.url)


def _terminal(stop: threading.Event, reason: list[str]):
    try:
        input()
        reason.append('enter')
    except EOFError:
        reason.append('stdin_eof')
    except OSError:
        reason.append('stdin_unavailable')
    finally:
        stop.set()


def run_record(url: str, result: dict, *, timeout: float,
               max_duration: float = 900, allow_origin: list[str] | None = None,
               stop_event: threading.Event | None = None, test_hook=None) -> bool:
    """Record until Enter, Ctrl+C, deadline or all windows close; return fatal."""
    from playwright.sync_api import Error as BrowserError, sync_playwright
    origins = allowed_origins(url, allow_origin)
    record = result['record'] = {
        'record_started_at': _utc(), 'record_ended_at': None,
        'duration_seconds': 0, 'stop_reason': None, 'allowed_origins': sorted(origins),
        'pages': [], 'interactions': [],
        'omitted_events': {'network': 0, 'interactions': 0, 'documents': 0},
        'limits': {'network_events': MAX_EVENTS, 'detailed_requests': MAX_DETAIL,
                   'interactions': MAX_INTERACTIONS, 'documents': MAX_DOCUMENTS},
        'scope': 'allowed_origin_main_frames_only',
        'limitations': ['manual_actions_not_causality', 'iframe_dom_not_supported',
                        'no_credential_or_raw_content_capture', 'heuristic_chart_api_linkage'],
    }
    result['runtime'] = {'domcontentloaded_observed': False, 'wait_seconds': 0,
                         'scroll_steps': 0, 'scope': 'record_manual',
                         'xhr_fetch_requests_seen': 0, 'xhr_fetch_responses_seen': 0,
                         'technologies': []}
    result['target']['input_url'] = record_safe_url(url)
    reason = ['unknown']
    fatal = False
    started = time.monotonic()
    stop = stop_event if stop_event is not None else threading.Event()
    pages = {}
    net = conn = bundles = None
    browser = context = None
    playwright_instance = None
    seen = {}
    marker_keys = set()
    docs_count = 0
    has_iframe_warning = False
    try:
        print('분석 범위: ' + ', '.join(sorted(origins)))
        print('브라우저에서 직접 조작하세요.')
        print('종료하려면 이 터미널로 돌아와 Enter를 누르세요.')
        print('로그인 비밀번호와 입력 내용은 기록하지 않습니다.')
        print('API 경로와 응답 구조에도 업무 정보가 포함될 수 있습니다.')
        if stop_event is None:
            threading.Thread(target=_terminal, args=(stop, reason), daemon=True).start()
        playwright_instance = sync_playwright().start()
        p = playwright_instance
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(accept_downloads=False, ignore_https_errors=False)
        def add_marker(marker, state):
            if not isinstance(marker, dict):
                return
            seq, stamp = marker.get('seq'), marker.get('at_ms')
            tag, selector = marker.get('tag'), marker.get('selector')
            if (type(seq) is not int or seq <= 0 or seq > MAX_INTERACTIONS
                    or type(stamp) is not int or stamp <= 0
                    or marker.get('type') not in ('click', 'change')
                    or not isinstance(tag, str)
                    or not re.fullmatch(r'[a-z][a-z0-9-]{0,30}', tag)
                    or not isinstance(selector, str)
                    or not re.fullmatch(r'[a-z0-9> ():nth-of-type.\-]{1,250}', selector)):
                return
            ident = (state['page_id'], state['navigation_id'], seq)
            if ident in marker_keys:
                return
            # Keep the dedupe index and persisted markers bounded together.
            if len(record['interactions']) >= MAX_INTERACTIONS:
                record['omitted_events']['interactions'] += 1
                return
            marker_keys.add(ident)
            record['interactions'].append({
                'type': marker['type'], 'at_ms': stamp,
                'tag': tag, 'selector': selector,
                'page_id': state['page_id'],
                'navigation_id': state['navigation_id']})

        def on_marker(source, marker):
            try:
                pg, frame = source['page'], source['frame']
                state = pages.get(pg)
                if (state and frame == pg.main_frame
                        and origin_string(frame.url) in origins
                        and state['document_key'] is not None):
                    add_marker(marker, state)
            except Exception:
                # Site events must not disrupt user browsing.
                pass

        context.expose_binding('__fable51_record_marker', on_marker)
        context.add_init_script(_guarded(CHART_OBSERVER_SCRIPT, origins))
        context.add_init_script(_guarded(INTERACTION_SCRIPT, origins))
        net = ScopedNetworkCollector(result, origins, pages)
        conn = ScopedConnectionCollector(result, origins, pages)
        bundles = BundleCollector(result)
        net.attach(context)
        context.on('response', conn.on_response)
        bundles.attach(context)

        def on_page(page):
            nonlocal docs_count
            if page in pages:
                return
            page_id = f'page-{len(pages)+1:03d}'
            state = {'page_id': page_id, 'navigation_id': 'nav-000',
                     'frame_id': page_id + '-main', 'document_key': None,
                     'document_time_origin': None, 'last_document_url': None}
            pages[page] = state
            conn.attach_page(page)
            def navigated(frame):
                nonlocal docs_count
                if frame != page.main_frame:
                    return
                address = frame.url
                in_scope = origin_string(address) in origins
                # Playwright fires framenavigated for hash/history changes too.
                # performance.timeOrigin is constant for a living JS document;
                # it changes on a true document load. Never inspect off-scope JS.
                document_origin = None
                if in_scope:
                    try:
                        document_origin = frame.evaluate("performance.timeOrigin")
                    except BrowserError:
                        pass
                last_origin = state.get('document_time_origin')
                last_url = state.get('last_document_url')
                url_without_hash = address.split('#', 1)[0]
                same_document = (
                    state['document_key'] is not None and
                    ((document_origin is not None and last_origin is not None
                      and document_origin == last_origin) or
                     (document_origin is None and last_url == url_without_hash
                      and in_scope))
                )
                # A pushState() route can change the path without loading a
                # document. The timeOrigin check above preserves its identity.
                if same_document:
                    if page_id == 'page-001':
                        result['target']['final_url'] = record_safe_url(address)
                    return
                docs_count += 1
                state['navigation_id'] = f'nav-{docs_count:04d}'
                state['document_key'] = page_id + ':' + state['navigation_id'] if docs_count <= MAX_DOCUMENTS else None
                state['document_time_origin'] = document_origin
                state['last_document_url'] = url_without_hash
                if page_id == 'page-001':
                    result['target']['final_url'] = record_safe_url(address)
                if len(record['pages']) >= MAX_DOCUMENTS:
                    record['omitted_events']['documents'] += 1
                    return
                record['pages'].append({
                    'page_id': page_id, 'navigation_id': state['navigation_id'],
                    'frame_id': state['frame_id'], 'url': record_safe_url(address),
                    'allowed': in_scope})

            def document_ready():
                if origin_string(page.url) not in origins:
                    return
                try:
                    # A full navigation callback can precede an evaluable JS
                    # context; fill its token before any subsequent hash route.
                    state['document_time_origin'] = page.evaluate('performance.timeOrigin')
                except BrowserError:
                    pass
            page.on('framenavigated', navigated)
            page.on('domcontentloaded', document_ready)
            # Never block navigation callbacks while CDP initializes.
            # Attach before initial page.goto, after registering handlers.
            net.decoded_tracker.attach_page(context, page)
        context.on('page', on_page)
        page = context.new_page()
        on_page(page)
        page.set_default_timeout(int(timeout * 1000))
        try:
            response = page.goto(url, wait_until='domcontentloaded', timeout=int(timeout*1000))
            result['runtime']['domcontentloaded_observed'] = True
            if response:
                result['target']['status_code'] = response.status
                if response.status >= 400:
                    result['warnings'].append(f'HTTP {response.status}: 페이지 응답 확인 필요')
        except BrowserError:
            result['warnings'].append('초기 탐색 실패: 부분 Record 보존')
            fatal = True

        def snapshot():
            nonlocal has_iframe_warning
            # Responses must be summarized while their document is still alive.
            if net is not None:
                net.flush_completed()
            for pg, state in list(pages.items()):
                if pg.is_closed() or origin_string(pg.url) not in origins:
                    continue
                if len(pg.frames) > 1 and not has_iframe_warning:
                    has_iframe_warning = True
                    result['warnings'].append('iframe DOM/상호작용 탐지는 지원하지 않습니다. main frame만 분석')
                key = state['document_key']
                if not key:
                    continue
                try:
                    local = {'charts': [], 'runtime': {}, 'frontend': [], 'evidence': []}
                    collect_runtime_charts(pg, local)
                    for c in local['charts']:
                        chart_key = (key, c['selector'], c['library'])
                        if chart_key in seen:
                            previous_chart = seen[chart_key]
                            c['id'] = previous_chart['id']
                            # Keep a previously observed change when an SPA
                            # destroys/recreates the same structural selector.
                            previous_update = previous_chart.get('last_observed_update_ms')
                            incoming_update = c.get('last_observed_update_ms')
                            if (type(previous_update) is int and
                                    (type(incoming_update) is not int or incoming_update < previous_update)):
                                c['last_observed_update_ms'] = previous_update
                                c['change_evidence'] = previous_chart.get('change_evidence')
                        else:
                            existing_charts = [k for k in seen
                                               if isinstance(k, tuple) and len(k) == 3]
                            if len(existing_charts) >= 80:
                                if not result['runtime'].get('record_chart_limit_warning'):
                                    result['warnings'].append('Record 차트 후보 80건 상한: 신규 차트 생략')
                                    result['runtime']['record_chart_limit_warning'] = True
                                continue
                            local_count = sum(k[0] == key for k in existing_charts)
                            c['id'] = (state['page_id'] + '-' + state['navigation_id']
                                       + f'-chart-{local_count + 1:03d}')
                        c.update(page_id=state['page_id'], navigation_id=state['navigation_id'],
                                 frame_id=state['frame_id'])
                        seen[chart_key] = c
                    for item in local['runtime'].get('technologies', []):
                        if not any(t['name'] == item['name'] for t in result['runtime']['technologies']):
                            result['runtime']['technologies'].append(item)
                            eid = f"record-tech-{len(result['evidence'])+1:04d}"
                            result['evidence'].append({
                                'id': eid, 'source': 'runtime_global',
                                'key': item['name'], 'value': item['evidence'],
                                'note': '허용 범위의 런타임 기술 마커 (차트 사용 확정 아님)'})
                            result['frontend'].append({
                                'name': item['name'], 'version': item.get('version'),
                                'confidence': 0.8, 'evidence_ids': [eid]})
                except Exception as exc:
                    if 'Record 차트 스냅샷 오류:' not in result['warnings']:
                        result['warnings'].append('Record 차트 스냅샷 오류: ' + type(exc).__name__)
                try:
                    value = pg.evaluate('() => window.__fable51_interactions && window.__fable51_interactions.snapshot()')
                    if isinstance(value, dict):
                        items = value.get('items', [])
                        # JS snapshot returns full history; track a cursor per document.
                        cursor_key = (key, 'interaction_cursor')
                        previous = seen.get(cursor_key, 0)
                        for marker in items[previous:]:
                            add_marker(marker, state)
                        seen[cursor_key] = len(items)
                        dropped_key = (key, 'interaction_dropped')
                        dropped = int(value.get('dropped') or 0)
                        record['omitted_events']['interactions'] += max(0, dropped - seen.get(dropped_key, 0))
                        seen[dropped_key] = dropped
                except BrowserError:
                    pass

        # Preserve an early terminal Enter/EOF delivered during browser startup.
        if not stop.is_set():
            reason[:] = ['max_duration']
        if not fatal:
            try:
                while True:
                    if stop.is_set():
                        reason[:] = [reason[-1] if reason and reason[-1] in ('enter', 'stdin_eof', 'stdin_unavailable') else 'stop_signal']
                        break
                    if time.monotonic() - started >= max_duration:
                        reason[:] = ['max_duration']
                        break
                    live = [pg for pg in context.pages if not pg.is_closed()]
                    if not live:
                        reason[:] = ['browser_closed']
                        break
                    if test_hook is not None:
                        test_hook(context, pages, time.monotonic() - started, stop)
                    try:
                        snapshot()
                        # Playwright sync messages are serviced while waiting here.
                        live[0].wait_for_timeout(PUMP_MS)
                    except BrowserError:
                        if not [pg for pg in context.pages if not pg.is_closed()]:
                            reason[:] = ['browser_closed']
                            break
            except KeyboardInterrupt:
                reason[:] = ['ctrl_c']
        else:
            reason[:] = ['navigation_error']

        snapshot()
        result['charts'] = list(seen[k] for k in seen if isinstance(k, tuple) and len(k) == 3)[:80]
        if len([k for k in seen if isinstance(k, tuple) and len(k) == 3]) > 80:
            record['omitted_events']['documents'] += 1
            result['warnings'].append('Record 차트 후보 총량 80개 상한 적용')
        if net:
            net.finalize()
            record['omitted_events']['network'] = net.omitted
            result['runtime']['xhr_fetch_requests_seen'] = net.event_count
            result['runtime']['xhr_fetch_responses_seen'] = sum(
                r['response_received_at_ms'] is not None for r in result['api']['endpoints'])
        if conn:
            conn.finalize()
        if bundles:
            bundles.finalize(url)
            for candidate in result['api'].get('candidates', []):
                candidate['source_script'] = record_safe_url(candidate['source_script'])
        map_chart_api_candidates(result)
        if page and not page.is_closed():
            result['target']['final_url'] = record_safe_url(page.url)
    except KeyboardInterrupt:
        reason = ['ctrl_c']
    except Exception as exc:
        reason[:] = ['browser_error']
        fatal = True
        result['warnings'].append('Record 브라우저 처리 실패: ' + type(exc).__name__)
    finally:
        record['record_ended_at'] = _utc()
        record['duration_seconds'] = round(time.monotonic() - started, 3)
        record['stop_reason'] = reason[-1]
        if reason[-1] in ('stdin_eof', 'stdin_unavailable'):
            result['warnings'].append('터미널 입력 불가: 대화형 터미널에서 실행하거나 종료 신호를 제공하세요.')
            fatal = True
        for resource in (context, browser):
            if resource is not None:
                try:
                    resource.close()
                except Exception:
                    result['warnings'].append('브라우저 정리 오류')
                    fatal = True
        if playwright_instance is not None:
            try:
                playwright_instance.stop()
            except Exception:
                result['warnings'].append('Playwright 종료 오류')
                fatal = True
    return fatal
