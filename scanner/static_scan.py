"""Bounded, read-only GET of precisely one public page and its redirects."""
from __future__ import annotations

import re
from http.cookies import SimpleCookie
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from .sanitize import request_url, safe_text, safe_url

ALLOWED_HEADERS = frozenset({
    "server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version",
    "cf-ray", "cf-cache-status", "x-vercel-id", "x-nf-request-id",
    "content-type", "via", "x-served-by",
})
MAX_REDIRECTS = 5
MAX_HTML_BYTES = 2_000_000
MAX_ITEMS = 100
MAX_CSP_DOMAINS = 60
HTML_MARKERS = (
    # Recognize structural markers, never generic page text.
    ("next_data", re.compile(r"<script\b[^>]*\bid\s*=\s*['\"]__NEXT_DATA__['\"]", re.I)),
    ("next_root", re.compile(r"<[^>]+\bid\s*=\s*['\"]__next['\"]", re.I)),
    ("nuxt_data", re.compile(r"\b(?:id|data-nuxt)\s*=\s*['\"]__nuxt['\"]", re.I)),
    ("nuxt_payload", re.compile(r"(?:window\.)?__NUXT__\s*=", re.I)),
    ("vue_mount", re.compile(r"\bdata-v-app(?:\s|=|>)", re.I)),
    ("angular_version", re.compile(r"\bng-version\s*=\s*['\"][\d.]+['\"]", re.I)),
    ("angular_app", re.compile(r"\bng-app\s*=", re.I)),
    ("react_root", re.compile(r"\bdata-reactroot(?:\s|=|>)", re.I)),
)
_CSP_DOMAIN = re.compile(r"(?i)(?:https?://)?(?:\*\.)?([a-z0-9][a-z0-9.-]*\.[a-z]{2,})(?::\d+)?")


def cookie_names(response: requests.Response) -> list[str]:
    # Multiple Set-Cookie headers should be processed separately.
    raw = response.raw.headers
    headers = raw.getlist("Set-Cookie") if hasattr(raw, "getlist") else []
    names: set[str] = set()
    for header in headers:
        match = re.match(r"\s*([A-Za-z0-9_!#$%&'*+.^`|~-]+)\s*=", header)
        if match:
            names.add(match.group(1)[:100])
    return sorted(names)


def _csp_domains(response: requests.Response) -> list[str]:
    values = [response.headers.get("Content-Security-Policy", ""),
              response.headers.get("Content-Security-Policy-Report-Only", "")]
    return sorted({m.group(1).lower() for val in values for m in _CSP_DOMAIN.finditer(val)})[:MAX_CSP_DOMAINS]


def _html_features(html: str) -> list[str]:
    return sorted({name for name, pattern in HTML_MARKERS if pattern.search(html)})


def _collect_html(html: str, final_url: str, target: dict) -> dict[str, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    generator = sorted({safe_text(tag.get("content", ""), 150) for tag in
                        soup.select("meta[name]")
                        if tag.get("name", "").strip().lower() == "generator" and tag.get("content")})[:MAX_ITEMS]
    scripts = sorted({safe_url(urljoin(final_url, tag["src"])) for tag in soup.find_all("script", src=True)
                      if tag.get("src", "").strip()})[:MAX_ITEMS]
    styles = sorted({safe_url(urljoin(final_url, tag["href"])) for tag in soup.find_all("link", href=True)
                     if "stylesheet" in [str(x).lower() for x in tag.get("rel", [])]})[:MAX_ITEMS]
    features = _html_features(html)
    target.update(meta_generator=generator, scripts=scripts, stylesheets=styles)
    return {"html": features, "meta_generator": generator, "script_src": scripts,
            "stylesheet_href": styles}


def scan_page(url: str, target: dict, warnings: list[str], timeout: float = 10,
              max_redirects: int = MAX_REDIRECTS,
              max_html_bytes: int = MAX_HTML_BYTES) -> tuple[dict[str, object], bool]:
    """Return (fingerprinting observations, fatal load failure).

    No follow-up URL discovery, credential transmission, probing, or persistent HTML.
    """
    current = request_url(url)
    observations: dict[str, object] = {}
    session = requests.Session()
    session.headers.update({"User-Agent": "FableWebCatcher/1.0 (single-page read-only)"})
    try:
        for hop in range(max_redirects + 1):
            try:
                with session.get(current, timeout=(timeout, timeout), stream=True,
                                 allow_redirects=False, verify=True) as response:
                    status = response.status_code
                    target["final_url"] = safe_url(response.url)
                    target["status_code"] = status
                    target["response_headers"] = {
                        key.lower(): safe_text(value, 200)
                        for key, value in response.headers.items() if key.lower() in ALLOWED_HEADERS
                    }
                    target["cookie_names"] = cookie_names(response)
                    target["csp_domains"] = _csp_domains(response)
                    observations["response_header"] = target["response_headers"]
                    observations["cookie_name"] = target["cookie_names"]
                    observations["csp_domain"] = target["csp_domains"]

                    if 300 <= status < 400 and response.headers.get("Location"):
                        if hop >= max_redirects:
                            warnings.append(f"리다이렉트 상한({max_redirects}회) 초과")
                            return observations, True
                        next_url = urljoin(current, response.headers["Location"])
                        try:
                            current = request_url(next_url)
                        except ValueError:
                            warnings.append("허용하지 않는 리다이렉트 주소")
                            return observations, True
                        target["redirect_chain"].append({"status_code": status,
                                                          "url": safe_url(response.url),
                                                          "location": safe_url(current)})
                        continue

                    if status in (403, 429):
                        warnings.append(f"HTTP {status}: 요청 제한 또는 접근 차단 가능성")
                    elif status >= 400:
                        warnings.append(f"HTTP {status}: 페이지 요청 실패")
                    content_type = response.headers.get("Content-Type", "")
                    if "text/html" not in content_type.lower() and "application/xhtml+xml" not in content_type.lower():
                        warnings.append("응답의 Content-Type이 HTML이 아닙니다. HTML 분석을 생략합니다.")
                        return observations, status >= 400
                    try:
                        size = int(response.headers.get("Content-Length", "0"))
                    except ValueError:
                        size = 0
                    if size > max_html_bytes:
                        warnings.append("HTML 다운로드 크기 상한 초과: 본문 분석을 생략합니다.")
                        return observations, status >= 400
                    blocks: list[bytes] = []
                    total = 0
                    for block in response.iter_content(chunk_size=16_384):
                        if not block:
                            continue
                        total += len(block)
                        if total > max_html_bytes:
                            warnings.append("HTML 다운로드 크기 상한 초과: 본문 분석을 생략합니다.")
                            return observations, status >= 400
                        blocks.append(block)
                    encoding = response.encoding or "utf-8"
                    html = b"".join(blocks).decode(encoding, errors="replace")
                    try:
                        observations.update(_collect_html(html, response.url, target))
                    except Exception:
                        # Parser failures are nonfatal: header/cookie evidence survives.
                        warnings.append("HTML 구조 분석 오류: 헤더 및 쿠키 근거만 사용했습니다.")
                    if re.search(r"(?i)<title[^>]*>[^<]*(?:access denied|just a moment|"
                                 r"attention required|captcha|request blocked)[^<]*</title>", html):
                        warnings.append("차단 또는 봇 검증 페이지로 의심됩니다.")
                    return observations, status >= 400
            except requests.exceptions.Timeout:
                warnings.append("요청 시간 초과")
                return observations, True
            except requests.exceptions.SSLError:
                warnings.append("TLS 인증서 검증 실패")
                return observations, True
            except requests.exceptions.RequestException:
                # Never stringify the exception: its URL may include secrets.
                warnings.append("네트워크 또는 HTTP 연결 오류")
                return observations, True
    finally:
        session.close()
    warnings.append("리다이렉트 처리 오류")
    return observations, True
