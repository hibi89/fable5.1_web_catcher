"""Observed-only reference JSON Schemas; never official server contracts."""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path

from .step5_common import (read_result, new_directory, atomic_json, atomic_text,
                           path_key, safe_structure, masked_field)

DRAFT = "https://json-schema.org/draft/2020-12/schema"
KNOWN_TYPES = {"object", "array", "string", "number", "integer", "boolean", "null"}
TIME_WORDS = {"date", "time", "timestamp", "datetime", "created_at", "updated_at",
              "year", "month", "week", "day"}


def shape_schema(shape, depth=0):
    """One value-free legacy observation. No required/additionalProperties:false."""
    if depth >= 9 or shape in ("truncated", "unknown"):
        return {}
    if isinstance(shape, str):
        return {"type": shape} if shape in KNOWN_TYPES else {}
    if isinstance(shape, list):
        if not shape:
            return {"type": "array", "items": {},
                    "description": "빈 배열만 관찰했거나 요소 타입을 확인하지 못했습니다."}
        return {"type": "array", "items": merge_schema([
            shape_schema(s, depth+1) for s in shape[:3]
        ])}
    if isinstance(shape, dict):
        props = {}
        for key, val in list(shape.items())[:24]:
            safe = masked_field(key) if isinstance(key, str) else "field_unknown"
            if safe in props:
                props[safe] = merge_schema([props[safe], shape_schema(val, depth+1)])
            else:
                props[safe] = shape_schema(val, depth+1)
        return {"type": "object", "properties": props}
    return {}


def merge_schema(schemas):
    """Evidence-driven union; unknown/empty observations cannot narrow types."""
    schemas = [s for s in schemas if isinstance(s, dict)]
    if not schemas or any(not s for s in schemas):
        return {}
    types = set()
    variants = []
    for s in schemas:
        if "anyOf" in s:
            variants.extend(s["anyOf"])
        else:
            variants.append(s)
    if len({s.get("type") for s in variants}) == 1:
        kind = variants[0].get("type")
        if kind == "object":
            fields = defaultdict(list)
            for s in variants:
                for k,v in s.get("properties", {}).items():
                    fields[k].append(v)
            # Properties observed in any sample remain *optional*; absence
            # counts are never inferred from old shape summaries.
            return {"type": "object",
                    "properties": {k: merge_schema(v) for k, v in sorted(fields.items())}}
        if kind == "array":
            return {"type": "array", "items": merge_schema([s.get("items", {}) for s in variants])}
        if kind:
            return {"type": kind}
    dedup = {}
    for s in variants:
        dedup[repr(s)] = s
    if len(dedup) == 1:
        return next(iter(dedup.values()))
    # Distinguish null from other types and mixed observed numeric types.
    return {"anyOf": list(dedup.values())[:12]}


def _field_candidates(schema, current="$", depth=0):
    out = {"array": [], "string": [], "number": [], "time_name": []}
    if depth > 7 or not isinstance(schema, dict):
        return out
    variants = schema.get("anyOf")
    if variants:
        for v in variants:
            child = _field_candidates(v, current, depth+1)
            for k in out:
                out[k].extend(child[k])
    typ = schema.get("type")
    if typ == "array":
        out["array"].append(current)
        child = _field_candidates(schema.get("items"), current+"[]", depth+1)
        for k in out:
            out[k].extend(child[k])
    if typ == "object":
        for k,v in schema.get("properties", {}).items():
            path = current+"."+k
            child = _field_candidates(v, path, depth+1)
            for name in out:
                out[name].extend(child[name])
            if k.lower() in TIME_WORDS:
                out["time_name"].append(path)
    if typ == "string":
        out["string"].append(current)
    if typ in ("integer","number"):
        out["number"].append(current)
    return {k: sorted(set(v))[:18] for k,v in out.items()}


def collect_contracts(result):
    groups = defaultdict(list)
    notes = []
    endpoints = result.get("api", {}).get("endpoints", [])
    for endpoint in endpoints:
        if not isinstance(endpoint, dict):
            continue
        key = path_key(endpoint.get("url"))
        if key is None:
            notes.append("경로 확인 불가: 구조 병합 제외")
            continue
        method = endpoint.get("method", "unknown")
        status = endpoint.get("status") if type(endpoint.get("status")) is int else None
        mime = endpoint.get("content_type")
        if mime not in ("application/json", "application/problem+json",
                        "application/graphql", "application/ld+json"):
            mime = "unknown"
        shape = endpoint.get("json_structure")
        prefix = endpoint.get("json_prefix_structure")
        shape = safe_structure(shape) if shape is not None else None
        groups[(key, method, status, mime)].append({
            "shape": shape,
            "partial_hint": isinstance(prefix, dict) and
                            prefix.get("completeness") == "partial_prefix_only",
            "analysis": endpoint.get("response_body_analysis", "unknown"),
            "evidence_id": endpoint.get("id") if isinstance(endpoint.get("id"), str)
                           and endpoint["id"].startswith("api-") else None,
        })
    entries = []
    for (origin_path, method, status, mime), samples in sorted(groups.items(), key=lambda x:repr(x[0])):
        origin, normalized_path = origin_path
        shapes = [s["shape"] for s in samples if s["shape"] is not None]
        # Only *full* observed structure allowed. Prefix hints never promoted.
        schema = merge_schema([shape_schema(s) for s in shapes]) if shapes else None
        identifier = "endpoint-" + str(len(entries)+1).zfill(3)
        entries.append({
            "endpoint_id": identifier, "path": "origin_observed" + normalized_path,
            "method": method if method in ("GET","POST","PUT","PATCH","DELETE") else "unknown",
            "status": status, "content_type": mime,
            "sample_count": len(samples),
            "structure_samples": len(shapes),
            "presence_frequencies": "unknown_in_legacy_results",
            "omitted_samples": len(samples) - len(shapes),
            "body_analysis_statuses": sorted({
                s["analysis"] for s in samples if isinstance(s["analysis"], str)
                and s["analysis"] in (
                    "structure_only", "decoded_too_large", "size_unknown",
                    "compressed_decoded_unavailable", "body_read_limit",
                    "too_large", "invalid_json", "non_json", "truncated", "ready"
                )}),
            "query_variants": "unknown; path/query conditions may change response",
            "source_evidence_ids": sorted({s["evidence_id"] for s in samples
                                            if s["evidence_id"]})[:30],
            "schema_available": schema is not None,
            "type_uncertainty": [
                "관찰 구조는 표본 타입만 표현하며 서버 required/validation을 확인하지 않았습니다.",
                "빈 배열은 요소 타입 unknown, null 단독은 다른 타입 unknown입니다.",
                "요약 표본 밖의 필드와 응답 변형이 존재할 수 있습니다."
            ],
            "schema": schema,
            "candidates": _field_candidates(schema) if schema is not None else None,
        })
    return {
        "schema_version": "contracts-1", "json_schema_draft": DRAFT,
        "notice": "관찰 기반 참고 계약. 서버 공식 OpenAPI/JSON Schema/validation 규칙이 아닙니다.",
        "endpoint_count": len(entries), "endpoints": entries,
        "limitations": notes + [
            "데이터 값, enum, default, examples, 숫자 범위, date format, 통화/단위는 추론하지 않습니다.",
            "표본에 항상 나온 필드도 실제 서버 required로 간주하지 않습니다.",
            "부분 prefix 구조와 크기 제한 응답은 전체 스키마로 변환하지 않습니다.",
        ],
    }


def as_json_schema(entry):
    observation = entry.get("schema")
    if observation is None:
        return None
    # Keep a non-restrictive reference schema; unknown variants remain open.
    return {
        "$schema": DRAFT,
        "title": entry["endpoint_id"] + " observed response",
        "description": "한정된 관찰 근거의 참고 스키마이며 공식 서버 계약/required 검증 아님",
        **observation,
    }


def render_contracts(document):
    lines = ["# Fable 5.1 — 관찰 기반 JSON 데이터 계약", "",
             "> 서버 공식 명세가 아닙니다. 코드·API 규칙·DB는 실제 확인하지 않았습니다.",
             "",
             "| API | Method | HTTP 상태 | 배열 데이터 경로 후보 | 문자열/범주 후보 | 수치 후보 | 시간명 후보 | 주의점 |",
             "|---|---|---:|---|---|---|---|---|"]
    for entry in document["endpoints"]:
        choices = entry["candidates"]
        def text(key):
            return ", ".join(choices[key][:6]) if choices else "unknown"
        lines.append("| " + entry["endpoint_id"] + " `" + entry["path"] +
                     "` | " + entry["method"] + " | " + str(entry["status"]) +
                     " | " + text("array") + " | " + text("string") + " | " +
                     text("number") + " | " + text("time_name") +
                     " | 개발자 확인 필요 |")
        if not entry["schema_available"]:
            lines.append("- " + entry["endpoint_id"] +
                         ": 본문 미분석/크기 제한/unknown — 스키마 생성하지 않음")
    if not document["endpoints"]:
        lines.append("| - | - | - | unknown | unknown | unknown | unknown | 관찰 구조 없음 |")
    lines += ["", "## 한계", ""]
    lines += ["- " + line for line in document["limitations"]]
    lines += ["", "- string 필드가 실제 범주형이라는 뜻이 아닙니다.",
              "- date/time 이름은 형식 검증이 아닌 이름 기반 후보입니다.",
              "- x/y 축, 집계 방식과 단위는 자동 결정하지 않습니다.",
              ""]
    return "\n".join(lines)


def run_contracts(source: Path, output: Path):
    result = read_result(source)
    document = collect_contracts(result)
    new_directory(output)
    atomic_json(output / "contracts.json", document)
    atomic_text(output / "contracts.md", render_contracts(document))
    schemas = output / "schemas"
    for entry in document["endpoints"]:
        schema = as_json_schema(entry)
        if schema is not None:
            atomic_json(schemas / (entry["endpoint_id"] + ".schema.json"), schema)
    return 0
