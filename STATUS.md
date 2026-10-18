# 2026-10-18 22:44 KST — p3 다음 1단위 구현, CI 차단으로 병합 대기

- `r`을 한글 자판의 `ㄱ`으로 해석해 다음 범위 단위 시작: 일반 SVG와 CSS bar 그룹의 기하적 변화 단서 수집.
- PR #4 (branch `fix/step3-generic-chart-change-evidence-20261018`): https://github.com/hibi89/fable5.1_web_catcher/pull/4, 기능 SHA `48312f0e6a7a21d138f083af9194e57d7b651ae1`, 문서 SHA `2cc411bb4fd309a541ef1b9b8204427bae8af31b`.
- 코드: SVG path/d/geometry/childList 변화 시각과 분류형 change_evidence, CSS bar 퍼센트 그룹의 동일 요소 내 모양 변화 비교, 무의미한 호버 이벤트 제외, 수집 값/스타일 원문 미저장, generic chart의 무근거 API 매핑 금지.
- 비브라우저 V8 JS 문법 검사와 모의 DOM에서 CSS baseline→변화, SVG class-only→geometry-change 분기 확인. **Python/Chromium CI는 PASS 아님.** PR 호출된 Windows `39132765417` 및 Chromium `39132765458` 실패, job steps 0개/로그 BlobNotFound. Windows 1회 재실행도 작업 단계 시작 전 실패. 해당 오류를 코드 테스트 실패로 확정할 근거 없음.
- 검증 전 변경을 `main`에 병합하지 않았다. 기존 PR #3 코드 및 CI 63/20/4 PASS 그대로 유지. **이번 단위 상태: 구현과 모의 JS 검증 완료, CI 실제 회귀 검증 차단, 병합 보류.**
- branch 문서: `docs/STEP3_GENERIC_CHART_GEOMETRY_PENDING_2026-10-18.md`. 다음 실행은 GitHub Actions runner/계정 상태 확인 또는 동일 소스의 직접 Python·Chromium 회귀 검증이 우선. 사용자 Windows 테스트 반복 불필요.

---

# Step 3 후속 단위: 헤더 없는 JSON 안전 구조 수집 추가 (2026-10-18 22:30 KST)

- **PR #3 main 병합 완료**: `f7b9bb9c09bc69cd305519b5676af31ff4b2d7ea` / 검증 기능 `dc5992391b399e29bcf6167daf455676e3c15ca7`. 사용자 Windows Record에서 외부 JSON이 `size_unknown`으로 제외됐던 원인에 대응.
- 새 기능은 `--record`에서만 수행. 응답에 Content-Length가 없을 때 requestfinished 후 Playwright 전송 크기 측정, 비압축·128KiB 이하만 JSON 값 없는 구조 분석. 크기/압축/본문 건수/민감키/origin 제한 유지. 기존 `--runtime`은 헤더 없는 JSON `size_unknown` 정책 유지.
- GitHub Actions 실제 확인: Windows Python 3.11 run **39131631123**, **63/63 PASS**. Ubuntu headed Chromium run **39131631050**, **20/20 PASS**, 보조 공개 사이트 **4/4 PASS**. 초기 CI 실패(대기열 정리·기존 Step 2 회귀·테스트 HTTP 버전)는 같은 PR에서 수정했고 최신 두 run만 합격 근거로 사용.
- **사용자 실제 대시보드의 해당 API가 구조 분석 성공하는지는 미검증**. Playwright 본문 처리의 절대 메모리 상한 보장은 없으며 JSON이 여전히 과대/압축/구조 오류일 수 있다. CSS/SVG 차트↔API 연결 후보 0개 문제와 iframe 미지원, browser_closed 시 스냅샷 경고는 변경 안 함.
- 상세: `docs/STEP3_HEADERLESS_JSON_BOUND_2026-10-18.md`. 다음 `ㄱ`은 별도 1단위로 generic CSS/SVG 변경 관찰 근거 보강을 검토할 수 있다. 이 단위에서 미구현.

---

# 2026-10-18 22:03 KST — Step 3 Windows 실제 사이트 재시험 결과 (result(3).json)

- **핵심 Record 동작 및 PR #2 현장 회귀 검증 통과.** 실제 33.312초 수집, browser_closed 정상 종료, 35건 실제 click, 복합키 기준 중복 **0건**, SPA 문서 1건/nav-0001, 차트 후보 3건/ID 충돌 0건, target.final_url 기록 성공.
- 승인한 외부 API origin을 포함해 2곳 허용. 기록된 API 200 application/json, `response_body_analysis=size_unknown` → Content-Length 미확인으로 JSON 구조 분석 보류, `chart_candidates=0`. 차트 후보는 generic SVG/CSS, 관찰 갱신 시각 없음. 첫 기록 클릭은 보존된 API 응답보다 1,539ms 뒤. 데이터 흐름을 임의 연결하면 안 된다.
- 본 실사이트 검사에선 클릭으로 인한 실제 필터 변화나 차트↔API 대응 후보는 미검증. Step 3 CLI 실사용/중복 수정 검증은 완료이지만 사용자 지침의 최종 예시인 'API와 차트 연관 후보 표시'는 이 사이트에서 충족되지 않았다.
- 경고: iframe 미지원, 네트워크 상세 1건 생략, browser_closed에 따른 TargetClosedError 차트 스냅샷 오류(정상 종료 자체는 성공).
- 현장 검사 원본 `result(3).json` SHA-256 `f501ee54ce773c8f7f1bd22945045371929d8ecf7275a876738595bfcf985067`; 전체 원본 결과는 GitHub 저장 금지. 상세: `docs/STEP3_WINDOWS_REAL_SITE_VERIFICATION_2026-10-18.md`.
- 이전 상태의 '실사이트 최종 재시험 미확인' 문구는 역사적 기록이며, **이번 새 현장 자료가 해당 확인을 대체한다**.

---

# 2026-10-18 사용자 업로드 후속 판정 — 새 실사이트 재시험 미확인

- 사용자가 추가 제출한 `result(2).json`은 직전 `result(1).json`과 바이트 단위로 완전히 동일 (SHA-256 `f47e088964ee947c7c3daf6be90d66565190ccb94f868491450036e2d1a29d0f`).
- JSON 내부 시작/종료 UTC: `2026-10-18T12:29:14`~`12:30:01`; 47.344초, 사용자 조작 총 228건, 실제 고유 조작 식별자 75건, 중복 초과 153건. 차트 4건 중 동일 id 중복 1건. 마지막 URL null. allowed_origins는 대시보드 하나이며 외부 API response_body_analysis는 `scope_or_auth_body_excluded`.
- 이는 **수정 전 동일 실행 결과**를 다시 첨부한 것으로, PR #2 병합 이후 Windows 실사이트 테스트가 성공 또는 실패했다는 새 근거는 아님. 자동 테스트 PASS 근거는 기존 문서대로 유지. STEP 3 실사이트 최종 검증 **보류**.
- 다음 검수는 로컬 최신 `main`을 `git rev-parse --short HEAD`로 확인 후 새 `--out ./out/record-after-fix`로 실행한 **그 경로의** `result.json`을 제출받을 것. 결과 파일이 새 실행 시간/명시적 API origin/고유 클릭을 포함하는지 재검토.

---

# Step 3 실제 사용자 대시보드 피드백 반영 (2026-10-18)

- 기존 Step 1/2 및 Step 3 CLI MVP 통과 상태 유지.
- 실제 사용자 테스트 기록: 약 47.344초, 4개 차트 후보, 조작 228건, 문서 5건, API 상세 1건, 차트↔API 후보 0건, browser_closed 종료. 외부 n8n webhook의 응답 구조는 origin 미허용으로 분석 제외.
- 수정: SPA hash/history 변경을 실제 새 JS 문서와 구분하고 중복 마커를 방지. chart ID 안정성 및 browser_closed 이후 last final_url 보존.
- [검증 완료] PR #2 소스 SHA 173d42d3a33d29bf80c2dc5a137daccf0992216d / main 병합 SHA b5496a61bd82d56204bdab24c984288230a95713.
- Windows CI run 39128145838: 60/60 PASS. Ubuntu headed Chromium CI run 39128145939: 19/19 PASS. 같은 run의 선택 공개 페이지 smoke: 4/4 PASS.
- [미검증] 위 코드를 사용자 Windows 실사이트에 적용한 재시험; 명시적 --allow-origin 사용 이후 외부 JSON 구조 확보 여부; 실제 CSS/일반 SVG 차트↔API 계보 확정.
- 보안: cross-origin 응답 구조 허용은 명시적으로 지정한 정확한 origin만. 일반 SVG/CSS 차트에 매핑 결과를 강제하지 않음. 공개 URL 서비스 배포 금지 유지.
- 인수 근거: docs/STEP3_REAL_RECORD_FEEDBACK_2026-10-18.md, 기존 docs/STEP3_FINAL_ACCEPTANCE.md.

---

# STATUS.md — Fable 5.1 Web Catcher / Step 3 자동 인수검사 완료

## 현재 검증된 기준 (2026-10-18 KST)
- Step 1 정적 CLI: 원본 7/7 PASS (유지).
- Step 2 Chromium runtime CLI: 원본 9/9 PASS (유지).
- **Step 3 headed Record CLI: 자동 fixture 인수검사 8/8, Windows 60 PASS / Ubuntu 실제 headed Chromium 16 PASS / 보조 공개 URL 4 PASS.** 실제 사람의 Windows 실사이트 로그인·필터·Enter 시나리오는 미검증.
- 검증 소스 80f71d2b7de0f7a803872e76a616fe70f974e192; PR #1 → main 병합 e28ea7f1f5a91d2f7a69160377558c6bc72e836d. 문서 변경 HEAD는 별도.
- 배포 없음: Python 로컬 CLI, Vercel/Production 미적용.

## 새 구현
--record, --max-duration (기본 900초), 반복 --allow-origin, 터미널 Enter·Ctrl+C·시간 만료·창 종료/EOF. 신규 tabs/main frames 문서 ID, 클릭·변경 마커, 승인 origin만 DOM/값 없는 응답 구조, 인증 요청 본문 보호, 이벤트 상한 생략 경고. Playwright 비영구 context. Step 2 수집기 유지 + 완료 JSON 구조 점진적 분석으로 페이지 이동 전 반영. result.json/report.md의 record 섹션 및 차트↔API **연관 후보**.
주요 경로: scanner/record_scan.py, scanner/network.py, scanner/chart_mapping.py, scanner/report.py, scan.py, tests/test_record.py, tests/browser_record_check.py, docs/STEP3_FINAL_ACCEPTANCE.md.

## 실제 검증
- Windows workflow run 39126644441: python -m pytest -q → 60 passed.
- Ubuntu run 39126644405: Xvfb Chromium 브라우저 fixture → 16 passed.
- 선택 공개 홈페이지 smoke → 4 passed. 모든 테스트는 해당 SHA에서 PASS.
- 원본 Step 1/2 회귀 포함. 개인정보/외부 origin/브라우저 중단/종료 시점 및 API 연관 후보 검증. 테스트용 login은 fixture에서 자동화한 것으로 실제 서비스 계정 로그인과 구별.

## 남은 한계 및 다음 순서
사용자의 Windows 표시 Chrome에서 직접 로그인→차트 필터 변경→Enter 확인 **검증 대기**. iframe DOM 분석 미지원(경고), 모든 사이트 차트 감지 및 API 인과 계보 확정 불가, Playwright decoded body 순간 절대 메모리 상한 미보장. 외부 URL을 받는 서버 배포 금지(SSRF 격리 없음). 필요하면 보안/범위/인증 변경은 먼저 승인. 인수인계 상세 HANDOFF.md, 증거 docs/STEP3_FINAL_ACCEPTANCE.md.

---

# Step 2 STATUS — 보존 이력

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

## 추가 실사이트 정확도 검증 1차 (2026-10-18 KST)
대상: https://daily-dashboard-ldh-1013.clevertide128.chatgpt.site/#v-dash
- 확인된 기존 약점: SPA URL fragment 손실, 18~60px 장식 SVG 다수의 과다 차트 후보 수집, CSS 막대 그룹 미감지.
- 최소 수정: --runtime 브라우저 탐색의 hash 유지(결과에는 미노출), 실제 DOM 크기/도형 수 기반 generic SVG 필터, 가변 퍼센트 높이/너비의 반복 막대 그룹에 css_bar_pattern_candidate(library unknown, confidence 0.5) 보수적 탐지.
- 해당 대시보드 실사이트: HTTP 200, XHR/fetch 2, 기존 차트 후보 14~15 -> **3건**(큰 SVG 2 + CSS 그룹 1), 알려진 라이브러리 0, 차트↔API 연관 후보 0(충분한 증거 없음), 오류/경고 0.
- Windows Python 3.11 **57/57 PASS** run **39123343492**, 실제 Chromium regression **12/12 PASS** run **39123322129**, 사용자 지정 URL 실사이트 진단 성공 run **39123343463**. 실사이트 검증 코드 SHA **b7c707386034a14c44820709b4a13388dfcf7e7e**. 이후 문서 수정만 이뤄짐.
- 실사이트 전체 그래프의 정밀 탐지율·데이터 API lineage는 미검증. 상세한 원인/회귀/출력 차이: docs/DASHBOARD_LIVE_ACCURACY_2026-10-18.md.
- Step 2 원본 기준 9/9 PASS 판정 유지. 다음 실제 대시보드 확장 검증은 별도 지시 시 진행. 개인 Windows에 이번 개선사항이 적용됐는지는 미확인.
