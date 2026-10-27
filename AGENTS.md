> **2026-10-28 해총 전 저장소 최상위 공통 운영 공지 (소유자 승인):** [개발 가속·로컬검증·병목제거 통합 정본](https://github.com/hibi89/hackathon-command-center-2026/blob/main/docs/DEV_ACCELERATION_AND_VERIFICATION_20261028.md) 확인. 현 시점 활성은 **KIC(+DL)·PayPal·UGREEN·LA 4개**만이다. 이 프로젝트는 **임시 개발 대기**(폐기·기존 기록 삭제 아님)로, 소유자의 재개 지시 없이 `ㄱ`만으로 신규 개발·CI·배포를 진행하지 않는다. 활성 프로젝트 일반 기능 구현은 **GPT-6 Instant**, 최초 설계·난제·해총 독립검수는 높은 추론. 파일 단위 GitHub 반복·다수 상태 문서 갱신·동일 SHA 반복 조회를 줄이고, 기능 단위 검증/정확한 PASS·FAIL·SKIP·커밋 SHA만 보고한다. 기존 제품 설계 동결, 외부 승인, 보안·고객데이터/원본·출시 게이트는 그대로 유지. 이 공지는 운영 통지이며 기능 완성 선언이 아니다.

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
