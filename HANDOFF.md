# HANDOFF.md — Fable 5.1 Web Catcher / Step 2 단위 2

## 1. 목표·용도·확정 요구·기술
공개 URL의 정적 HTTP 기술 근거 및 격리 브라우저 런타임 관찰 CLI. Step 1: requests, BeautifulSoup, 자체 핑거프린트. Step 2: 사용자 원본 fable5.1_step2.txt, Python 3.11+, Playwright Chromium, 근거 기반 동적 관찰. Step 2 전체가 아니라 **단위 1~2만 구현/검증 완료**. 사이트 디자인 복제나 서버 내부·DB 추출을 주장하지 않음.

## 2. 완료 기능·변경·결정 근거
- Step 1 정적 명령 및 스키마 유지. Step 2 단위 1의 --runtime, --headed, --wait, 격리 Chromium, DOMContentLoaded, 제한 스크롤, 부분 결과·자원 정리 유지.
- 단위 2: scanner/network.py에서 실제 관찰한 xhr/fetch request·response·requestfinished·requestfailed 이벤트를 이동 전에 등록. 각 endpoint id, 마스킹된 URL, HTTP method, resource type, UTC epoch ms의 요청/응답 시각, status, content-type, GraphQL 후보(관찰 경로 또는 MIME), JSON 구조·본문 분석 상태를 기록.
- 응답 원문/요청 본문/헤더 인증정보/쿠키는 결과에 보관하지 않음. 완료된 응답에서 Content-Length가 명시된 128KiB 이하 JSON만 최대 20개 구조 분석. 원시 값이 아닌 필드명·자료형, 객체 최대 24키, 배열 표본 최대 3, 깊이 5. 전체 endpoint 최대 150개. 위험한 JSON 키는 마스킹. 응답 크기 불명·과대·비JSON·실패에도 endpoint 보존.
- scanner/runtime_scan.py에 collector 연결 및 종료 직전 finalize, scanner/report.py에 실제 API 섹션 추가. tests/fixture_server.py의 브라우저 fixture: 지연 JSON chart API, 시각이 비슷한 무관한 API, 큰 응답, 크기 불명, 비JSON, 잘못된 JSON, 실제 POST /graphql. tests/test_network.py 단위 4건; tests/browser_runtime_check.py 1건 추가 총 3건. runtime CI 트리거 업데이트.
- 설계 대안: (A) 별도 브라우저 프로그램은 기존 static 모델/마스킹/보고 중복, (B) 기존 모델 재사용+수동 이벤트 컬렉터 분리는 유지보수·비용 면에서 유리해 B 채택. 원본 데이터 비저장과 관찰/분석 책임을 분리.

## 3. 테스트 명령·성공/실패 수·검증/미검증
- 일반/Windows Python 3.11: python -m pytest -q → **34/34 PASS**, 0 FAIL, 6.78초. GitHub Actions run **39115403591**, conclusion success, head **67a8c4132d115e33c3ad0501b642549122eb2e61**. 기존 Step 1 26건 및 단위 1 4건 포함.
- 실제 Chromium/Ubuntu Python 3.11: python -m pytest -q tests/browser_runtime_check.py → **3/3 PASS**, 0 FAIL, 6.60초, run **39115403678**, conclusion success, 동일 head. 브라우저가 발생시킨 API 7종·응답 상태·JSON 구조·GraphQL POST·비밀값 비저장 및 CLI subprocess 검사.
- 개발 환경의 보조 순수 Python 단위 4/4 PASS. 실제 브라우저 실험은 격리 GitHub Actions Chromium으로 검증(사용자 PC 실행은 미검증).
- **미검증:** 공개 실사이트 런타임 정확도, 다양한 사이트의 브라우저 제한, Windows 실제 headed UI, WebSocket/SSE, 차트/번들 및 차트↔API 결합, 실제 사용자의 OS에서 실행.

## 4. 완료/진행/대기/차단·중단 지점
- Step 1 원본 요구 완료 기준 7/7 PASS, 과거 Windows/Linux/macOS 각 26/26 PASS 및 두 공개 사이트 JSON/Markdown/evidence 무결성 PASS (docs/STEP1_FINAL_ACCEPTANCE.md).
- Step 2 단위 1: Chromium 브라우저 실행 기반 완료. 단위 2: xhr/fetch 및 JSON 구조 수집 완료. **Step 2 전체 미완료**.
- 다음 단위: WebSocket 연결/프레임 수 및 SSE 연결 메타데이터(스트림 body 미독취)·유한 시간 내 종료를 로컬 fixture로 검증. 사용자 다음 ㄱ 전 미착수.

## 5. 오류 근거·원인·시도·재시도 금지·대안
- 단위 2 로컬 순수 Python 테스트 첫 1/4 실패는 깊이 5 경계 테스트가 원시 string을 truncation으로 잘못 기대한 테스트 명세 문제. 객체 중첩을 6단계로 고친 뒤 4/4 PASS. 실측 CI Windows 34/34 및 Chromium 3/3 PASS.
- 이전 컨테이너의 시스템 Chromium은 net::ERR_BLOCKED_BY_ADMINISTRATOR로 localhost 접근 실패. 동일 환경 우회 금지. 독립 GitHub Actions 실제 Chromium fixture로 대체해 성공.
- Playwright 응답 API는 gzip/deflate decoding 시 순간 메모리 사용의 완전한 상한을 보장하지 못함. 크기 미지정/큰 응답은 아예 본문 조회하지 않지만, 길이 헤더와 실제 디코딩 메모리가 다를 수 있어 향후 고위험 환경에는 추가 격리 필요. 서버용 SSRF 방어 프록시는 구현 안 됨.

## 6. 저장소·브랜치·SHA·주요 경로
비공개 hibi89/fable5.1_web_catcher / main. 기능 및 테스트 검증 대상 SHA **67a8c4132d115e33c3ad0501b642549122eb2e61**. 선행 커밋 d5e816be412e778983323b5421af4090415ae12c(scanner/network.py), cc0ca9aeea2b222c5dbd301872cda0e4815e975a(integration), 67a8c4132d115e33c3ad0501b642549122eb2e61(unit tests). 핵심 파일 scan.py, scanner/network.py, scanner/runtime_scan.py, scanner/report.py, scanner/sanitize.py, tests/fixture_server.py, tests/test_network.py, tests/browser_runtime_check.py, README.md, requirements.txt.

## 7. Production URL·Vercel 프로젝트·실행 명령·환경
배포 미적용 (로컬 CLI; Vercel/Production URL 없음). 환경 Python 3.11+, Playwright Chromium. 설치: python -m pip install -r requirements.txt; python -m playwright install chromium. 정적: python scan.py https://example.com --out ./out/static. 런타임: python scan.py https://example.com --runtime --wait 10 --out ./out/runtime. 별도 headed: 위 명령에 --headed. 기본 테스트: python -m pytest -q. Chromium: python -m pytest -q tests/browser_runtime_check.py. GitHub Actions workflow runtime-python311.yml은 자체 코드/fixture/test push 및 수동 dispatch에 반응, contents: read.

## 8. 원본·백업·인증 관리·수정 금지
확정 요구는 대화 첨부 fable5.1_step1.txt / fable5.1_step2.txt. GitHub main이 소스·버전 단일 기준, 구버전 commit으로 복구 가능. 로그인·폼 제출·자동 API introspection·비허가 크롤링·WAF 우회 금지. 토큰·.env·HAR·쿠키·인증헤더·원본 응답/요청 본문·브라우저 storage state 저장 금지. tests/test_static.py.bak 무단 삭제 금지.

## 9. 다음 작업 우선순위·절차·완료 기준·승인 사항
다음 ㄱ: **Step 2 단위 3 WebSocket + SSE 연결의 안전한 메타데이터 수집**. 실제로 열린 ws/wss URL(마스킹), 프레임 수, 시간과 SSE 응답 content-type/시각만 기록하며 프레임 내용·스트림 body/토큰을 저장하지 않는다. EventSource가 끝나지 않는 로컬 fixture에서 종료가 제한 시간 내 이뤄지고 기존 API 수집 회귀 34/3 유지되는지 검증. 런타임 차트 라이브러리·차트↔API 연관·JS 번들은 이후 단위로 미루고, 새 ㄱ 없이 선행 작업하지 않는다.

## 10. 갱신 일시(KST)·확인 시점·검증 범위·문서 기준 커밋
2026-10-18 18:28 KST 테스트 검증. source/test 커밋 **67a8c4132d115e33c3ad0501b642549122eb2e61**. Windows 34/34 run 39115403591, Chromium 3/3 run 39115403678. 문서 자신의 커밋 SHA는 커밋 후 branch HEAD 재조회로 확정한다. 실사이트/사용자 PC/Step 2 전체 검증 미완료.
