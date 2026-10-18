"""Locally render a safe Korean report, never render model HTML or URLs."""
from __future__ import annotations

import html
import re

from .llm_validate import validate_llm_output


def _safe(value):
    # Prevent link/image/HTML injection in a Markdown viewer. Newline is data.
    cleaned = html.escape(value, quote=True).replace("\x00", "")
    cleaned = re.sub(r"([\\`\[\]()*_#!|>])", r"\\\1", cleaned)
    return cleaned.replace("\r", " ").replace("\n", " ").strip()


def render_llm_report(report: dict, payload: dict) -> str:
    report = validate_llm_output(report, payload)
    f = {x["id"]: x for x in payload["findings"]}
    a = {x["id"]: x for x in payload["api_endpoints"]}
    c = {x["id"]: x for x in payload["charts"]}
    candidate = {(x["chart_id"], x["endpoint_id"]): x
                 for x in payload["chart_api_candidates"]}
    lines = [
        "# Fable 5.1 Web Catcher — AI 보조 한국어 분석",
        "",
        "> 모델 분석은 공개 단서에 대한 해석이며, 서버 코드·DB·내부 아키텍처를 실제 확인한 결과가 아닙니다.",
        "> 외부로 전송한 데이터는 정제된 일부 자료입니다. confidence는 확률이 아닌 기존 로컬 엔진 점수입니다.",
        "",
        "## 1. 요약", "",
        _safe(report["summary"]), "",
        "## 2. 관찰된 기술과 근거", "",
    ]
    for item in payload["findings"]:
        lines.append("- **" + _safe(item["name"]) + "** (" + item["id"] +
                     ", " + item["category"] + ") · 규칙 엔진 confidence " +
                     format(item["confidence"], ".3f") +
                     " · 근거 ID: " + ", ".join(item["evidence_ids"]))
    if not payload["findings"]:
        lines.append("- **unknown**: 확인 가능한 기술 근거가 없습니다.")
    lines.extend(["", "## 3. 백엔드 추정 및 confidence (서버 실제 코드 미확인)", ""])
    for item in report["backend_assessments"]:
        finding = f[item["finding_id"]]
        lines.extend([
            "- **" + _safe(finding["name"]) + "** · 기존 엔진 confidence " +
            format(finding["confidence"], ".3f") + " (확률 아님)",
            "  - 근거: " + ", ".join(item["evidence_ids"]),
            "  - 설명: " + _safe(item["explanation"]),
            "  - 한계: " + _safe(item["caveats"]),
        ])
    if not report["backend_assessments"]:
        lines.append("- **unknown**: 백엔드 구현을 확인할 근거가 충분하지 않습니다.")
    lines.extend(["", "## 4. 실제 관찰된 API", ""])
    for ep in payload["api_endpoints"]:
        lines.append("- " + ep["id"] + " " + ep["method"] + " `" +
                     _safe(ep["path"]) + "` HTTP " +
                     (str(ep["status"]) if ep["status"] is not None else "unknown") +
                     " · " + ep["content_type"] +
                     (" · 제한된 부분 JSON 필드 단서" if ep["partial_prefix_fields"] else ""))
    if not payload["api_endpoints"]:
        lines.append("- 관찰된 API 없음")
    lines.extend(["", "## 5. 차트 ↔ API 연관 후보 (확정 아님)", ""])
    for item in report["chart_api_assessments"]:
        chosen = candidate[item["chart_id"], item["endpoint_id"]]
        lines.extend([
            "- " + item["chart_id"] + " ↔ " + item["endpoint_id"] +
            " · 기존 매핑 confidence " + format(chosen["confidence"], ".3f"),
            "  - 근거: " + ", ".join(item["evidence_ids"]),
            "  - 설명: " + _safe(item["explanation"]),
            "  - 한계: " + _safe(item["caveats"]),
        ])
    if not report["chart_api_assessments"]:
        lines.append("- 관찰·검증된 연관 후보 없음. 시간 근접만으로 매핑하지 않습니다.")
    lines.extend(["", "## 6. 알 수 없는 부분과 분석 한계", ""])
    for note in report["limitations"] + payload["limitations"]:
        lines.append("- " + _safe(note))
    if any(payload["omissions"].values()):
        lines.append("- 입력 근거 일부 생략: " + ", ".join(
            k + "=" + str(v) for k, v in payload["omissions"].items() if v))
    lines.extend(["", "## 7. 재구현 제안 — 원 사이트 사용 기술과 별개", ""])
    for item in report["implementation_suggestions"]:
        lines.extend(["- **" + _safe(item["title"]) + "**",
                      "  - 제안: " + _safe(item["description"]),
                      "  - 한계: " + _safe(item["caveats"])])
    if not report["implementation_suggestions"]:
        lines.append("- 별도 재구현 제안 없음")
    lines.extend(["", "모델에 실행 도구나 파일 접근 권한을 제공하지 않았으며 출력된 명령을 자동 실행하지 않습니다.", ""])
    return "\n".join(lines)
