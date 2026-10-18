"""Korean Markdown report from already sanitized, structured data."""
from __future__ import annotations

import json
from pathlib import Path

from .models import CATEGORIES
from .sanitize import safe_text

NAMES = {"frontend": "프론트엔드", "backend_inferred": "백엔드 추정", "infra": "인프라/CDN"}


def to_markdown(result: dict) -> str:
    target = result["target"]
    by_id = {ev["id"]: ev for ev in result["evidence"]}
    lines = ["# Fable 5.1 Web Catcher — 정적 분석 보고서", "",
             f"- 대상: `{target['input_url']}`",
             f"- 최종 URL: `{target['final_url'] or 'unknown'}`",
             f"- 실행 시각 (UTC): {result['scanned_at']}",
             f"- 분석 모드: `{result['scan_mode']}` — 공개 HTML, 응답 헤더, 쿠키 이름, 정적 리소스, CSP 도메인만 조사",
             f"- HTTP 상태: {target['status_code'] if target['status_code'] is not None else 'unknown'}", ""]
    for cat in CATEGORIES:
        lines.extend([f"## {NAMES[cat]}", ""])
        for item in result[cat]:
            if item["name"] == "unknown":
                lines.extend(["- **unknown** — 근거가 없어 판정하지 않음", ""])
                continue
            version = f" (버전 {item['version']})" if item["version"] else ""
            lines.append(f"- **{item['name']}**{version} · confidence **{item['confidence']:.3f}** (휴리스틱, 확률 아님)")
            for eid in item["evidence_ids"]:
                ev = by_id[eid]
                lines.append(f"  - `{eid}` {ev['source']} / {ev['key']}: `{safe_text(ev['value'])}` — {ev['note']}")
        lines.append("")
    lines.extend(["## 리다이렉트 및 공개 단서", "",
                  f"- 리다이렉트: {len(target['redirect_chain'])}건",
                  f"- 허용 응답 헤더: {', '.join(sorted(target['response_headers'])) or '없음'}",
                  f"- 쿠키 이름: {', '.join(target['cookie_names']) or '없음'} (값 저장 안 함)",
                  f"- meta generator: {', '.join(target['meta_generator']) or '없음'}",
                  f"- script src: {len(target['scripts'])}건",
                  f"- stylesheet href: {len(target['stylesheets'])}건",
                  f"- CSP 서비스 도메인: {', '.join(target['csp_domains']) or '없음'}", "",
                  "## 한계 및 주의", "",
                  "- 분석 결과는 공개 응답의 단서이며 서버 코드·데이터베이스·실제 내부 기술을 확인한 것이 아닙니다.",
                  "- 응답 헤더와 쿠키 이름은 프록시·CDN·서버 설정에 의해 변경되거나 위조될 수 있습니다.",
                  "- Next.js 감지는 전체 백엔드가 Node.js임을 의미하지 않습니다.",
                  "- Java Servlet의 JSESSIONID만으로 Spring Boot를 단정하지 않습니다.",
                  "- 정적 GET 1페이지 외 로그인, API 호출, 임의 경로 탐색, 동적 JS 실행은 수행하지 않았습니다.",
                  "- Step 1의 API와 차트 관계 분석은 비활성화되어 있습니다.", "",
                  "## 경고", ""])
    if result["scan_mode"] == "runtime":
        lines[0] = "# Fable 5.1 Web Catcher — 런타임 브라우저 관찰 보고서"
        for i, line in enumerate(lines):
            if line.startswith("- 분석 모드:"):
                lines[i] = "- 분석 모드: `runtime` — Chromium DOMContentLoaded 및 제한 관찰(실행 기반만 구현)"
            elif line.startswith("- 정적 GET 1페이지"):
                lines[i] = "- 격리 브라우저로 페이지만 열고 제한적으로 스크롤했습니다. 로그인·클릭·폼 제출은 하지 않았습니다."
            elif line.startswith("- Step 1의 API"):
                lines[i] = "- 현재 Step 2 단위 1에서는 API·차트 연관 분석이 아직 비활성화되어 있습니다."
        runtime = result.get("runtime", {})
        index = lines.index("## 한계 및 주의")
        lines[index:index] = [
            "## 브라우저 실행 상태", "",
            f"- DOMContentLoaded: {runtime.get('domcontentloaded_observed', False)}",
            f"- 추가 대기(초): {runtime.get('wait_seconds', 0)}",
            f"- 스크롤: {runtime.get('scroll_steps', 0)}회",
            f"- XHR/fetch 요청 관찰 수(메타데이터 미저장): {runtime.get('xhr_fetch_requests_seen', 0)}",
            f"- XHR/fetch 응답 관찰 수(메타데이터 미저장): {runtime.get('xhr_fetch_responses_seen', 0)}",
            "- API 엔드포인트·차트·번들 문자열 분석은 아직 구현하지 않았습니다.", "",
        ]
    lines.extend([f"- {safe_text(w)}" for w in result["warnings"]] or ["- 없음"])
    return "\n".join(lines) + "\n"


def write_reports(result: dict, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (destination / "report.md").write_text(to_markdown(result), encoding="utf-8")
