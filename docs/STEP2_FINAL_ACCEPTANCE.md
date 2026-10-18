# Step 2 최종 인수 검사 — Fable 5.1 Web Catcher

기준: 사용자 첨부 원본 fable5.1_step2.txt. 검수일: 2026-10-18 (KST).
저장소: 비공개 hibi89/fable5.1_web_catcher, main.

## 원본 완료 기준 9개

| 번호 | 원본 완료 기준 | 판정 및 근거 |
| --- | --- | --- |
| 1 | 기존 Step 1 CLI 유지 | PASS — 기본 정적 모드 및 기존 정적 회귀 보존 |
| 2 | --runtime으로 실제 Chromium 실행 | PASS — Ubuntu Chromium 11/11, subprocess와 공개 URL 실행 |
| 3 | fixture에서 API·JSON 구조·차트 후보 저장 | PASS — browser_final_check.py 통합 사례 |
| 4 | 근거/confidence 붙은 차트 연관 후보 | PASS — api.chart_candidates, 경쟁 API 보류 |
| 5 | 번들 후보/실제 요청 명확한 구분 | PASS — api.candidates는 미검증 bundle_string, api.endpoints는 실제 요청 |
| 6 | 유한 시간 종료와 브라우저 정리 | PASS — 제한된 wait, SSE 미완료 테스트, context/browser finally |
| 7 | JSON/MD/로그 비밀값 비노출 | PASS — fixture의 토큰·JSON 원본·JS·WS·SSE 비노출 검사 |
| 8 | 정적·브라우저 테스트 통과 | PASS — Windows 55/55, 실제 Chromium 11/11, 공개 페이지 4/4 |
| 9 | README 설치·실행·한계·해결방법 | PASS — README의 Step 1/2 명령과 설치/실패/주의사항 |

**판정: 사용자 원본의 Step 2 완료 기준 9/9 PASS (공개·무인증 페이지 CLI MVP 범위).**

## 실제 검증

- Windows 2022 Python 3.11: python -m pytest -q → 55 passed.
- Ubuntu 24.04 Python 3.11 + 설치된 Playwright Chromium: python -m pytest -q tests/browser_runtime_check.py tests/browser_mapping_check.py tests/browser_bundle_check.py tests/browser_final_check.py → 11 passed.
- 동일 Ubuntu 환경 공개 홈페이지 실제 실행: python -m pytest -q -s tests/public_runtime_smoke.py → 4 passed.
- 공개 URL: https://example.com/ 및 https://www.python.org/ 를 정적·런타임 각 1회씩 확인. 4개 모두 HTTP 200/exit 0 및 JSON/Markdown 구조 검증. Python.org 런타임에서 실제 XHR/fetch 요청 10건 관찰. 이는 기술 탐지 정확도 자체의 검증은 아님.
- Actions 근거: Windows run 39120274152, Chromium+공개 사이트 run 39120274247. 최종 코드 SHA는 해당 작업의 GitHub HEAD 및 실행 run head_sha를 함께 확인.
- 전환 과정의 중간 실패를 최종 PASS로 집계하지 않음. 원본 요구 재검토 후 JS 최대 10파일, 번들 문자열 api.candidates/source_script/discovered_by, 차트 연관 별도 api.chart_candidates/reasons, 내장 HTML 데이터 가능성 안내를 보완함.

## 결과 항목 예시 (구조 설명용, 실사이트 데이터 아님)

- scan_mode: runtime
- api.endpoints: 실제 관찰한 XHR/fetch 요청 ID, 시각, 응답 상태, 값 없는 JSON 구조
- api.connections: 실제 WebSocket/SSE 연결의 마스킹 URL·시각·프레임 개수/응답 MIME
- api.candidates: 로드된 JS에서 발견한 미검증 경로, source_script, discovered_by=bundle_string, observed_request=false
- api.chart_candidates: chart_id, endpoint_id, candidate_only, confidence, reasons, limitations
- charts[].data_sources: 실제 lineage가 아닌 선택된 endpoint **후보** ID
- runtime.bundle_scan 및 runtime.mapping_analysis: 제한·보류·증거 부족 표시
- result.json과 report.md: 모든 성공/실패 시 보존, 부분 오류 시 exit 2

## 실행

    python -m pip install -r requirements.txt
    python -m playwright install chromium
    python scan.py https://example.com/ --out ./out/static
    python scan.py https://example.com/ --runtime --wait 10 --out ./out/runtime
    python scan.py https://example.com/ --runtime --headed --wait 10 --out ./out/visible
    python -m pytest -q
    python -m pytest -q tests/browser_runtime_check.py tests/browser_mapping_check.py tests/browser_bundle_check.py tests/browser_final_check.py

## 남은 한계 (완료 선언의 범위 밖)

- 테스트용 chart library 전역 일부는 명시적 stub. 실제 상용 배포 라이브러리를 별도 통합 테스트하지 않음.
- 차트↔API 연관은 관찰 근거 기반 **추정 후보**이지 실제 데이터 흐름 확정 아님. 초기 HTML/인라인 데이터로 차트가 렌더링될 수도 있고 반복 상관성은 검증하지 않음.
- 일반 canvas/SVG는 차트 확정 불가. DOM first_seen은 렌더 완료가 아니며 canvas 픽셀 갱신은 MutationObserver에서 보이지 않음.
- JS는 같은 출처 이미 로드된 완료 응답 중 최대 10개, 각 128 KiB까지만 분석. Playwright의 압축 해제 메모리 절대 상한은 보장되지 않음. 소스맵/미관찰 경로 탐색하지 않음.
- 사용자 개인 Windows PC Chromium/headed, 다양한 실사이트별 휴리스틱 품질은 미검증.
- SSRF 차단 프록시는 없으므로 외부 사용자 임의 URL을 입력받는 서버로 공개하지 않음.
- Record, LLM 연동, 웹 UI, 여러 페이지 크롤러 및 배포는 사용자 요구에 따라 범위 밖.

## 주요 파일

- 구현: scan.py, scanner/runtime_scan.py, scanner/network.py, scanner/connections.py, scanner/runtime_detect.py, scanner/chart_mapping.py, scanner/bundle_scan.py, scanner/report.py.
- 검증: tests/test_bundle_scan.py, tests/test_chart_mapping.py, tests/browser_final_check.py, tests/browser_runtime_check.py, tests/browser_mapping_check.py, tests/browser_bundle_check.py, tests/public_runtime_smoke.py, tests/fixture_server.py.
- CI/문서: .github/workflows/windows-python311.yml, .github/workflows/runtime-python311.yml, README.md, REQUIREMENTS.md, STATUS.md, HANDOFF.md.
