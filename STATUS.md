# STATUS.md — Fable 5.1 Web Catcher / Step 2 단위 3

## 현재 상태 (2026-10-18 KST)
- Step 1 **완료 7/7 (100%)**: 기존 정적 CLI·26개 테스트 보존, 종전 3 OS 각 26/26 PASS, Python.org/example.com 정적 HTTP/JSON/Markdown/evidence smoke PASS. 상세 docs/STEP1_FINAL_ACCEPTANCE.md.
- Step 2 **단위 1~3 구현·검증 완료, 전체 미완료**. 단위 1 격리 Chromium·CLI, 단위 2 XHR/fetch 실제 endpoint·값 없는 JSON 구조·GraphQL 후보, 단위 3 WS/SSE 연결 메타데이터·프레임 수. 차트 라이브러리/DOM 변화·차트↔API 관계·JS 번들 후보는 아직 미구현.
- GitHub 비공개 hibi89/fable5.1_web_catcher, main. 검증 코드 SHA f8a4f5dc50cdb4993b0161abb80193e46d00f534. Production/Vercel 미적용.

## 단위 3 변경
- scanner/connections.py 새 모듈: WebSocket 연결 URL/시각/프레임 카운트/닫힘/오류 boolean, SSE response가 실제 text/event-stream일 때 URL/status/MIME/시각만 저장.
- 마스킹 URL만 저장, 프레임 원문·socketerror 내용·SSE 스트림 body·인증 헤더·쿠키는 저장하거나 읽지 않음. 연결 60건 상한, 프레임 카운트 방향별 100만 상한. page.goto 전 listener 설치 및 메타데이터 보존.
- scanner/runtime_scan.py·report.py 확장, fixture_server.py에 stdlib websocket handshake/프레임 및 미종결 SSE fixture, tests/test_connections.py 단위 4개, browser_runtime_check.py 통합 1개 추가, README/Actions 갱신.

## 실제 테스트
- Windows 2022 Python 3.11 전체 **38/38 PASS**, run 39116413660, SHA f8a4f5dc50cdb4993b0161abb80193e46d00f534.
- Ubuntu 24.04 Python 3.11 / Playwright Chromium **4/4 PASS**, run 39116413676, 동일 SHA. 이전 초회 3 PASS/1 FAIL(run 39116326072)은 기능 오류가 아닌 오래된 runtime.scope assertion; 한 줄 정정 후 4/4 PASS.
- WebSocket 프레임 송수신 각 >=1, SSE 응답 헤더, 끝나지 않는 스트림에서도 유한 시간 내 종료, 출력에 테스트 비밀값 부재 확인.
- 실사이트 동적 정확도/사용자 PC/Windows headed는 미검증. SSRF proxy 없는 로컬 CLI를 무단 외부 서비스로 배포하지 않는다.

## 다음 ㄱ
**Step 2 단위 4: 알려진 런타임 기술 흔적과 MutationObserver 기반 차트 DOM 후보 탐지**. 차트 라이브러리 존재와 실제 차트 인스턴스 구분, canvas/SVG만으로 확정 금지, 타이밍은 같은 epoch ms. 차트↔API 연관 및 JS 번들은 이후 단위.
상세 10항 인수인계 HANDOFF.md.
