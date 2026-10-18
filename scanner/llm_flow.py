"""Offline dry-run and separate validated LLM report files."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .llm_client import LLMServiceError, generate_structured
from .llm_payload import build_llm_payload, PAYLOAD_SCHEMA_VERSION
from .llm_report import render_llm_report
from .llm_validate import PROMPT_VERSION


def run_llm_from_result(source: Path, output: Path, *, model=None, dry_run=False,
                        client=None) -> int:
    try:
        if not source.is_file():
            print("LLM 실패: 지정한 result.json 파일이 없습니다.")
            return 3
        if source.stat().st_size > 6_000_000:
            print("LLM 실패: result.json 파일 크기 상한 6MB 초과")
            return 3
        original = source.read_bytes()
        result = json.loads(original)
        payload = build_llm_payload(result)
        output.mkdir(parents=True, exist_ok=True)
        if dry_run:
            path = output / "llm_payload.preview.json"
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) +
                            "\n", encoding="utf-8")
            print("외부 API 호출 없음: 전송 예정 데이터 미리보기 " + str(path))
            return 0
        analysis, usage = generate_structured(payload, model, client=client)
        markdown = render_llm_report(analysis, payload)
        package = {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model": model, "prompt_version": PROMPT_VERSION,
            "payload_schema_version": PAYLOAD_SCHEMA_VERSION,
            "source_result_sha256": hashlib.sha256(original).hexdigest(),
            "api_usage": usage, "omissions": payload["omissions"],
            "warnings": payload["warnings"] +
                        (["선택된 일부 근거에 기반한 분석"] if any(payload["omissions"].values()) else []),
            "analysis": analysis,
        }
        (output / "llm_report.json").write_text(
            json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (output / "llm_report.md").write_text(markdown, encoding="utf-8")
        print("검증된 AI 보조 보고서: " + str(output / "llm_report.md"))
        return 0
    except LLMServiceError as exc:
        # Never echo provider exception URLs, keys, response bodies or raw model text.
        print("LLM 실패 [" + exc.kind + "]: " + str(exc))
        print("기존 result.json/report.md는 그대로 유지됩니다.")
        return 3
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError):
        print("LLM 실패: 결과 파일/전송 자료 검증 오류. 기존 보고서를 확인하세요.")
        return 3
