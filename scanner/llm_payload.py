"""Step 4 outbound-data allowlist. Never forward result.json to any model.

Everything in a scan can be adversarial. No URL, raw evidence value, free-form
warning, page script, cookie, form input or subject host crosses this boundary.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from .models import CATEGORIES

PAYLOAD_SCHEMA_VERSION = "step4-payload-1"
MAX_BYTES = 28_000
MAX_EVIDENCE = 45
MAX_FINDINGS = 35
MAX_ENDPOINTS = 24
MAX_CHARTS = 16
MAX_CANDIDATES = 20
MAX_WARNINGS = 12
ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,72}$")
NUMERIC = re.compile(r"^\d{1,12}$")
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f-]{16,}$", re.I)
SAFE_SEGMENTS = frozenset("api v1 v2 v3 v4 graphql gql data chart charts series report reports stats summary dashboard metrics search trend trends time daily weekly monthly users posts products categories items analytics list public client assets json".split())
SAFE_FIELD_NAMES = frozenset("items item id date datetime timestamp time label labels value values count total name category type color colors series data points x y size unit status result results summary trend country region language year month week day price rate score likes comments followers metric metrics title created_at updated_at page pages limit offset next previous payload success message error code rows columns datasets labels length detail information technique texture motif season use design post media engagement".split())
SAFE_EVIDENCE_MARKERS = frozenset("next_data next_root nuxt_data nuxt_payload vue_mount angular_version angular_app react_root".split())
SAFE_EVIDENCE_SOURCES = frozenset("html response_header cookie_name meta_generator script_src stylesheet_href csp_domain runtime_global".split())
SAFE_LIBRARIES = frozenset("unknown echarts highcharts chart.js chartjs d3 d3.js plotly apexcharts recharts vue react angular".split())
SAFE_MIMES = frozenset(("application/json", "application/graphql", "text/event-stream", "application/problem+json", "application/ld+json"))
SAFE_METHODS = frozenset(("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"))


def _id(value):
    return value if isinstance(value, str) and ID_RE.fullmatch(value) else None


def _score(value):
    return round(value, 3) if type(value) in (float, int) and 0 <= value <= 1 else 0.0


def _version(value):
    return value if isinstance(value, str) and re.fullmatch(r"\d+(?:\.\d+){0,5}", value) else None


def _shape(value, depth=0):
    if depth >= 5:
        return "truncated"
    if isinstance(value, str):
        return value if value in ("string", "number", "boolean", "null", "unknown", "truncated") else "unknown"
    if isinstance(value, list):
        return [_shape(v, depth + 1) for v in value[:3]]
    if isinstance(value, dict):
        out = {}
        for n, (k, v) in enumerate(list(value.items())[:24]):
            # Key names can themselves be private persons' names or emails.
            name = k if type(k) is str and k.lower() in SAFE_FIELD_NAMES else "field_" + str(n + 1)
            if name in out:
                continue
            out[name] = _shape(v, depth + 1)
        return out
    return "unknown"


def _path(url, origins):
    try:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            return "origin_unknown/:path"
        host = (parts.hostname.lower(), parts.port)
        if host not in origins:
            origins[host] = "origin_" + str(len(origins) + 1)
        segments = [x for x in parts.path.split("/") if x][:9]
        normalized = []
        for seg in segments:
            word = seg.lower()
            if word in SAFE_SEGMENTS:
                normalized.append(word)
            elif NUMERIC.fullmatch(word) or UUID.fullmatch(word):
                normalized.append(":id")
            else:
                normalized.append(":segment")
        return origins[host] + "/" + "/".join(normalized)
    except (TypeError, ValueError):
        return "origin_unknown/:path"


def _catalog():
    file = Path(__file__).resolve().parent.parent / "rules" / "fingerprints.json"
    return {t["name"] for t in json.loads(file.read_text(encoding="utf-8"))["technologies"]}


def build_llm_payload(result: dict) -> dict:
    """Produce a new JSON-safe object built entirely from known field names."""
    if not isinstance(result, dict):
        raise ValueError("result.json must be a JSON object")
    allowed_names = _catalog()
    ev_index = {}
    evidence = []
    omissions = {"evidence": 0, "duplicate_evidence": 0,
                 "findings": 0, "endpoints": 0,
                 "charts": 0, "chart_api_candidates": 0}
    # Prioritize evidence cited by a finding, then deterministic structural
    # evidence; this avoids wasting the 45-entry budget on unreferenced noise.
    referenced = {eid for category in CATEGORIES
                  for finding in result.get(category, [])
                  if isinstance(finding, dict)
                  for eid in finding.get("evidence_ids", [])
                  if type(eid) is str}
    priority = {"html": 0, "meta_generator": 1, "response_header": 2,
                "cookie_name": 3, "script_src": 4,
                "stylesheet_href": 5, "runtime_global": 6, "csp_domain": 7}
    entries = [x for x in result.get("evidence", []) if isinstance(x, dict)]
    entries.sort(key=lambda x: (x.get("id") not in referenced,
                                priority.get(x.get("source"), 99)))
    duplicate_signatures = {}
    for raw in entries:
        if not isinstance(raw, dict):
            omissions["evidence"] += 1
            continue
        orig = _id(raw.get("id"))
        source = raw.get("source")
        if not orig or orig in ev_index or source not in SAFE_EVIDENCE_SOURCES:
            omissions["evidence"] += 1
            continue
        marker = raw.get("value")
        marker = marker if type(marker) is str and marker in SAFE_EVIDENCE_MARKERS else None
        key = raw.get("key")
        key = key.lower() if type(key) is str and key.lower() in SAFE_FIELD_NAMES else "redacted"
        signature = (source, key, marker)
        if signature in duplicate_signatures:
            ev_index[orig] = duplicate_signatures[signature]
            omissions["duplicate_evidence"] += 1
            continue
        if len(evidence) >= MAX_EVIDENCE:
            omissions["evidence"] += 1
            continue
        eid = "e" + str(len(evidence) + 1).zfill(3)
        ev_index[orig] = eid
        duplicate_signatures[signature] = eid
        evidence.append({"id": eid, "source": source, "key": key,
                         "structural_marker": marker})
    findings = []
    for cat in CATEGORIES:
        for raw in result.get(cat, []):
            if not isinstance(raw, dict) or raw.get("name") not in allowed_names:
                continue
            refs = [ev_index[x] for x in raw.get("evidence_ids", [])
                    if type(x) is str and x in ev_index]
            if not refs:
                omissions["findings"] += 1
                continue
            if len(findings) >= MAX_FINDINGS:
                omissions["findings"] += 1
                continue
            findings.append({"id": "f" + str(len(findings)+1).zfill(3),
                             "name": raw["name"], "category": cat,
                             "confidence": _score(raw.get("confidence")),
                             "version": _version(raw.get("version")),
                             "evidence_ids": list(dict.fromkeys(refs))[:15]})
    origins = {}
    endpoints, end_ids = [], {}
    for raw in result.get("api", {}).get("endpoints", []):
        if not isinstance(raw, dict) or not _id(raw.get("id")):
            omissions["endpoints"] += 1
            continue
        if len(endpoints) >= MAX_ENDPOINTS:
            omissions["endpoints"] += 1
            continue
        endpoint_id = "a" + str(len(endpoints)+1).zfill(3)
        end_ids[raw["id"]] = endpoint_id
        method = raw.get("method")
        status = raw.get("status")
        mime = raw.get("content_type")
        status = status if type(status) is int and 100 <= status <= 599 else None
        mime = mime if mime in SAFE_MIMES else "unknown"
        shape = _shape(raw.get("json_structure")) if raw.get("json_structure") is not None else None
        prefix = raw.get("json_prefix_structure")
        partial = (_shape(prefix.get("fields"))
                   if isinstance(prefix, dict)
                   and prefix.get("completeness") == "partial_prefix_only" else None)
        endpoints.append({"id": endpoint_id, "path": _path(raw.get("url"), origins),
                          "method": method if method in SAFE_METHODS else "unknown",
                          "status": status, "content_type": mime,
                          "json_structure": shape, "partial_prefix_fields": partial})
    charts, chart_ids = [], {}
    for raw in result.get("charts", []):
        if not isinstance(raw, dict) or not _id(raw.get("id")):
            omissions["charts"] += 1
            continue
        if len(charts) >= MAX_CHARTS:
            omissions["charts"] += 1
            continue
        chart_id = "c" + str(len(charts)+1).zfill(3)
        chart_ids[raw["id"]] = chart_id
        library = str(raw.get("library", "unknown")).lower()
        charts.append({"id": chart_id,
                       "library": library if library in SAFE_LIBRARIES else "unknown",
                       "confidence": _score(raw.get("detection_confidence")),
                       "updated": type(raw.get("last_observed_update_ms")) is int,
                       "data_source_observed": bool(raw.get("data_sources"))})
    mapped = []
    for raw in result.get("api", {}).get("chart_candidates", []):
        if not isinstance(raw, dict):
            continue
        ci = chart_ids.get(raw.get("chart_id"))
        ai = end_ids.get(raw.get("endpoint_id"))
        if not ci or not ai or len(mapped) >= MAX_CANDIDATES:
            omissions["chart_api_candidates"] += 1
            continue
        delta = raw.get("time_delta_ms")
        delta = delta if type(delta) is int and 0 <= delta <= 600_000 else None
        mapped.append({"chart_id": ci, "endpoint_id": ai,
                       "confidence": _score(raw.get("confidence")),
                       "time_delta_ms": delta,
                       "status": "hypothesis_only"})
    warning_count = min(999, len(result.get("warnings", [])))
    payload = {"payload_schema_version": PAYLOAD_SCHEMA_VERSION,
               "scan_mode": result.get("scan_mode") if result.get("scan_mode") in ("static", "runtime", "record") else "unknown",
               "findings": findings, "evidence": evidence, "api_endpoints": endpoints,
               "charts": charts, "chart_api_candidates": mapped,
               "warnings": ["원본 경고 " + str(warning_count) + "건 (값 미전송)"] if warning_count else [],
               "omissions": omissions,
               "omission_reasons": {
                   "evidence": "invalid source/ID or max 45 allowed",
                   "duplicate_evidence": "same sanitized evidence source/key/marker",
                   "findings": "no allowed evidence or max 35",
                   "endpoints": "invalid identifier or max 24",
                   "charts": "invalid identifier or max 16",
                   "chart_api_candidates": "unreferenced pair or max 20",
               },
               "limitations": ["한 페이지에서 관찰된 부분 단서이며 실제 서버 코드/DB를 확인한 것이 아닙니다.",
                               "부분 JSON 구조는 첫 표본 객체이며 전체 스키마를 의미하지 않습니다.",
                               "confidence는 기존 엔진의 휴리스틱 점수이고 확률이 아닙니다.",
                               "차트와 API는 인과 관계가 아닌 연관 후보입니다."]}
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > MAX_BYTES:
        raise ValueError("sanitized payload exceeds bound; reduce scan input first")
    return payload
