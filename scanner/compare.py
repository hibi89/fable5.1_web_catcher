"""Step 5 offline comparison of recorded *observations*, not live site changes."""
from __future__ import annotations
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl

from .models import CATEGORIES
from .step5_common import (read_result, new_directory, atomic_json,
                           atomic_text, path_key, anonymous_path,
                           safe_structure, source_identity)
from .llm_payload import _catalog

ALLOWED_TECH = _catalog()


def _findings(result):
    evidence = {x.get("id"): x.get("source", "unknown")
                for x in result.get("evidence", []) if isinstance(x, dict)}
    out = {}
    for category in CATEGORIES:
        if category not in result:
            continue
        for row in result.get(category, []):
            if not isinstance(row, dict):
                continue
            name = row.get("name")
            if name not in ALLOWED_TECH and name != "unknown":
                continue
            if name == "unknown":
                continue
            key = category + "/" + name.lower()
            out[key] = {
                "name": name, "category": category,
                "version": row.get("version") if isinstance(row.get("version"), str)
                           and row["version"].replace(".", "").isdigit() else None,
                "confidence": row.get("confidence") if type(row.get("confidence")) in
                              (int, float) else None,
                "evidence_sources": sorted({evidence[eid] for eid in row.get("evidence_ids", [])
                                            if eid in evidence and evidence[eid] in
                                            ("html", "response_header", "cookie_name",
                                             "script_src", "stylesheet_href",
                                             "meta_generator", "runtime_global")}),
            }
    return out


def _api(result):
    groups = defaultdict(list)
    for ep in result.get("api", {}).get("endpoints", []):
        if not isinstance(ep, dict):
            continue
        url = ep.get("url")
        if not isinstance(url, str):
            continue
        key = path_key(url)
        if key is None:
            continue
        method = ep.get("method", "unknown")
        if method not in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
            method = "unknown"
        query_keys = []
        try:
            query_keys = sorted({k.lower() for k, _ in parse_qsl(urlsplit(url).query)
                                 if k.lower() in ("page", "limit", "offset", "sort",
                                                  "filter", "date", "region", "country")})
        except ValueError:
            pass
        groups[(key, method)].append({
            "status": ep.get("status") if type(ep.get("status")) is int else None,
            "content_type": ep.get("content_type") if ep.get("content_type") in
                            ("application/json", "application/graphql",
                             "application/problem+json") else "unknown",
            "json_structure": (safe_structure(ep.get("json_structure"))
                               if ep.get("json_structure") is not None else None),
            "query_keys": query_keys,
            "analysis": ep.get("response_body_analysis", "unknown"),
        })
    return groups


def _comparison_state(a, b, same):
    if a and b:
        return "common"
    if same:
        return "not_observed_in_previous" if b else "not_observed_this_run"
    return "only_in_b" if b else "only_in_a"


def _tree_changes(left, right, path="$"):
    if left == right:
        return []
    if isinstance(left, dict) and isinstance(right, dict):
        changed = []
        for k in sorted(set(left) | set(right)):
            if k not in left:
                changed.append({"field": path + "." + k, "change": "observed_only_in_b"})
            elif k not in right:
                changed.append({"field": path + "." + k, "change": "observed_only_in_a"})
            else:
                changed.extend(_tree_changes(left[k], right[k], path + "." + k))
        return changed[:80]
    if isinstance(left, list) and isinstance(right, list):
        # Array sample order is not schema evidence; compare unique shape set.
        l = sorted({repr(v) for v in left})
        r = sorted({repr(v) for v in right})
        return [] if l == r else [{"field": path, "change": "observed_array_item_shape_difference"}]
    return [{"field": path, "change": "observed_type_or_shape_difference",
             "a": str(left) if isinstance(left, str) and left in
                  ("string", "number", "integer", "boolean", "null", "unknown", "truncated") else "unknown",
             "b": str(right) if isinstance(right, str) and right in
                  ("string", "number", "integer", "boolean", "null", "unknown", "truncated") else "unknown"}]


def _scope(result):
    run = result.get("runtime", {})
    rec = result.get("record", {})
    meta = {"scan_mode": result.get("scan_mode", "unknown"),
            "wait_seconds": run.get("wait_seconds") if isinstance(run, dict) else None,
            "record_duration_seconds": (rec.get("duration_seconds")
                                        if isinstance(rec, dict) else None),
            "allowed_origin_count": (len(rec["allowed_origins"])
                                     if isinstance(rec, dict) and isinstance(rec.get("allowed_origins"), list)
                                     else None),
            "warnings_count": len(result.get("warnings", [])),
            "schema_version": result.get("schema_version", "legacy_unknown")}
    return meta


def compare_results(a, b):
    same = source_identity(a) is not None and source_identity(a) == source_identity(b)
    ia, ib = source_identity(a), source_identity(b)
    kind = ("same_target" if same else
            "different_targets" if ia is not None and ib is not None and ia != ib
            else "unknown_identity")
    warnings = []
    if kind == "unknown_identity":
        warnings.append("마스킹/누락된 대상 식별자로 동일 사이트 여부를 확정할 수 없습니다.")
    if _scope(a)["scan_mode"] != _scope(b)["scan_mode"]:
        warnings.append("스캔 모드가 달라 수집 범위가 직접 비교 가능하지 않습니다.")
    if _scope(a)["allowed_origin_count"] != _scope(b)["allowed_origin_count"]:
        warnings.append("허용 origin 범위 정보가 다르거나 이전 결과에 없습니다.")
    fa, fb = _findings(a), _findings(b)
    technology = []
    for key in sorted(set(fa) | set(fb)):
        x, y = fa.get(key), fb.get(key)
        changes = {}
        if x and y:
            for field in ("version", "confidence", "evidence_sources"):
                if x[field] != y[field]:
                    changes[field] = {"a": x[field], "b": y[field]}
        technology.append({"name": key, "state": _comparison_state(x,y,same),
                           "changes": changes})
    aa, bb = _api(a), _api(b)
    # Never match a different origin just because path segments look alike.
    endpoint_rows = []
    for key in sorted(set(aa) | set(bb), key=repr):
        left, right = aa.get(key, []), bb.get(key, [])
        origin, normalized_path = key[0]
        method = key[1]
        if len(left)>1 or len(right)>1:
            state = "ambiguous_normalized_endpoint"
        else:
            state = _comparison_state(left, right, same)
        changes = []
        if len(left) == len(right) == 1:
            for k in ("status", "content_type", "query_keys", "analysis"):
                if left[0][k] != right[0][k]:
                    changes.append({"field": k, "change": "observation_diff"})
            if left[0]["json_structure"] is None or right[0]["json_structure"] is None:
                if left[0]["json_structure"] != right[0]["json_structure"]:
                    changes.append({"field": "json_structure", "change": "unknown_on_one_side"})
            else:
                changes += _tree_changes(left[0]["json_structure"],right[0]["json_structure"])
        endpoint_rows.append({
            "id": "api-" + str(len(endpoint_rows)+1).zfill(3),
            "method": method,
            "path": "origin_observed" + normalized_path,  # host deliberately omitted
            "state": state, "samples_a": len(left), "samples_b": len(right),
            "changes": changes[:80],
        })
    chart_a = Counter(str(c.get("library", "unknown")).lower()
                      for c in a.get("charts", []) if isinstance(c, dict))
    chart_b = Counter(str(c.get("library", "unknown")).lower()
                      for c in b.get("charts", []) if isinstance(c, dict))
    chart_a = {k:v for k,v in chart_a.items() if k in
               ("unknown", "echarts", "highcharts", "d3", "chart.js",
                "recharts", "plotly", "apexcharts")}
    chart_b = {k:v for k,v in chart_b.items() if k in
               ("unknown", "echarts", "highcharts", "d3", "chart.js",
                "recharts", "plotly", "apexcharts")}
    mapping_a = len(a.get("api",{}).get("chart_candidates", []))
    mapping_b = len(b.get("api",{}).get("chart_candidates", []))
    scope_a, scope_b = _scope(a), _scope(b)
    if any(scope_a.get(k) != scope_b.get(k) for k in
           ("wait_seconds", "record_duration_seconds", "warnings_count")):
        warnings.append("대기/기록 시간 또는 경고 수 차이로 관찰 범위가 달라졌을 수 있습니다.")
    return {
        "schema_version": "comparison-1", "comparison_mode": kind,
        "metadata": {"a": scope_a, "b": scope_b},
        "warnings": warnings + [
            "이번 실행에서 미관찰된 기술/API는 실제로 삭제되었다는 의미가 아닙니다.",
            "구조 차이는 관찰 표본 차이로, 서버의 breaking change 확증이 아닙니다.",
            "차트 ID/selector는 실행 간 불안정하므로 개별 차트 동일성을 추정하지 않습니다."],
        "technologies": technology, "api_endpoints": endpoint_rows,
        "charts": {"count_a": sum(chart_a.values()),"count_b":sum(chart_b.values()),
                   "libraries_a": chart_a, "libraries_b": chart_b,
                   "candidate_pairs_count_a": mapping_a,
                   "candidate_pairs_count_b": mapping_b,
                   "individual_matching": "unsupported"},
        "to_verify": ["스캔 모드·로그인 상태·조작 순서와 동적 로딩의 차이를 확인하세요.",
                      "JSON Schema 구조 차이는 실제 API 계약 변경인지 공식 명세로 검증하세요."],
    }


def render_diff(diff):
    lines = ["# Fable 5.1 — 저장된 결과 비교", "",
             "- 비교 구분: " + diff["comparison_mode"],
             "- 다른 사이트는 시간 경과에 따른 삭제/추가로 표현하지 않습니다.",
             "", "## 비교 가능성 경고", ""]
    lines += ["- " + s for s in diff["warnings"]]
    lines += ["", "## 기술 비교", "", "| 기술 | 관찰 분류 | 세부 변화 |",
              "|---|---|---|"]
    lines += ["| " + x["name"] + " | " + x["state"] + " | " +
              ", ".join(x["changes"]) + " |" for x in diff["technologies"]]
    lines += ["", "## API/JSON 구조 비교", "", "| API | 메서드 | 경로 | 상태 | 구조/값 차이 |",
              "|---|---|---|---|---|"]
    lines += ["| " + x["id"] + " | " + x["method"] + " | " + x["path"] +
              " | " + x["state"] + " | " +
              ", ".join(c["field"] + ":" + c["change"] for c in x["changes"][:10]) +
              " |" for x in diff["api_endpoints"]]
    lines += ["", "## 차트 비교", "",
              "- 후보 수: A=" + str(diff["charts"]["count_a"]) +
              ", B=" + str(diff["charts"]["count_b"]),
              "- 개별 차트 매칭은 근거 부족으로 지원하지 않습니다.",
              "", "## 확인이 필요한 변화", ""]
    lines += ["- " + text for text in diff["to_verify"]]
    return "\n".join(lines) + "\n"


def run_compare(path_a: Path, path_b: Path, out: Path):
    a, b = read_result(path_a), read_result(path_b)
    diff = compare_results(a, b)
    new_directory(out)
    atomic_json(out / "diff.json", diff)
    atomic_text(out / "diff.md", render_diff(diff))
    return 0
