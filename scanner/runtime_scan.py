"""Isolated Chromium runtime navigation scaffold (Step 2, unit 1).

Network payload inspection, library detection and chart mapping are deliberately
not enabled here. Subsequent units extend this browser observation boundary.
"""
from __future__ import annotations

from urllib.parse import urlsplit

from .sanitize import safe_url

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
        'scope': 'navigation_only',
        'xhr_fetch_requests_seen': 0,
        'xhr_fetch_responses_seen': 0,
    }
    warnings.append('Step 2 부분 구현: API 요청·차트·런타임 기술 탐지는 아직 수집하지 않습니다.')
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
                def observed_request(request):
                    if request.resource_type in ('fetch', 'xhr'):
                        result['runtime']['xhr_fetch_requests_seen'] += 1

                def observed_response(response):
                    if response.request.resource_type in ('fetch', 'xhr'):
                        result['runtime']['xhr_fetch_responses_seen'] += 1

                page.on('request', observed_request)
                page.on('response', observed_response)
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
