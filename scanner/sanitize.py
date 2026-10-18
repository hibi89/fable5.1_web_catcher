"""Redaction for all externally supplied data before persistence or display."""
from __future__ import annotations

import re
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

SECRET_KEYS = re.compile(
    r"(?:token|secret|password|passwd|pwd|auth|api[_-]?key|access[_-]?key|"
    r"session|sid|jwt|signature|sig|credential|client[_-]?secret|code)", re.I,
)
_URL = re.compile(r"https?://[^\s<>\"']+", re.I)
_PAIR = re.compile(
    r"(?i)(\b(?:access_token|refresh_token|id_token|api[_-]?key|secret|password|"
    r"passwd|pwd|authorization|session(?:id)?|jwt|signature|client_secret)\b\s*[=:]\s*)"
    r"([^\s&,;\"'<>}]+)"
)
_BEARER = re.compile(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+\-/=]+")
_COOKIE_LINE = re.compile(r"(?im)\b(set-cookie|cookie|authorization)\s*:\s*[^\r\n]+")


def safe_url(url: str, max_length: int = 600) -> str:
    """Strip URL credentials and sensitive query values (not query names)."""
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        netloc = host + (f":{parts.port}" if parts.port else "")
        query = urlencode(
            [(key, "[REDACTED]" if SECRET_KEYS.search(key) else val)
             for key, val in parse_qsl(parts.query, keep_blank_values=True)],
            doseq=True, safe="[]",
        )
        result = urlunsplit((parts.scheme, netloc, parts.path, query, ""))
    except (ValueError, TypeError):
        return "[INVALID URL]"
    return result[:max_length] + ("…" if len(result) > max_length else "")


def safe_text(value: object, max_length: int = 200) -> str:
    """Mask common secret patterns and sanitize embedded URLs; keep excerpts short."""
    s = str(value)
    s = _COOKIE_LINE.sub(lambda m: m.group(1) + ": [REDACTED]", s)
    s = _BEARER.sub(lambda m: m.group(1) + " [REDACTED]", s)
    s = _URL.sub(lambda m: safe_url(m.group(0), max_length=1000), s)
    s = _PAIR.sub(lambda m: m.group(1) + "[REDACTED]", s)
    s = s.replace("\r", " ").replace("\n", " ")
    return s[:max_length] + ("…" if len(s) > max_length else "")


def request_url(url: str) -> str:
    """Remove userinfo before a request so credentials are never transmitted."""
    parts = urlsplit(url)
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        raise ValueError("HTTP 또는 HTTPS URL만 허용합니다.")
    if parts.port is not None and not (1 <= parts.port <= 65535):
        raise ValueError("URL 포트가 올바르지 않습니다.")
    host = parts.hostname
    if ":" in host:
        host = f"[{host}]"
    netloc = host + (f":{parts.port}" if parts.port else "")
    return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", parts.query, ""))
