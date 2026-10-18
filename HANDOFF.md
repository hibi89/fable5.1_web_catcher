# HANDOFF.md — Fable 5.1 Web Catcher / Step 2 단위 3

## ① 목표·용도·확정 요구·기술
대상: 공개 URL의 근거 기반 기술 관찰 CLI. Step 1은 Python requests/BeautifulSoup 정적 탐지, Step 2는 사용자 첨부 fable5.1_step2.txt를 근거로 Python 3.11+ Playwright/Chromium을 통한 동적 요청·연결·차트 관찰. 이번 ㄱ은 **단위 3: 실제 WebSocket/SSE 연결 메타데이터 수집** 한 단위. Step 2 전체 미완료. 사이트 소스·DB 재현을 보장하지 않음.

## ② 완료 기능·변경·결정 근거
- Step 1 정적 CLI는 보존. 단위 1 격리 Chromium/--runtime/--headed/--wait/partial 결과와 단위 2 XHR/fetch 엔드포인트·제한 JSON 구조·GraphQL 후보 유지.
- 신규 scanner/connections.py: 페이지 이동 **전** WebSocket 이벤트와 일반 response 이벤트를 수동 등록해 api.connections에 보관. WebSocket은 id, 마스킹 URL, 관찰 epoch ms, 송/수신 프레임 수, 연결 종료 시각(관찰 때만), 오류 발생 boolean. SSE는 Content-Type text/event-stream 실제 응답만 id, URL, HTTP status, MIME, epoch ms 기록.
- WebSocket frame payload·socketerror 내용, SSE 이벤트/본문, 인증 헤더·쿠키·HAR·storage state는 읽거나 저장하지 않음. 프레임 이벤트는 카운트만 수행하고 내용은 무시. 최대 연결 60, 방향별 프레임 수 포화 1,000,000.
- scanner/runtime_scan.py에 collector attach/finalize, scanner/report.py에 연결 섹션, tests/fixture_server.py에 stdlib WebSocket handshake/두 서버 프레임·클라이언트 송신 및 종료하지 않는 SSE, tests/test_connections.py 단위 4개, tests/browser_runtime_check.py 실제 Chromium 통합 1개 추가, README/CI workflow 갱신.
- 비교: CDP 원시 프레임 추적은 복잡도·민감정보 노출 위험이 크다. Playwright 공식 이벤트로 메타데이터만 수집하는 기존 스키마 확장이 비용·유지보수·보안에 유리. 실제 사이트를 클릭·로그인·우회하는 코드는 없음.

## ③ 테스트 명령·성공/실패 수·검증/미검증
- python -m pytest -q → Windows Server 2022 Python 3.11 GitHub Actions **38/38 PASS** 0 fail, run 39116413660, 최종 대상 SHA f8a4f5dc50cdb4993b0161abb80193e46d00f534. Step 1 기존 26개 포함.
- python -m pytest -q tests/browser_runtime_check.py → Ubuntu 24.04 / Python 3.11 / 실제 Playwright Chromium, **4/4 PASS** 0 fail, run 39116413676, 동일 SHA. 신규 테스트에서 WebSocket 양방향 프레임 수 >=1, SSE HTTP 200/MIME·URL, 비밀 테스트값 비노출, 완료되지 않은 SSE에서도 제한 시간 내 종료 검증.
- 최초 코드 SHA a7abd603e8bb1cf33797ed5e32fae459bcae3273의 브라우저 run 39116326072는 **3 PASS / 1 FAIL**: 기존 단위 2 테스트가 runtime.scope 문자열을 이전 값 network_metadata_only로 고정한 회귀 테스트 기대값 불일치. 실사용 신규 WebSocket/SSE 시험은 그 실행에서도 성공. 기존 테스트 기대값만 새로운 network_and_connections_metadata로 고치고 SHA f8a4f5dc50cdb4993b0161abb80193e46d00f534의 CI에서 4/4 PASS 확인.
- 미검증: 사용자 PC Windows --headed, 임의 실사이트 프레임/스트림 정확도, 실제 API-차트 매핑, 번들 문자열, 모든 OS 브라우저 차이. Step 2 전체 완료 미판정.

## ④ 완료/진행/대기/차단·중단 지점
- Step 1 원본 7/7 완료, 이전 3 OS 각 26/26 PASS·공개 두 사이트 정적 smoke 성공.
- Step 2 단위 1 브라우저 실행, 단위 2 XHR/fetch+JSON 구조, **단위 3 WebSocket/SSE 연결** 구현·Chromium 테스트 통과.
- 진행 중/대기: 런타임 기술 라이브러리 추적, DOM/MutationObserver 차트 후보, 차트↔실제 API 근거기반 연관 후보, 동일 origin JS 번들, 전체 보고서·보안 최종 승인.
- 중단점: 다음 사용자 ㄱ 전 단위 4 미착수.

## ⑤ 오류 근거·원인·시도·재시도 금지·대안
- 초기 브라우저 1 FAIL은 스키마 범위 라벨 변경에 비해 기존 assertion이 갱신되지 않은 회귀 검사 문제, 정확한 라벨 갱신으로 해결 후 4/4 PASS. 동일 코드 수정 반복 불필요.
- 이전 개발 컨테이너의 시스템 Chromium localhost 접근은 net::ERR_BLOCKED_BY_ADMINISTRATOR. 접근 정책 우회하지 말고 GitHub Actions Ubuntu Chromium fixture를 검증 환경으로 이용.
- 완전한 메모리 상한이 보장되지 않는 Playwright의 JSON body API 한계는 단위 2에서 명시. 연결 이벤트는 프레임 내용을 읽지 않음. 외부에 임의 URL 스캔 서비스를 공개할 때 SSRF 보호 없는 현재 CLI를 그대로 서버에 노출하지 말 것.

## ⑥ 저장소·브랜치·SHA·주요 경로
비공개 hibi89/fable5.1_web_catcher / main. 검증한 기능 SHA f8a4f5dc50cdb4993b0161abb80193e46d00f534. 신규 수집 코드 커밋 27e3fbda676e8bc748628f23f8de024d8399789f, 통합 커밋 a7abd603e8bb1cf33797ed5e32fae459bcae3273, 회귀 assertion 수정 f8a4f5dc50cdb4993b0161abb80193e46d00f534. scanner/connections.py, scanner/network.py, scanner/runtime_scan.py, scanner/report.py, scan.py, tests/fixture_server.py, tests/test_connections.py, tests/test_network.py, tests/browser_runtime_check.py, README.md.

## ⑦ Production URL·Vercel 프로젝트·실행 명령·환경
배포 미적용(로컬 CLI). Vercel 프로젝트/Production URL 없음. Python 3.11+, pip install -r requirements.txt, python -m playwright install chromium. 기본 정적: python scan.py https://example.com --out ./out/static. 런타임: python scan.py https://example.com --runtime --wait 10 --out ./out/runtime. headed(화면 환경에서만): python scan.py https://example.com --runtime --headed --wait 10 --out ./out/runtime. 테스트: python -m pytest -q 및 python -m pytest -q tests/browser_runtime_check.py. runtime GitHub Actions는 관련 소스·fixture·workflow push 또는 수동 dispatch에서 실행, 토큰 contents: read.

## ⑧ 원본 위치·백업·인증 관리·수정 금지
요구 원본: 현재 대화의 fable5.1_step2.txt, 이전 대화 fable5.1_step1.txt. GitHub main을 단일 소스 기준으로 사용. 기존 안정 버전 SHA 9ef6ae952a5fd4976c627ea62d47f7a73ada4395(단위 2 완료)로 Git history에서 복구 가능하며 force push 금지. 인증 토큰·개인 데이터·쿠키·원본 응답/HAR/storage state GitHub 업로드 금지. tests/test_static.py.bak 보존. 수집 fixture의 비밀 문자열은 테스트 전용이며 출력 파일 비노출 검사 통과.

## ⑨ 다음 작업 우선순위·절차·완료 기준·승인 사항
다음 ㄱ의 확정 단위: **Step 2 단위 4 — 실행 중 런타임 기술 흔적과 차트 DOM 후보 수집**. Next.js/Nuxt 및 Chart.js/Highcharts/ECharts/Plotly/ApexCharts/D3의 알려진 전역 속성만 읽기 전용 확인, 실제 차트 인스턴스와 라이브러리 로드 분리. DOM/MutationObserver로 SVG/canvas 차트 후보의 첫 관찰·관련 attribute 업데이트 관찰, canvas만으로 라이브러리 확정하지 않음. 내부 URL 탐색·사이트 데이터 변경·무작위 window 순회 금지. localhost fixture + 단위/Chromium 회귀 통과를 완료 기준으로 한다. 차트↔API 점수화와 번들 문자열 검사는 **다음 단위 이후**, 새 ㄱ 전 미착수.

## ⑩ 갱신 일시(KST)·확인 시점·검증 범위·문서 기준 커밋
2026-10-18 18:43 KST CI 최종 결과 확인. 검증된 기능 SHA f8a4f5dc50cdb4993b0161abb80193e46d00f534, Windows 39116413660 38 PASS, Chromium 39116413676 4 PASS. 프로젝트 문서의 HEAD SHA는 문서 커밋 후 GitHub main 재조회로 확인; 인수인계 작성만으로 전체 Step 2 완료라고 주장하지 않음.
