# STATUS.md — Fable 5.1 Web Catcher

## 현재 상태 (2026-10-18 KST)
- **Step 1 완료 100%**: 원본 7/7 PASS. Windows/Linux/macOS Python 3.11 각 26/26, Python.org 및 example.com HTTP·JSON·Markdown/evidence PASS. docs/STEP1_FINAL_ACCEPTANCE.md 참고.
- **Step 2 진행 중 — 단위 1 구현·검증 완료**: 전체 Step 2 완료 아님. 원본 사용자 첨부 fable5.1_step2.txt 수령.
- GitHub hibi89/fable5.1_web_catcher, main. 단위 1 구현 SHA 9db9befa4866c73dd80777d8c71191d783737c96, 추가 브라우저 CLI 검증 SHA e89bdec994f4bdcbd9132773ed12073c48e9fe4e.
- 배포 미적용(로컬 CLI).

## Step 2 단위 1 구현 범위
- scan.py: 정적 경로 유지, --runtime / --headed / --wait 추가. 기본 대기 10초.
- scanner/runtime_scan.py: 격리 Playwright Chromium 컨텍스트, 이동 전 이벤트 리스너·init script, DOMContentLoaded, 이벤트 펌프 대기, 2회 이내 제한 스크롤, HTTP 상태·최종 URL·script/stylesheets URL 관찰·마스킹, 오류시 부분 결과 저장 및 자원 정리.
- models의 기존 프론트/백엔드 추정/인프라/evidence/api/charts 키 유지. runtime.scope=navigation_only 표시. 실제 API endpoint·JSON 구조·GraphQL/WebSocket/SSE·런타임 차트/연관 후보·JS 번들 추출은 미구현.
- Playwright 의존성, 런타임 Markdown 분기, README 사용법·테스트 설명, 독립 Chromium GitHub Actions workflow 추가.

## 검증
- Windows Server 2022 Python 3.11: python -m pytest -q → **30 passed / success**, run 39114514927. Step 1 기존 26건 포함.
- Ubuntu 24.04 Python 3.11 + Playwright Chromium: python -m pytest -q tests/browser_runtime_check.py → **2 passed / success**, run 39114514969. 하나는 실제 CLI subprocess로 --runtime --wait 수행.
- 컨테이너 헬퍼 2/2 PASS, 하지만 시스템 Chromium 로컬 HTTP는 net::ERR_BLOCKED_BY_ADMINISTRATOR 환경 차단. 정책 우회 금지, GitHub CI로 실제 브라우저 검증 완료.
- 사용자 PC에서의 Step 2 실행, 공개 실사이트 동적 분석 정확도, 서버 SSRF 보호는 **미검증·미구현**. Record/LLM/UI/크롤러 범위 밖.

## 다음 ㄱ
**단위 2: 네트워크 XHR/fetch 요청·응답 메타데이터 및 JSON 값 없는 구조 추출**, 민감정보 마스킹·응답 크기 제한·부분 실패시 endpoint 보존과 오프라인 테스트. 차트 후보·WebSocket/SSE·번들·연관 점수는 이후 단위. 새 ㄱ 없이는 진행하지 않음.

자세한 10항 인수인계는 HANDOFF.md. 최종 테스트 소스 기준 e89bdec994f4bdcbd9132773ed12073c48e9fe4e.
