# STATUS.md — Fable 5.1 Web Catcher / Step 2 최종 완료

## 최종 판정 (2026-10-18 KST)
- **Step 1 완료 7/7 (100%)**: 정적 CLI 회귀 유지.
- **Step 2 원본 완료 기준 9/9 (100%) PASS**: 공개·무인증 페이지 CLI MVP 범위. 상세 기준/근거 `docs/STEP2_FINAL_ACCEPTANCE.md`.
- GitHub 비공개 `hibi89/fable5.1_web_catcher`, `main`. 기능 최종 검증 SHA **`e743e8c2b208940e66e03cfd6fc799031d7cc337`**. 배포/Production/Vercel 없음.

## 구현한 Step 2 범위
1. --runtime/--headed/--wait 기본 10초, 새 격리 Chromium, 이동 전 리스너, 제한 스크롤, 자원 정리.
2. XHR/fetch 관찰 endpoint, HTTP 메타데이터, 크기 제한 JSON 값 없는 구조, GraphQL 후보.
3. WebSocket 프레임 개수 및 SSE 연결 메타데이터(내용 미저장).
4. 알려진 JS 차트 라이브러리 런타임 마커, DOM+MutationObserver 기반 SVG/canvas 후보(확정 아님).
5. 차트↔API 근거 기반 보수적 **연관 후보**, 동시 적격 API 경합 시 보류.
6. 이미 로드된 동일 출처 JS 파일 10개 이하/개별 128KiB 이하의 문자열 기반 **미검증 API 후보**; 새 경로 요청 안 함.
- **출력 구분:** `api.endpoints`는 실제 XHR/fetch, `api.connections`는 실제 WS/SSE, `api.candidates`는 미검증 JS 문자열(source_script/discovered_by=bundle_string), `api.chart_candidates`는 차트 연관 후보(reasons/limitations). `charts[].data_sources`는 확정 lineage 아님.

## 최종 실행 테스트
- Windows Server 2022 / Python 3.11: `python -m pytest -q` → **55/55 PASS**, run **39120274152**.
- Ubuntu 24.04 / 실제 Playwright Chromium: 4개 독립 fixture 테스트 파일 → **11/11 PASS**, run **39120274247**.
- 공개 `https://example.com/`, `https://www.python.org/`의 정적 및 Chromium 런타임 각 1회 → **4/4 PASS**; HTTP 200, exit 0 및 구조/근거 검사 통과. 같은 Chromium run 로그.
- 모두 소스 SHA **`e743e8c2b208940e66e03cfd6fc799031d7cc337`**. 최종 완료 문서/README 커밋은 테스트 후 별도 문서 변경.
- 중간 실패·옛 스키마는 최종 성공과 혼동하지 말 것. 최종 원본 스키마/10개 상한/이유(reasons)·HTML 내장 가능성 문구를 수정하고 재검증.

## 한계 / 비목표
- 실제 라이브러리 통합은 일부 stub, 임의 공개 사이트의 탐지 정확도는 미검증. 차트↔API 매핑은 실제 데이터 흐름 확인이 아닌 연관 후보.
- Playwright 본문 압축 해제 메모리의 절대 상한 보장 불가. 브라우저 미설치나 사이트 차단 시 부분 결과 및 안내.
- 개인 Windows PC headed 동작 및 SSRF 서버 방어 미검증/미구현. 외부 사용자 URL 서비스로 배포 금지.
- Record 모드, LLM, 웹 UI, 다중 페이지 크롤러, Production 배포는 범위 밖.

## 다음 진행
**필수 Step 2 작업 없음.** 새 사용자 요청이 있을 때에만 실사이트 확대 검증·정확도 개선·후속 Step 3/배포 등을 별도로 계획. `HANDOFF.md`에 10항 인수인계.
