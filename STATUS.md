# STATUS.md — Fable 5.1 Web Catcher

## 2026-10-18 현재
- **Step 1 완료 100%**: 원문 기준 7/7. 기존 정적 CLI·26개 회귀 테스트 보존. Windows/Linux/macOS Python 3.11 각 26/26, Python.org 및 example.com 정적 JSON/Markdown/evidence 무결성 PASS. docs/STEP1_FINAL_ACCEPTANCE.md.
- **Step 2 단위 1~2 완료, Step 2 전체 진행 중**: 단위 1 격리 Chromium/CLI, 단위 2 실제 xhr/fetch 네트워크 메타데이터와 제한된 값 없는 JSON 구조 요약/GraphQL 후보. SSE·WebSocket·차트/번들·차트↔API 연관 미구현. 원본 fable5.1_step2.txt 수령.
- 저장소 hibi89/fable5.1_web_catcher, main. 기능 테스트 근거 SHA 67a8c4132d115e33c3ad0501b642549122eb2e61. 배포 미적용(로컬 CLI).

## 구현
- 기존 --runtime/--headed/--wait 10초 기본 유지. scanner/network.py 신규 도입, 런타임 페이지 이동 **전** fetch/XHR 리스너. api.endpoints에서 id, 마스킹 URL, method, 리소스 타입, UTC epoch ms 시각, status, MIME, GraphQL 여부 후보, 본문 구조/스킵 이유를 기록. api.candidates/connections·charts는 계속 빈 상태.
- JSON 값·요청 본문·인증 헤더/쿠키/원본 응답/HAR 미저장. endpoint 150, JSON 분석 20, 헤더 선언 128KiB, 구조 깊이 5·객체 키 24·배열 표본 3 상한. 크기 불명·초과·비JSON·응답 실패는 endpoint 보존하되 본문 분석 생략. Playwright body API 자체의 완전한 메모리 상한 미보장.
- 보고서에 관찰 endpoint 목록 및 JSON 구조 타입 요약 추가. 테스트 서버는 지연 차트 데이터·유사 시각 무관한 API·큰 응답·크기 불명·비JSON·잘못된 JSON·GraphQL POST를 재현. 네트워크 일반 단위 4건과 실제 Chromium fixture 1건 추가.

## 실제 검증
- Windows 2022 / Python 3.11: **34/34 PASS**, GitHub Actions run **39115403591**, success, 6.78초 (기존 Step 1 26 포함).
- Ubuntu 24.04 / Python 3.11 / 설치된 실제 Chromium: **3/3 PASS**, run **39115403678**, success, 6.60초.
- 사용자 PC, 실제 공개 사이트 동적 정확도는 미검증. 서버 SSRF 프록시 미구현. 임시 개발 컨테이너 Chromium 로컬 주소 정책 차단, GitHub Chromium fixture 검증으로 대체. Production/Vercel 미적용.

## 다음 ㄱ
**Step 2 단위 3: WebSocket/SSE 연결 메타데이터와 프레임 수 관찰**. 스트림 내용 저장·대기 금지, 제한 시간 내 종료·마스킹·기존 회귀 확인. 차트/번들 및 연관성 추정은 이후.
상세 인수인계 HANDOFF.md.
