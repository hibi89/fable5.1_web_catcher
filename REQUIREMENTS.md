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

Step 2 단위 1~5 구현: 격리 Chromium·XHR/fetch 및 제한 JSON 구조·WS/SSE·차트 DOM 후보·차트↔API 보수적 연관 후보. 일반 SVG/canvas와 시간 근접은 실제 데이터 연결의 증거가 아니며, 경합 API가 있으면 연결 보류. confidence는 비확률적 휴리스틱. **JS 번들 후보 및 전체 Step 2 검수 미완료**.
