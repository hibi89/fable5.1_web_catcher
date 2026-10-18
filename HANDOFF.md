# HANDOFF.md — Fable 5.1 Web Catcher / Step 3 CLI MVP

> 최신 인수인계(2026-10-18 KST). 아래 기존 Step 2 HANDOFF는 보존한 과거 이력이다. 최신 개발 기준은 이 Step 3 섹션 및 docs/STEP3_FINAL_ACCEPTANCE.md.

## ① 목표·용도·확정 요구·기술
권한 있는 공개·자체 사이트를 로컬 headed Chromium으로 사용자가 직접 탐색·로그인·조작하는 동안 기술·API·차트 근거를 수집한다. 사용자 원본 5 .1_step3.txt. Python 3.11+ Playwright, 기존 Step 1 static 및 Step 2 runtime 분석 유지. 자동 로그인·WAF 우회·LLM·웹 UI·영구 세션 저장은 범위 밖.

## ② 완료 기능·변경·결정 근거
--record/--max-duration(기본900초)/반복 --allow-origin 추가. --runtime과 중복 브라우저 실행 금지. input 스레드는 종료 신호만 송신하고 메인 Playwright 이벤트는 계속 처리. Enter·Ctrl+C·시간 만료·창 종료·EOF 처리. 새 비영구 context, 팝업/탭·main frame 문서 ID, origin 허용/응답 구조 구분, 클릭·변경 시각/구조 selector, 미수집 카운트, 원본 Step 2 collector 재사용. 차트 ↔ API 후보는 동일 page/navigation에서만 시계열 구조·DOM 갱신에 근거해 점수화하며 인과관계 확정이 아니다. cross-navigation 응답을 잃지 않도록 NetworkCollector에 완료 응답 점진적 JSON 구조 처리 도입. 새로운 네트워크 분석 엔진 대신 기존 구조 재사용 선택(유지보수·보안·회귀 영향 최소화).

## ③ 테스트 및 미검증
Windows Server 2022 Python 3.11 run 39126644441 → **60/60 PASS**. Ubuntu 24.04 실제 headed Chromium(Xvfb) run 39126644405 → **16/16 PASS**. 동일 Ubuntu 선택 공개 URL smoke **4/4 PASS**. 검증 소스 SHA 80f71d2b7de0f7a803872e76a616fe70f974e192, main merge SHA e28ea7f1f5a91d2f7a69160377558c6bc72e836d. 사용자 PC에서 사람의 실제 로그인·필터 변경은 미검증. 원본 Step 1 7/7·Step 2 9/9 완료 유지.

## ④ 완료·진행·대기·차단
Step 3 자동 fixture 기반 CLI MVP 완료(8/8 수용항목에 대한 자동 테스트 근거, 각 범위 docs/STEP3_FINAL_ACCEPTANCE.md). 사용자 로컬 Windows headed 실제 사이트 점검 **검증 대기**. Production 배포는 계획 및 구현 대상 아님. 사용자 원본을 모른 채 무단 기능 확장하지 않는다.

## ⑤ 오류 근거·원인·시도·재시도 주의
초기 headless와 다르게 headed Chrome 자원 정리 순서 오류 수정(Playwright stop 전 context/browser close). 종료 사유 덮어쓰기·finally 분기 들여쓰기 오류를 실브라우저 CI로 확인해 수정. 필터 후 차트는 DOM 관찰됐으나 최종 결과 누락됨 → 종료 시 스냅샷 항상 수행하도록 수정. JSON 구조가 페이지 이동 이후 보류될 수 있어 완료 응답을 이동 전에 점진적 요약하도록 수정. 마지막 실제 CI 60/16/4 성공. 이미 해소한 실패 재시도/무의미한 재배포 금지. SSRF 보호 없는 CLI를 외부 입력 URL 서버로 전환 금지.

## ⑥ 저장소·브랜치·SHA·주요 경로
비공개 hibi89/fable5.1_web_catcher main. 병합 PR #1. 코드: scan.py, scanner/record_scan.py, scanner/network.py, scanner/chart_mapping.py, scanner/report.py 및 기존 Step 2 모듈. 테스트: tests/test_record.py, tests/browser_record_check.py. 자동화: .github/workflows/runtime-python311.yml, windows-python311.yml. 기록: README.md, REQUIREMENTS.md, docs/STEP3_FINAL_ACCEPTANCE.md. 기능 테스트 소스 SHA 80f71d2b... / main 병합 SHA e28ea7f1....

## ⑦ 실행·배포·환경
배포 미적용(로컬 CLI). Vercel/Production URL 없음. 설치: python -m pip install -r requirements.txt; python -m playwright install chromium. 실행: python scan.py URL --record --max-duration 900 --out ./out/record. 기본 origin 외 필요시 --allow-origin 정확한 origin 추가. 결과 result.json/report.md. 테스트 명령: python -m pytest -q; Linux headed: xvfb-run -a python -m pytest -q tests/browser_record_check.py.

## ⑧ 원본·백업·인증·수정 금지
첨부 요구 파일 fable5.1_step1.txt, fable5.1_step2.txt, 5 .1_step3.txt 원본 우선. GitHub 기존 main 이력과 병합 PR을 원복 지점으로 사용, 강제 push 금지. 토큰·세션·cookie 값·입력값·원본 응답·HAR·storage_state·스크린샷·영상 저장 금지. 로그인은 사용자가 소유·권한 있는 사이트에서 직접만 수행. Playwright 비영구 context는 종료 시 파기.

## ⑨ 다음 작업·절차·완료 기준·승인
1순위: 사용자 Windows 로컬 git pull 후 --record 실제 사이트 로그인→필터 변경→Enter→result.json/report.md에서 해당 API와 차트 **연관 후보**·마스킹 확인(기능 검증 마지막 항목). 실제 데이터 연결 인과성은 결과만으로 확정할 수 없다. 필요 시 데이터/인증 처리 범위 확대, iframe 지원, 공개 서비스·배포는 별도 보안 설계와 사전 승인 필수.

## ⑩ 갱신 일시·검증 범위·문서 기준
2026-10-18 21:20 KST 부근. 기능 SHA 80f71d2b...에서 Windows/Ubuntu CI 직접 확인, main 병합 SHA e28ea7f1... 확인. 이후 HANDOFF/STATUS/BOOK 문서 커밋 HEAD는 따로 재조회하고 갱신한다. 사용자 로컬/임의 상용 사이트 완전 탐지율은 미검증.

---

# Step 2 HANDOFF — 보존 이력 (2026-10-18)

## ① 목표·용도·확정 요구·기술
공개 URL의 근거 기반 기술 스캔 CLI. Step 1 = requests/BeautifulSoup 정적 분석, Step 2 = Python 3.11+ Playwright Chromium 런타임 관찰. 사용자 원본 요구 fable5.1_step1.txt 및 fable5.1_step2.txt. 비공개 GitHub `hibi89/fable5.1_web_catcher` main. **Step 1 완료 7/7; Step 2 완료 기준 9/9 PASS (공개·무인증 CLI MVP 범위).**

## ② 완료 기능·변경·결정 근거
- 기존 Step 1 CLI 그대로 보존. Step 2 --runtime/--headed/--wait, 격리 컨텍스트·DOMContentLoaded·제한 스크롤·부분 실패 결과 및 종료 자원 정리.
- XHR/fetch 실제 메타데이터, 제한된 JSON 자료형 구조, GraphQL 후보, WS/SSE 연결의 값 없는 정보.
- 런타임 기술 전역 및 MutationObserver SVG/canvas 차트 후보, 실제 라이브러리/DOM 마커와 일반 후보 구분.
- 시차·시계열 JSON·DOM 마커를 조합한 보수적 chart↔API **연관 후보**, 경합 요청은 보류; HTML 내장 데이터/반복 검증 부재 한계 표시.
- 브라우저가 이미 로드한 같은 origin JS 문자열만 수동 검사, 최대 **10개 JS 파일 / 파일당 128KiB**. 새 경로 요청 없이 미검증 API 경로만 기록. `source_script`·`discovered_by=bundle_string` 포함.
- 데이터 모델: `api.endpoints` 실제 요청, `api.connections` 실제 WS/SSE, `api.candidates` JS 문자열 미검증 후보, `api.chart_candidates` 차트 연관 후보 및 `charts[].data_sources` ID 참조. 기존 정적 결과의 3개 api 키는 불변.
- 대안 선택: URL/probing·CDP 원시 추적보다 Playwright 사전 리스너와 완료된 응답 재사용 방식이 비용·보안·유지보수 우위. 추가 인증·사이트 조작·LLM 호출 없음.

추가 실사이트 개선(2026-10-18): 사용자 제공 공개 대시보드 URL의 #v-dash가 Chromium 탐색에서 손실되는 것을 발견해 브라우저 내 fragment 유지(결과 비저장)로 수정. generic SVG를 연결 DOM/100×70px 이상/도형 2개 이상일 때만 후보로 유지해 작은 아이콘을 억제. CSS의 서로 다른 퍼센트 높이/너비를 가진 반복 bar 그룹(4개 이상)을 css_bar_pattern_candidate(library unknown/confidence 0.5)로 추가. 실사이트 실제 실행: HTTP 200, XHR/fetch 2, 기존 차트 후보 14~15개에서 3개(큰 SVG 2 + CSS 막대 그룹 1), 에러 0. chart↔API 연결은 근거 부족으로 0. docs/DASHBOARD_LIVE_ACCURACY_2026-10-18.md에 증거 정리.

## ③ 테스트 명령·실제 성공/실패·미검증
- Windows 2022 Python 3.11: `python -m pytest -q` → **55/55 PASS**, run `39120274152`.
- Ubuntu 24.04 실제 Playwright Chromium: `python -m pytest -q tests/browser_runtime_check.py tests/browser_mapping_check.py tests/browser_bundle_check.py tests/browser_final_check.py` → **11/11 PASS**, run `39120274247`.
- 같은 Ubuntu 러너 공개 홈페이지 smoke: `python -m pytest -q -s tests/public_runtime_smoke.py` → **4/4 PASS**, example.com/python.org 각각 정적·런타임에서 HTTP 200/exit 0·결과 구조 검사.
- 최종 검증 소스 SHA: `e743e8c2b208940e66e03cfd6fc799031d7cc337`. 문서 HEAD는 검증 후 추가 변경으로 별도 재조회. 완료 기준 9개 및 한계 `docs/STEP2_FINAL_ACCEPTANCE.md`.
- 실제 상용 차트 라이브러리 통합은 일부 명시적 stub, 모든 실사이트 정확도·사용자의 Windows headed는 **미검증**.

실사이트 확장 검증: Windows Python3.11 57/57 PASS (run 39123343492), Ubuntu Chromium 12/12 PASS (run 39123322129), 대상 사이트 일회성 read-only 진단 PASS (run 39123343463). 검증 기능 HEAD b7c707386034a14c44820709b4a13388dfcf7e7e. 후속 커밋은 문서 변경만. 실제 전체 대시보드의 모든 시각화 탐지율과 데이터 lineage는 미검증.

## ④ 완료·진행·대기·차단·중단점
원본 Step 1 완료 및 Step 2 9/9 완료. **필수 남은 구현 없음.** 사용자 추가 요청이 없는 한 다음 단위 자동 개발·배포하지 않음. 실사이트 범위 확장, 실제 차트/라이브러리 정확도 검증, 배포는 별도 요청·승인 필요.

## ⑤ 오류 근거·시도·재시도 금지·대안
- 최종 보안 검수에서 원본 상한 10개와 과거 코드의 12개 불일치, 번들 후보가 api.bundle_candidates에 있었던 불일치, 차트 후보의 reasons 누락, HTML 내장 데이터 가능성 보고 누락을 확인. 한정된 소스/테스트 수정 및 최종 55/11/4 PASS로 검증. 이전의 중간 실패 CI를 최종 성공으로 오인하지 말 것.
- 한 번의 대형 GitHub 호출은 도구 호출 수 상한으로 중단됨. 소규모 변경 그룹별 트리 커밋으로 성공. 같은 대형 호출 반복 금지.
- 이전 컨테이너 Chromium localhost 접근은 ERR_BLOCKED_BY_ADMINISTRATOR 환경 정책 차단; 우회/반복 금지, GitHub Ubuntu Chromium fixture로 검증.
- Playwright decoded body 메모리 절대 상한 불가, 서버용 SSRF 방어 미구현. 이 CLI를 무신뢰 입력을 받는 외부 서비스로 공개하지 않는다.

## ⑥ 저장소·브랜치·SHA·주요 파일
`hibi89/fable5.1_web_catcher`, `main` (private). 최종 테스트 소스 SHA `e743e8c2b208940e66e03cfd6fc799031d7cc337`. 직전 단위 6 문서 HEAD `1184a4fc6a18ba377123406f30cdae535d686b9d`로 이력 확인 가능. `scan.py`, `scanner/runtime_scan.py`, `scanner/network.py`, `scanner/connections.py`, `scanner/runtime_detect.py`, `scanner/chart_mapping.py`, `scanner/bundle_scan.py`, `scanner/report.py`, `tests/browser_final_check.py`, `tests/public_runtime_smoke.py`, `docs/STEP2_FINAL_ACCEPTANCE.md`.

## ⑦ Production URL·Vercel·실행 명령·환경
배포 미적용(로컬 CLI), Production/Vercel URL 없음. 설치: `python -m pip install -r requirements.txt` 및 `python -m playwright install chromium`. 정적: `python scan.py https://example.com --out ./out/static`. 런타임: `python scan.py https://example.com --runtime --wait 10 --out ./out/runtime`; `--headed`는 표시 환경에서 선택. 결과는 지정 폴더의 result.json 및 report.md. 테스트 명령 ③ 참조.

## ⑧ 원본·백업·인증 관리·수정 금지
사용자 첨부 fable5.1_step1.txt/fable5.1_step2.txt가 최종 요구 원본. GitHub main이 코드 기준, git history로 복구 가능, 강제 push 금지. tests/test_static.py.bak 보존. API token, URL 인증 쿼리, cookie, raw response/JS, HAR, storage state, 비밀 로그 저장 금지. 로그인·WAF 우회·임의 경로 probing 금지.

## ⑨ 다음 작업 우선순위·완료 기준·승인
**Step 2는 원본 기준 9/9 완료 판정.** 첫 실사이트 정확도 개선까지 별도 확인했지만 모든 차트 형식의 완전한 탐지나 사용자 Windows 최신 개선 코드 설치는 입증하지 않았음. 향후 더 높은 실제 사이트 정확도/사용자 로컬headed/서버 배포는 새 범위로 취급하고 사용자 지시를 받은 뒤 시작. 배포 시 보안 격리·SSRF·리소스 상한을 새로 설계해야 한다. 지금 단계에서 추가 개발·배포 필수 작업 없음.

## ⑩ 갱신 일시·검증 범위·문서 기준 커밋
2026-10-18 KST. 최종 CI run 39120274152 (Windows 55 PASS), 39120274247 (Chromium 11 + 공개 사이트 4 PASS), 소스 SHA e743e8c2b208940e66e03cfd6fc799031d7cc337. 문서 커밋 HEAD 및 중앙 BOOK.md 갱신은 최종 재조회 확인 후 상태 보고. 실제 사이트 전체 탐지 정확도와 사용자 개인 PC는 미검증.
