"""Isolated Chromium runtime navigation scaffold (Step 2, unit 1).

Observed XHR/fetch and WebSocket/SSE connection metadata are enabled.
Known runtime library markers and DOM chart candidates are enabled.
Conservative chart-to-API hypotheses and passive observed JS literal scan enabled.
"""
from __future__ import annotations

from urllib.parse import urlsplit

from .sanitize import safe_url
from .network import NetworkCollector
from .connections import ConnectionCollector
from .runtime_detect import CHART_OBSERVER_SCRIPT, collect_runtime_charts
from .chart_mapping import map_chart_api_candidates
from .bundle_scan import BundleCollector

# Installed by Playwright BEFORE navigation, to observe page timings only.
# No site state, forms, cookies, or storage are changed by this script.
_INIT_OBSERVER = """(() => {
  const seen = {dom_ready_ms: null};
  Object.defineProperty(window, '__fable51_observation', {
    value: seen, configurable: true, enumerable: false
  });
  document.addEventListener('DOMContentLoaded', () => {
    seen.dom_ready_ms = performance.timeOrigin + performance.now();
  }, {once: true});
})();"""


def _script_urls(page, selector: str, attribute: str) -> list[str]:
    """Read only already-present resource URLs; never fetch new paths."""
    try:
        raw = page.locator(selector).evaluate_all(
            "(nodes, attr) => nodes.slice(0, 100).map(el => el[attr] || '')", attribute
        )
        return sorted({safe_url(u) for u in raw if isinstance(u, str) and urlsplit(u).scheme in ('http', 'https')})[:100]
    except Exception:
        return []


def _bounded_wait(page, seconds: float) -> int:
    """Pump browser events and make at most two read-only scroll observations."""
    milliseconds = round(seconds * 1000)
    if milliseconds <= 0:
        return 0
    slices = 2 if milliseconds >= 2 else 1
    scrolled = 0
    spent = 0
    for index in range(slices):
        portion = (milliseconds - spent) // (slices - index)
        page.wait_for_timeout(portion)
        spent += portion
        try:
            page.evaluate('window.scrollBy(0, Math.min(window.innerHeight, 600))')
            scrolled += 1
        except Exception:
            pass
    if milliseconds > spent:
        page.wait_for_timeout(milliseconds - spent)
    return scrolled


def scan_runtime_page(url: str, result: dict, *, timeout: float, wait: float, headed: bool) -> bool:
    """Navigate once and preserve partial evidence on errors. Returns fatal flag."""
    warnings = result['warnings']
    result['runtime'] = {
        'domcontentloaded_observed': False,
        'wait_seconds': wait,
        'scroll_steps': 0,
        'scope': 'network_and_connections_metadata',
        'xhr_fetch_requests_seen': 0,
        'xhr_fetch_responses_seen': 0,
    }
    try:
        from playwright.sync_api import Error as BrowserError
        from playwright.sync_api import TimeoutError as BrowserTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError:
        warnings.append('Playwright 미설치: pip install -r requirements.txt')
        return True

    browser = None
    context = None
    page = None
    fatal = False
    try:
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=not headed)
                context = browser.new_context(accept_downloads=False, ignore_https_errors=False)
                page = context.new_page()
                page.set_default_timeout(int(timeout * 1000))
                # Register before any navigation, including redirect and early events.
                page.add_init_script(_INIT_OBSERVER)
                page.add_init_script(CHART_OBSERVER_SCRIPT)
                network = NetworkCollector(result)
                connections = ConnectionCollector(result)
                bundles = BundleCollector(result)
                network.attach(page)
                connections.attach(page)
                bundles.attach(page)
                try:
                    response = page.goto(url, wait_until='domcontentloaded', timeout=int(timeout * 1000))
                    result['runtime']['domcontentloaded_observed'] = True
                    if response is not None:
                        result['target']['status_code'] = response.status
                        if response.status >= 400:
                            warnings.append(f'HTTP {response.status}: 페이지 요청 실패')
                            fatal = True
                    result['runtime']['scroll_steps'] = _bounded_wait(page, wait)
                except BrowserTimeoutError:
                    warnings.append('브라우저 DOMContentLoaded 대기 시간 초과: 부분 결과 보존')
                    fatal = True
                except BrowserError:
                    warnings.append('브라우저 탐색 오류: 부분 결과 보존')
                    fatal = True
                finally:
                    try:
                        if page and urlsplit(page.url).scheme in ('http', 'https'):
                            result['target']['final_url'] = safe_url(page.url)
                            result['target']['scripts'] = _script_urls(page, 'script[src]', 'src')
                            result['target']['stylesheets'] = _script_urls(page, 'link[rel~=stylesheet][href]', 'href')
                    except Exception:
                        warnings.append('브라우저 DOM 일부 메타데이터 조회 실패')
                    try:
                        if page:
                            collect_runtime_charts(page, result)
                    except Exception:
                        warnings.append('차트 DOM/런타임 증거 조회 실패: 기존 부분 결과 보존')
                    try:
                        network.finalize()
                        result['runtime']['xhr_fetch_requests_seen'] = len(result['api']['endpoints'])
                        result['runtime']['xhr_fetch_responses_seen'] = sum(
                            item['response_received_at_ms'] is not None for item in result['api']['endpoints']
                        )
                    except Exception:
                        warnings.append('네트워크 응답 구조 분석 오류: 기록된 endpoint만 보존')
                    try:
                        connections.finalize()
                    except Exception:
                        warnings.append('연결 관찰 마무리 오류: 기록된 연결만 보존')
                    try:
                        bundles.finalize(page.url if page else url)
                    except Exception:
                        warnings.append('번들 문자열 분석 오류: 이전 부분 결과 보존')
                    try:
                        map_chart_api_candidates(result)
                    except Exception:
                        warnings.append('차트↔API 후보 계산 실패: 관찰된 데이터만 보존')
            except BrowserError:
                warnings.append('Chromium 실행 실패: python -m playwright install chromium 명령으로 설치를 확인하세요.')
                fatal = True
            finally:
                # Close context before browser; cleanup errors cannot discard results.
                for resource in (context, browser):
                    if resource is not None:
                        try:
                            resource.close()
                        except Exception:
                            warnings.append('브라우저 자원 정리 실패: 환경을 확인하세요.')
                            fatal = True
    except Exception:
        warnings.append('브라우저 초기화 오류: 부분 결과 보존')
        fatal = True
    return fatal
