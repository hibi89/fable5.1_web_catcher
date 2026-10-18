# HANDOFF.md — Fable 5.1 Web Catcher Step 2 단위 4

## ① 목표·용도·확정 요구·기술
공개 URL의 근거 기반 정적/동적 기술 분석 CLI. Python 3.11+, requests, BeautifulSoup, Playwright/Chromium. 사용자 원본 fable5.1_step1.txt와 fable5.1_step2.txt. Step 1은 완료, Step 2는 1~4단위만 완료. 실제 사이트 코드·DB 복원 아님.

## ② 완료 기능·변경·결정 근거
정적 기본 CLI 및 앞선 런타임 기능 유지. 새 scanner/runtime_detect.py: 페이지 이동 전 JS MutationObserver 설치, 초기 및 추가 SVG/canvas/관련 속성 변경(상한 80 후보·1200 mutation), 첫 관찰 및 업데이트 UTC epoch ms, 구조적 selector, 휴리스틱 confidence, 라이브러리 근거 및 빈 data_sources 기록. Next.js, Nuxt, Highcharts, Chart.js, ECharts, Plotly, ApexCharts, D3의 명시적 전역/마커만 읽기 전용 확인. Chart.instances/Highcharts.charts 개수를 확인할 수 있는 경우와 단순 라이브러리 로드를 구분. D3 존재·canvas/svg만으로 차트 확정 금지. runtime_scan.py 이동 전 설치/종료 관찰, report.py 보고서, fixture·일반/브라우저 테스트 및 README/CI 연동.
대안 비교: CDP 직접 내부 추적은 개발 비용·노출 위험 높음, 알려진 속성+DOM 후보 방식은 낮은 비용과 기존 스키마 재사용에 유리. 인스턴스 확인 불가능한 라이브러리를 억지로 확정하지 않음.

## ③ 테스트 명령·성공/실패 수·검증/미검증
python -m pytest -q → Windows Python 3.11 42/42 PASS, GitHub Actions run 39117164191. python -m pytest -q tests/browser_runtime_check.py → Ubuntu 실제 Playwright Chromium 5/5 PASS, run 39117164160. 검증 코드 SHA a1a7ae57675c36e2b7673e2156e405ccb70d9ecd. 기존 Step 1 26개 회귀 포함. test stub(Highcharts/Chart.js/D3, Next marker), 일반 SVG/canvas, 지연 SVG 마커·속성 갱신, ECharts DOM 마커, 비밀값 마스킹 검증. **실제 라이브러리 패키지 통합, 공개 사이트·사용자 PC, Windows headed 미검증**.

## ④ 완료/진행/대기/차단·중단 지점
Step 1 원본 완료 조건 7/7 PASS(기존 3 OS 각 26 PASS·Python.org/example.com 정적 smoke). Step 2 단위 1 격리 Chromium, 2 실제 XHR/fetch/JSON 구조, 3 WebSocket/SSE, **4 런타임 기술·차트 DOM 후보** 완료. 차트↔API 후보 점수화, 동일 origin JS 번들 문자열 분석, 최종 통합 검증 대기. 새 ㄱ 전 다음 단위 작업 미착수.

## ⑤ 오류 근거·원인·시도·재시도 금지·대안
초기 통합 소스 SHA 5621c0e58353c358faa6531df61e1e3dd37d754f의 Chromium run 39117073731은 4 PASS/1 FAIL. SVG tagName 대소문자 검사 오류로 SVG 누락. localName/tagName 소문자 정규화한 SHA a1a7ae57675c36e2b7673e2156e405ccb70d9ecd에서 재검증 5/5 PASS. 이전 로컬 컨테이너 Chromium은 관리자 차단(net::ERR_BLOCKED_BY_ADMINISTRATOR); 우회/반복 금지, GitHub 실제 Chromium 사용. canvas 픽셀 변경은 MutationObserver로 알 수 없고 DOM 첫 관찰은 렌더 완료 시각 아님.

## ⑥ 저장소·브랜치·SHA·주요 경로
hibi89/fable5.1_web_catcher (private), main. 검증 소스 SHA a1a7ae57675c36e2b7673e2156e405ccb70d9ecd. 새 모듈 scanner/runtime_detect.py, 기존 scanner/runtime_scan.py, scanner/network.py, scanner/connections.py, scanner/report.py, tests/test_runtime_detect.py, tests/browser_runtime_check.py, tests/fixture_server.py. 이전 안정 단위 3 문서 SHA cb6457c179e1d9f78daec174862f58280a16d235로 이력 복원 가능.

## ⑦ Production URL·Vercel·실행 명령·환경
배포 미적용(로컬 CLI), Vercel URL·Production SHA 없음. python -m pip install -r requirements.txt; python -m playwright install chromium; python scan.py https://example.com --runtime --wait 10 --out ./out/runtime; 정적은 --runtime 없이. 화면 환경에서 --headed 가능. 테스트 명령 위 ③ 참고. GitHub Actions contents: read.

## ⑧ 원본·백업·인증 관리·수정 금지
GitHub main이 코드 기준, fable5.1_step1.txt/fable5.1_step2.txt가 확정 요구 원본. 비밀값·원본 HTML·인증 헤더·쿠키·HAR·storage state 저장 금지, 테스트용 문자열도 출력 검증. 임의 백업/비밀 경로 요청·로그인·WAF 우회 금지. tests/test_static.py.bak 보존; force push 금지. 서버용 SSRF 차단 프록시 미구현으로 공개 URL 스캔 서비스로 무단 배포 금지.

## ⑨ 다음 작업 우선순위·절차·완료 기준·승인 사항
다음 ㄱ 한 단위는 **Step 2 단위 5: 차트↔관찰 API 연관 후보**. 양쪽 UTC epoch ms, JSON 구조의 수치/시계열 특성, 반복 일관성·동시 다중 요청 경쟁을 함께 평가. ±500ms 단독으로 확정 금지. confidence/reasons/limitations과 '연관 후보' 표기, 근거 부족하면 data_sources 빈 배열. 무관한 근접 요청이 연결되지 않도록 로컬 fixture 및 Chromium 회귀 테스트. JS 번들 분석은 그 이후.

## ⑩ 갱신 일시(KST)·확인 시점·검증 범위·문서 기준 커밋
2026-10-18 KST. Windows run 39117164191 42 PASS, Chromium run 39117164160 5 PASS 검증 시점 2026-10-18 18:55 KST. 기능 기준 SHA a1a7ae57675c36e2b7673e2156e405ccb70d9ecd. 문서 자체 커밋 SHA는 GitHub 재조회로 확인할 것. Step 2 전체 완료 아님.
