# REQUIREMENTS.md — Fable 5.1 Web Catcher Step 1

소스 요구사항: 대화 첨부 `fable5.1_step1.txt` (2026-10-18).

## 확정 요구

1. Python 3.11+, `requests`, `beautifulsoup4`, `pytest`, argparse; 키·LLM·DB·Docker 필요 없음.
2. `python scan.py URL [--out PATH] [--timeout SECONDS]`로 JSON/한국어 MD 결과.
3. 허용 헤더/쿠키 이름/meta generator/자산 URL/HTML 프레임워크 구조/CSP 도메인 및 경고.
4. 원격 규칙 다운로드 금지. 16개 기술 핑거프린트, 근거 ID, 비확률적 confidence, 버전은 확실할 때만.
5. 개인정보/토큰 쿼리·쿠키값·userinfo·원본 HTML 저장 금지. 리다이렉트/크기/타임아웃/TLS 보호.
6. offline fixture, 정적·추정·실패·민감정보 스키마 검증. 테스트 실행 증거 있는 경우에만 PASS.
7. Step 1에서 Playwright, Record, LLM, 웹 UI 제외.

## 범위 밖

- 사이트 내부 서버 코드, DB, API 호출 그래프, 동적 JS 추적, 로그인, 여러 페이지 크롤링.
- 외부 배포 또는 Vercel 연동.


## Step 2 신규 사용자 요구 (2026-10-18)

원본: 대화 첨부 `fable5.1_step2.txt`. Chromium + Playwright로 실행 관찰, XHR/fetch·WebSocket/SSE 연결의 메타데이터, JSON 구조, 런타임 차트 라이브러리, 차트↔API **연관 후보**, 현재 로드된 동일 origin JS 번들 문자열을 근거로 분석한다. 비밀값·원본 응답·storage state·HAR 저장 금지. 자동 로그인·클릭·폼 제출·우회·무작위 API 탐색 금지. Step 1의 정적 분석은 그대로 유지한다.

**Step 2 원본 완료 기준 9/9 PASS (2026-10-18).** 단위 1~6 구현 후 최종 통합/보안 fixture 검증과 실제 공개 홈페이지 2곳 정적·런타임 구조 검사 완료. 관찰 API=api.endpoints, WebSocket/SSE=api.connections, JS 문자열 미검증 경로=api.candidates (source_script, discovered_by=bundle_string), 차트↔API 연관 후보=api.chart_candidates로 분리. 번들 최대 10개·파일당 128KiB, 원본 코드/데이터 저장 금지. 실제 상용 차트 라이브러리 정확도·사용자 PC/임의 사이트 성능·서버 SSRF 차단은 범위/검증 밖. 상세 근거 docs/STEP2_FINAL_ACCEPTANCE.md.


## Step 3 사용자 원본 요구 (2026-10-18 제공 파일 5 .1_step3.txt)

사용자가 직접 로그인·클릭·필터 변경하는 로컬 headed Record. --record, --max-duration 기본 900초, 반복 --allow-origin, --runtime과 중복 실행 금지 및 기존 CLI 보존. Enter·Ctrl+C·시간 만료·브라우저 종료 처리. 입력 감시 스레드가 종료 신호만 보내고 Playwright 생성 스레드는 이벤트를 처리함. Step 2의 네트워크·차트·JS 번들 수집기를 재사용하며 원본 자료형 분석·크기 제한 유지. 탭·문서 ID, 허용 origin 격리, iframe 미지원 경고, click/change의 시각·구조적 selector만 허용. 키입력·폼값·쿠키·인증 정보·원문·HAR·스크린샷·세션 저장 금지. 긴 수집의 건수/메모리 상한과 생략 경고. 회귀 및 실제 Chromium 테스트 확인 전 Step 3 완료 주장 금지. LLM·웹 UI·로그인 자동화·세션 재사용 금지.
