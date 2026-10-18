"""Sequential, non-resumable Step 5 batch. Each scan gets a fresh browser."""
from __future__ import annotations
import contextlib
import copy
import io
import json
import re
import secrets
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from .models import CATEGORIES
from .llm_payload import SAFE_EVIDENCE_MARKERS
from .report import to_markdown
from .step5_common import (atomic_json, atomic_text, new_directory, normalized_batch_url,
                           safe_batch_url, anonymous_path, privacy_summary,
                           safe_structure, masked_field, safe_error)

MAX_INPUT_BYTES = 100_000


def utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_urls(path, max_urls=50):
    if not path.is_file() or path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("배치 목록을 찾지 못했거나 크기 제한을 초과했습니다.")
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    seen, valid, errors = set(), [], []
    for number, line in enumerate(lines, 1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        try:
            clean = normalized_batch_url(text)
            if clean not in seen:
                seen.add(clean)
                valid.append(clean)
                if len(valid) > max_urls:
                    raise ValueError("배치 URL 수 제한 초과")
        except ValueError as exc:
            if "수 제한 초과" in str(exc):
                raise
            errors.append({"line": number, "error": "invalid_url"})
    return valid, errors


def _redact(value, key="", origin_alias="https://batch-unknown.invalid"):
    """Serialize a constrained result without raw identifiers or PII."""
    from .llm_payload import _catalog
    allowed_technologies = _catalog()
    if key in ("json_structure",):
        return safe_structure(value) if value is not None else None
    if key == "json_prefix_structure":
        if isinstance(value, dict) and value.get("completeness") == "partial_prefix_only":
            return {"completeness": "partial_prefix_only",
                    "sample_kind": "first_complete_object",
                    "fields": safe_structure(value.get("fields"))}
        return None
    if isinstance(value, dict):
        return {k: _redact(v, k, origin_alias) for k, v in value.items()
                if not k.lower().startswith(("raw_", "secret_", "access_token"))}
    if isinstance(value, list):
        return [_redact(v, key, origin_alias) for v in value[:200]]
    if not isinstance(value, str):
        return value
    if key in ("input_url", "final_url", "url", "source_script"):
        return anonymous_path(value, origin=origin_alias)
    if key == "name":
        return value if value in allowed_technologies or value == "unknown" else "unknown"
    if key == "version":
        return value if re.fullmatch(r"\d+(?:\.\d+){0,5}", value) else None
    if key == "evidence_ids":
        # Safe structural references must survive redaction so reports can
        # resolve citations. Reject any user-controlled/free-text values.
        return value if re.fullmatch(r"ev_[0-9]{1,6}", value) else "[REDACTED]"
    if key == "key":
        return masked_field(value)
    if key == "value":
        return value if value in SAFE_EVIDENCE_MARKERS else "[REDACTED]"
    if key in ("note", "selector", "tag", "pattern", "path", "fragment"):
        return "[REDACTED]"
    if key in ("source", "id", "method", "content_type", "library", "resource_type",
               "scan_mode", "schema_version", "response_body_analysis", "detection_level",
               "change_evidence", "stop_reason", "kind", "status", "page_id",
               "navigation_id", "frame_id", "type", "reason"):
        return value[:75] if re.fullmatch(r"[A-Za-z0-9_.+:/-]{1,75}", value) else "unknown"
    return "[REDACTED]"


def safe_batch_result(result, origin_alias):
    clean = _redact(result, origin_alias=origin_alias)
    # Drop raw-content-derived strings and all potential URL hints not
    # needed for reproducible offline comparison/contracts.
    clean["warnings"] = ["상세를 저장하지 않은 원본 경고"] * min(100, len(result.get("warnings", [])))
    clean.setdefault("api", {})["candidates"] = []
    clean["target"]["cookie_names"] = []
    clean["target"]["meta_generator"] = []
    clean["target"]["response_headers"] = {}
    clean["target"]["csp_domains"] = []
    # Known-list summary reports do not need the original path or host.
    return clean


def batch_report(manifest):
    lines = [
        "# Fable 5.1 Web Catcher — URL 배치 분석",
        "",
        "> 관찰 결과는 해당 실행 범위에 한정됩니다. 실패는 기술/API 미탐지가 아닙니다.",
        "| 대상 | 상태 | 주요 기술 | 백엔드 추정 | API | 차트 | 경고 | 보고서 |",
        "|---|---|---|---|---:|---:|---:|---|",
    ]
    for t in manifest["targets"]:
        s = t.get("summary") or {}
        tech = s.get("technologies", {})
        front = ", ".join(tech.get("frontend", [])[:4]) or "unknown"
        back = ", ".join(tech.get("backend_inferred", [])[:4]) or "unknown"
        report = t.get("report_path")
        link = "[" + t["target_id"] + "](" + report + ")" if report else "-"
        def amount(field):
            return str(s.get(field, 0)) if s else "미확인"
        lines.append("| " + " | ".join([
            t["target_id"], t["status"], front if s else "미확인",
            back if s else "미확인", amount("api_count"), amount("chart_count"),
            amount("warning_count"), link]) + " |")
    lines.extend(["", "## 배치 집계", ""])
    count = {}
    for t in manifest["targets"]:
        count[t["status"]] = count.get(t["status"], 0) + 1
    lines.append("- " + ", ".join(k + "=" + str(v) for k, v in sorted(count.items())))
    if manifest["input_errors"]:
        lines.append("- 잘못된 입력: " + str(len(manifest["input_errors"])) +
                     "건 (줄 번호와 오류 유형은 batch_manifest.json 참고)")
    lines.extend(["- 분석 결과는 개인정보 보호를 위해 사이트 이름·쿼리값·임의 경로를 일반화했습니다.",
                  "- 자동 재개·병렬 실행·로그인·우회·자동 LLM 호출은 지원하지 않습니다.", ""])
    return "\n".join(lines)


def run_batch(input_path, output, *, scan_fn, runtime=False, headed=False,
              wait=10, timeout=10, delay=2, max_urls=50, sleep=time.sleep):
    if delay < 1 or not (1 <= max_urls <= 500):
        raise ValueError("--delay는 1초 이상이고 --max-urls는 1~500이어야 합니다.")
    urls, errors = parse_urls(input_path, max_urls=max_urls)
    new_directory(output)
    targets = []
    run_nonce = secrets.token_hex(6)  # not a server secret, just an alias namespace
    origin_aliases = {}
    aliases = []
    for i, url in enumerate(urls, 1):
        parts = urlsplit(url)
        key = (parts.scheme, parts.hostname, parts.port)
        if key not in origin_aliases:
            index = len(origin_aliases) + 1
            origin_aliases[key] = ("https://batch-" + run_nonce + "-origin-" +
                                   str(index).zfill(3) + ".batch.invalid")
        aliases.append(origin_aliases[key])
        targets.append({
            "target_id": "target-" + str(i).zfill(3),
            "masked_url": safe_batch_url(url, aliases[-1]),
            "status": "pending", "started_at": None, "ended_at": None,
            "duration_seconds": None, "result_path": None, "report_path": None,
            "warnings": [], "error": None,
        })
    manifest = {"schema_version": "batch-1", "created_at": utc(),
                "scan_mode": "runtime" if runtime else "static",
                "input_errors": errors, "targets": targets}
    def checkpoint():
        atomic_json(output / "batch_manifest.json", manifest)
        atomic_json(output / "batch_summary.json", {
            "schema_version": "batch-summary-1", "target_count": len(targets),
            "counts": {state: sum(t["status"] == state for t in targets)
                       for state in ("pending", "running", "success", "partial",
                                     "failed", "interrupted", "skipped")},
            "input_error_count": len(errors),
        })
        atomic_text(output / "batch_report.md", batch_report(manifest))
    checkpoint()
    blocked = set()
    had_failure = bool(errors)
    for i, url in enumerate(urls):
        row = targets[i]
        origin = urlsplit(url).netloc
        if origin in blocked:
            row.update(status="skipped", ended_at=utc(),
                       error="origin_rate_limited")
            had_failure = True
            checkpoint()
            continue
        if i > 0:
            sleep(delay)
        row["status"] = "running"
        row["started_at"] = utc()
        began = time.monotonic()
        checkpoint()
        folder = output / "targets" / (str(i + 1).zfill(3) + "-site")
        try:
            with tempfile.TemporaryDirectory(prefix="fable-batch-") as scratch:
                # Suppress raw scanner stdout so it cannot echo a secret URL.
                with contextlib.redirect_stdout(io.StringIO()):
                    status = scan_fn(url, Path(scratch), timeout, runtime=runtime,
                                     wait=wait, headed=headed)
                scan_file = Path(scratch) / "result.json"
                if not scan_file.exists():
                    raise ValueError("missing_result")
                obj = json.loads(scan_file.read_text(encoding="utf-8"))
                clean = safe_batch_result(obj, aliases[i])
                folder.mkdir(parents=True, exist_ok=False)
                atomic_json(folder / "result.json", clean)
                # Reports are generated from redacted structured values.
                try:
                    report = to_markdown(clean)
                except (KeyError, TypeError, ValueError):
                    report = "# Fable 5.1 — 개별 분석 요약\n\n" + (
                        "정제된 result.json에서 상세 정보 확인 필요\n")
                atomic_text(folder / "report.md", report)
                row["result_path"] = (folder / "result.json").relative_to(output).as_posix()
                row["report_path"] = (folder / "report.md").relative_to(output).as_posix()
                row["summary"] = privacy_summary(clean)
                http = obj.get("target", {}).get("status_code")
                if http == 429:
                    blocked.add(origin)  # Skip same-origin remainder; never retry.
                row["status"] = ("failed" if status != 0 else
                                 "partial" if obj.get("warnings") else "success")
                row["warnings"] = (["경고 " + str(len(obj["warnings"])) + "건"]
                                    if obj.get("warnings") else [])
                if status != 0:
                    row["error"] = ("rate_limited_429" if http == 429 else
                                    "blocked_403" if http == 403 else "scan_failed")
                    had_failure = True
        except KeyboardInterrupt:
            row["status"] = "interrupted"
            row["error"] = "interrupted"
            row["ended_at"] = utc()
            row["duration_seconds"] = round(time.monotonic() - began, 3)
            checkpoint()
            return 130
        except Exception:
            row["status"] = "failed"
            row["error"] = "scan_failed"
            had_failure = True
        finally:
            if row["status"] == "running":
                row["status"] = "failed"
            if row["ended_at"] is None:
                row["ended_at"] = utc()
                row["duration_seconds"] = round(time.monotonic() - began, 3)
            checkpoint()
    # 0: success (including nonfatal warnings); 2: any failed/skipped/invalid.
    return 2 if had_failure else 0
