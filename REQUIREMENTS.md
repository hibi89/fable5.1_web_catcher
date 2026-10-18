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
