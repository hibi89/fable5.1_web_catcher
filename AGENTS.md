# AGENTS.md — Fable 5.1 Web Catcher

- 소스 기준: `hibi89/fable5.1_web_catcher`, `main`. 작업 시작 시 최신 GitHub HEAD 및 문서를 먼저 확인한다.
- 목표는 공개 단서 기반 기술 스캔 CLI의 정확한 근거 기록이다. 탐지 결과는 추정이며 소스/DB 추출이라고 주장하지 않는다.
- 자동 로그인, 폼 제출, 임의 엔드포인트 탐색, 관리자/백업/비밀 경로 probing 금지.
- 민감 쿼리, userinfo, 쿠키·인증정보 노출 금지. Step 1은 정적 1페이지 GET 및 허용 리다이렉트만 수행한다.
- 변경 시 비밀값 비노출 테스트, 오프라인 fixture 테스트, CLI 정상·실패 종료 코드를 검사한다.
- Playwright, Record, LLM, 웹 UI는 Step 1 범위 밖이다.
- 실제 서비스/외부 URL 감지는 구조 검증만 하고 특정 기술 탐지를 강제하지 않는다.
- 코드·문서 변경 완료 시 `STATUS.md`, `HANDOFF.md`, 중앙 `BOOK.md`를 실제 검증 상태로 갱신한다.

- Step 2 사용자 지침 `fable5.1_step2.txt` 수령(2026-10-18). `--runtime`은 브라우저 격리·수동 상호작용 금지·비밀정보 비저장·부분 결과 보존이 필수. 기존 정적 CLI는 유지. Step 2는 단위별 구현하며 통합 완료로 오인하지 말 것.

- Step 3 사용자 지침 `5 .1_step3.txt` 수령(2026-10-18). --record는 사용자 주도 headed 관찰만 허용한다. 승인 origin 외 DOM/JSON 구조 분석 금지, 인증/입력/세션/원문 저장 금지. 타이밍 차트↔API 후보는 인과관계 확정이 아니다. 서버 공개 배포는 SSRF 격리 전 금지. Step 1/2 회귀 보존, CI 근거는 `docs/STEP3_FINAL_ACCEPTANCE.md`.
