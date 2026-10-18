# STATUS.md — Fable 5.1 Web Catcher / Step 2 단위 6

## 현재 상태 (2026-10-18 KST)
- Step 1: 사용자 원본 완료 기준 7/7 PASS, 기존 정적 CLI와 원본 26개 테스트 보존.
- Step 2: **단위 1~6 구현 및 해당 fixture 검증 완료, 전체 Step 2 미완료**. 브라우저 실행, XHR/fetch·제한 JSON 구조, WebSocket/SSE, 런타임 차트 DOM, 차트↔API 연관 후보, 로드된 JS 문자열 기반 **미검증 API 후보** 구현.
- 비공개 저장소 `hibi89/fable5.1_web_catcher` / `main`; CI Chromium 최신 SHA `4f8dccc1421adb158be892fe6f4de1f6e51bb458`. 배포/Vercel 미적용.

## 단위 6 구현 범위
- `scanner/bundle_scan.py`: 브라우저의 response/requestfinished 이벤트로 **이미 로드된 JS**만 수집. 최종 페이지와 동일 scheme·hostname·port 확인. 추가 fetch나 임의 경로 probing 없음.
- 응답 status 200, JS MIME, 완료된 요청, 유효한 Content-Length 1~131072 bytes만 본문을 일시적으로 열어 검사. 최대 12개 JS 응답, 미검증 후보 최대 30개, 스크립트당 15개. 원본 JS·토큰·응답값 결과 저장 안 함. 압축된 body의 순간 메모리 상한은 완전 보장 불가.
- 제한된 짧은 문자열 리터럴에서 API/GraphQL 경로만 추출. query 제거, 민감 키/경로 배제, 실제 XHR/fetch로 관찰된 endpoint와 중복 제거. `api.bundle_candidates`는 runtime에만 생성되며 `status=unverified_string_literal`, `observed_request=false`. 기존 `api.endpoints`는 관찰 사실이며 혼동 금지.
- `scanner/runtime_scan.py`, `scanner/report.py`에 관찰/결과 분리. 단위 테스트 5건 및 실제 Chromium fixture 2건 추가. 기존 정적/동적 기능 유지.

## 검증
- Windows Server 2022 Python 3.11: 전체 **54/54 PASS**, run `39119023745`, 소스 SHA `f74592918a098315e4f1b2d1e51ad6c771deafb0`.
- Ubuntu 24.04 실제 Chromium: 기존/신규 browser fixture 합계 **9/9 PASS**, run `39119033591`, 최종 HEAD `4f8dccc1421adb158be892fe6f4de1f6e51bb458`. 두 SHA 사이의 변경은 Chromium CI workflow에 신규 fixture 실행을 추가한 것뿐.
- 추가 네트워크 요청이 없는지 fixture 서버 hit, 대용량/미완료/크기 불명/교차 출처 제외, 비밀값 비저장, 실제 호출·문자열 추정 분리를 테스트.
- 실제 외부 사이트·사용자 Windows headed·실제 라이브러리·모든 탐지 정확도·SSRF 서버 보호는 **미검증 또는 미구현**. 결과는 테스트 fixture 통과이며 Step 2 전체 승인 아님.

## 다음 ㄱ
**최종 단위: Step 2 전체 통합/보안/실사이트 검증 및 완료 기준 점검.** 현 코드·문서 보존 후 CLI 정상/실패·복구·제한·오탐·마스킹 및 가능한 공개 실사이트의 익명 분석을 확인하고, 불충분한 기준은 미검증/미완료로 남길 것. 새로운 기능이나 배포는 승인 없이 추가하지 않음.

상세 10항 인수인계: `HANDOFF.md`.
