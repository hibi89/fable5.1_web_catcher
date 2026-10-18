"""Step 5 offline I/O and minimal non-identifying observation helpers."""
from __future__ import annotations
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .models import SCHEMA_VERSION
from .llm_payload import _shape, SAFE_SEGMENTS, SAFE_FIELD_NAMES

MAX_RESULT_BYTES = 6_000_000
KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
NUMERIC = re.compile(r"^\d{1,12}$")
UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F-]{16,}$")
HUMAN = re.compile(r"(?:@|%40|[+]|\\|\.{2})")
ALLOWED_TYPES = {"string", "number", "integer", "boolean", "null", "unknown", "truncated"}


def read_result(path: Path):
    if not path.is_file() or path.stat().st_size > MAX_RESULT_BYTES:
        raise ValueError("결과 파일이 없거나 크기가 6MB를 초과합니다.")
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeError, OSError, ValueError) as exc:
        raise ValueError("JSON 파일 파싱에 실패했습니다.") from exc
    if not isinstance(obj, dict):
        raise ValueError("결과 최상위 객체가 유효하지 않습니다.")
    version = obj.get("schema_version")
    if version not in (None, SCHEMA_VERSION):
        raise ValueError("지원하지 않는 schema_version: 기존 1.0 또는 구버전 누락만 허용합니다.")
    for field in ("frontend", "backend_inferred", "infra", "charts", "evidence", "warnings"):
        if field in obj and not isinstance(obj[field], list):
            raise ValueError("결과 필드 타입 불일치")
    if "api" in obj and (not isinstance(obj["api"], dict)
                         or not isinstance(obj["api"].get("endpoints", []), list)):
        raise ValueError("API 필드 타입 불일치")
    return obj


def atomic_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name("." + path.name + ".tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def atomic_text(path: Path, data: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name("." + path.name + ".tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def new_directory(path: Path):
    # Refuse silent overwrite even if a directory exists but is empty.
    if path.exists():
        raise ValueError("출력 디렉터리가 이미 있습니다. 다른 --out 경로를 지정하세요.")
    path.mkdir(parents=True, exist_ok=False)


def markdown(value):
    text = str(value)[:200]
    text = re.sub(r"[^\w가-힣 .:/-]", "_", text)
    return text.replace("|", "_").replace("\n", " ").replace("\r", " ")


def masked_field(key):
    if isinstance(key, str) and key.lower() in (SAFE_FIELD_NAMES | {"empty", "deep", "layer", "nested"}):
        return key.lower()
    return "field_unknown"


def path_key(url):
    """Join endpoints only on identical original origin, not display alias."""
    try:
        p = urlsplit(url)
        if p.scheme.lower() not in ("http", "https") or not p.hostname:
            return None
        origin = (p.scheme.lower(), p.hostname.lower(), p.port)
        chunks = [x for x in p.path.split("/") if x]
        parts = []
        for word in chunks[:12]:
            if NUMERIC.fullmatch(word) or UUID.fullmatch(word):
                parts.append(":id")
            elif word.lower() in SAFE_SEGMENTS:
                parts.append(word.lower())
            else:
                parts.append(":segment")
        return origin, "/" + "/".join(parts)
    except (TypeError, ValueError):
        return None


def anonymous_path(url, *, origin="site"):
    key = path_key(url)
    if key is None:
        return "unknown"
    return origin + key[1]


def source_identity(result):
    target = result.get("target", {})
    if not isinstance(target, dict):
        return None
    url = target.get("input_url") or target.get("final_url")
    if not isinstance(url, str):
        return None
    try:
        p = urlsplit(url)
        if p.scheme.lower() not in ("http", "https") or not p.hostname:
            return None
        # A redacted URL may collide with an unredacted one. Don't assert
        # same-site identity from it when any uncertainty exists.
        if "[REDACTED]" in url or "…" in url or p.hostname.lower().endswith(".batch.invalid"):
            return None
        return (p.scheme.lower(), p.hostname.lower(), p.port,
                p.path or "/", p.query)
    except ValueError:
        return None


def normalized_batch_url(url):
    # Preserve ordered query and path exactly. Remove only fragment and userinfo.
    from .sanitize import request_url
    return request_url(url)


def safe_batch_url(url, origin_alias):
    """An ephemeral non-reversible alias. Never persist the real host."""
    return anonymous_path(url, origin=origin_alias)


def privacy_summary(result):
    from .models import CATEGORIES
    found = {}
    for category in CATEGORIES:
        entries = result.get(category, [])
        found[category] = sorted({
            str(x.get("name"))[:55] for x in entries
            if isinstance(x, dict) and isinstance(x.get("name"), str)
            and x["name"] not in ("", "unknown")
            and x["name"].isascii() and all(c.isalnum() or c in " .+-#" for c in x["name"])
        })[:15]
    return {
        "technologies": found,
        "api_count": len(result.get("api", {}).get("endpoints", [])),
        "chart_count": len(result.get("charts", [])),
        "warning_count": len(result.get("warnings", [])),
    }


def safe_structure(shape, depth=0):
    """Value-free old/new shape summary preserving integer and unknown types."""
    if depth >= 7:
        return "truncated"
    if isinstance(shape, str):
        return shape if shape in ALLOWED_TYPES else "unknown"
    if isinstance(shape, list):
        return [safe_structure(x, depth+1) for x in shape[:3]]
    if isinstance(shape, dict):
        result = {}
        for k, v in list(shape.items())[:24]:
            safe = masked_field(k)
            if safe in result:
                # Redacted keys may collapse; never pretend the last won.
                prior = result[safe]
                result[safe] = prior if prior == safe_structure(v, depth+1) else "unknown"
            else:
                result[safe] = safe_structure(v, depth+1)
        return result
    return "unknown"


def safe_error(kind):
    return kind if kind in {"scan_failed", "blocked_403", "rate_limited_429",
                            "invalid_url", "missing_result", "interrupted",
                            "origin_rate_limited", "batch_limit"} else "scan_failed"
