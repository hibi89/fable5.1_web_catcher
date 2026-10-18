# HANDOFF.md — Fable 5.1 Web Catcher / Step 2 단위 6

## ① 목표·확정 요구·기술
공개 URL 정적 기술 단서 및 Chromium에서 실행된 API/차트/JS 문자열 단서를 기록하는 Python 3.11+ CLI. 원본 사용자 요구 `fable5.1_step1.txt`, `fable5.1_step2.txt`. Step 1 완료; Step 2 **단위 1~6 구현·해당 fixture 검증 완료, 전체 최종 승인 미완료**. 사이트 내부 코드/DB·실제 데이터 연결 추출이라고 주장하지 않음.

## ② 완료 기능·변경·결정 근거
이전 단위 1 Chromium, 2 XHR/fetch·JSON 값 없는 구조, 3 WS/SSE, 4 차트 DOM·라이브러리, 5 차트↔API 보수적 연관 후보 유지.
단위 6 `scanner/bundle_scan.py`는 페이지 이동 전 script response/requestfinished 리스너를 연결하고 **브라우저가 이미 받은 JS만** 검사한다. 동일 scheme/host/port, 200 응답, JS MIME, 명시된 길이, 완료된 요청만 분석. 최대 12개 JS 응답·개별 Content-Length 128 KiB·짧은 따옴표 문자열/경로·스크립트당 15 후보·전체 30 후보. 원본 JS·인증정보·헤더/쿠키·본문값/시크릿 저장하지 않음. 짧은 확정 형식 API/GraphQL path에서 query 제거·민감 경로 제외; 관찰된 API와 중복은 제외. runtime 전용 `api.bundle_candidates`는 **unverified_string_literal/observed_request=false/confidence=0.2** 별도 영역. `api.endpoints`의 실제 관찰 기록과 절대 혼동 금지. `runtime.bundle_scan`에 상한·건수 기록.
설계 비교: A) JS 주소 재요청 또는 새 API 경로 요청은 추가 트래픽과 오용 위험이 큼. B) Playwright가 이미 받은 응답에 수동 리스너로 제한 분석은 별도 fetch가 없고 기존 이벤트 재사용/유지보수 우위. B 선택. `scanner/runtime_scan.py` 연동, `scanner/report.py` 후보 전용 절과 한계 기록, `tests/test_bundle_scan.py` 단위 5건, `tests/browser_bundle_check.py` 실제 Chromium 2건, CI workflow 갱신.

## ③ 테스트 명령·성공/실패 수·미검증
일반: `python -m pytest -q` → Windows 2022 / Python 3.11 **54/54 PASS**, 0 FAIL, Actions run **39119023745**, 소스 SHA `f74592918a098315e4f1b2d1e51ad6c771deafb0`.
실제 Chromium: `python -m pytest -q tests/browser_runtime_check.py tests/browser_mapping_check.py tests/browser_bundle_check.py` → Ubuntu 24.04 / Python 3.11 Chromium **9/9 PASS**, 0 FAIL, run **39119033591**, 최신 기능/CI SHA `4f8dccc1421adb158be892fe6f4de1f6e51bb458`. 두 SHA 사이는 Chromium CI workflow의 신규 브라우저 테스트 포함만 변화.
로컬 fixture는 실제 로드 스크립트·미검증 /api 문자열·실제 호출된 API·중복·과대 JS·빈 후보·토큰 보호·추가 미검증 경로 요청 없음 검증. 이전 Step 1 정적 테스트 포함.
미검증: 일반 실사이트 정확도, 실제 상용 차트 라이브러리 전체 통합, 사용자 Windows headed, 교차 환경, 서버용 SSRF 보호. fixture 통과를 Step 2 전체 승인으로 오인 금지.

## ④ 완료/진행/대기·중단 지점
Step 1 원본 7/7 완료. Step 2 단위 1~6 해당 fixture 테스트 성공. **다음 ㄱ은 새 기능 개발이 아닌 Step 2 최종 통합/보안/실사이트 검수**. 사전 승인 없는 배포·보안 범위 변경 금지.

## ⑤ 오류·실패 근거·재시도 금지·대안
코드 작성 첫 호출에서 임베디드 테스트 문자열의 템플릿 표기 때문에 JS orchestration ReferenceError가 발생, GitHub 쓰기 전에 실패. 단일 모듈/테스트 파일 분리 호출로 전환, 이후 구현·CI 정상.
중간 Chromium CI는 새 runtime-only 필드로 인한 기존 스키마 기대값 불일치를 포함해 실패했고, `tests/browser_runtime_check.py`의 기대값을 명시적으로 갱신한 뒤 최종 9/9 PASS. 이전 로컬 Chromium net::ERR_BLOCKED_BY_ADMINISTRATOR 정책은 우회 금지, GitHub Actions로 테스트.
크기 제한은 선언된 Content-Length 및 읽은 body를 확인하나 Playwright 내부 압축/메모리 절대 상한을 보장하지 못함. 코드/스니펫 원문 저장 금지. SSRF 차단이 없으므로 외부 사용자 URL을 받는 서버에 공개하지 말 것.

## ⑥ 저장소·브랜치·SHA·주요 경로
비공개 `hibi89/fable5.1_web_catcher` / `main`. 단위 6 Chromium 검증 HEAD `4f8dccc1421adb158be892fe6f4de1f6e51bb458`; Windows 검증 SHA `f74592918a098315e4f1b2d1e51ad6c771deafb0`. 이전 안정 단위 5 문서 HEAD `fededbdef17dab3f2f0e2dbf786ba2dbaa2b70b3`로 복원 가능. 핵심 `scanner/bundle_scan.py`, `scanner/runtime_scan.py`, `scanner/report.py`, `scanner/network.py`, `tests/test_bundle_scan.py`, `tests/browser_bundle_check.py`, `.github/workflows/runtime-python311.yml`.

## ⑦ Production URL·Vercel·실행 명령·환경
배포 대상 아님(로컬 CLI), Vercel/Production URL/SHA **미적용**. Python 3.11+, `python -m pip install -r requirements.txt`, `python -m playwright install chromium`. 기본 정적 `python scan.py https://example.com --out ./out/static`. 런타임 `python scan.py https://example.com --runtime --wait 10 --out ./out/runtime`. headed GUI 선택: `--headed`. 테스트 명령 ③ 참조.

## ⑧ 원본·백업·인증 관리·수정 금지
사용자 원본 `fable5.1_step1.txt`, `fable5.1_step2.txt`(대화 첨부); GitHub main 소스 단일 기준. 원본 HTML/JS/응답/HAR/storage state/인증 헤더·쿠키·토큰 저장 및 강제 push 금지. `tests/test_static.py.bak` 보존. 추가 API 경로 probing, 자동 로그인·폼 제출·WAF 우회 금지.

## ⑨ 다음 우선순위·완료 기준·승인
다음 ㄱ: Step 2 전체 최종 수용성 검증 — 로컬 CLI 성공·부분 오류 출력, 정적/동적 회귀, 브라우저 오탐·상한·결측·마스킹·보고서 일관성, 접근 가능한 공개 실사이트의 무인증 실행과 결과 구조 검사. 실제 기술/연관 탐지 정확도는 fixture와 분리 판정. 확인된 실패만 최소 수정·재검증; 미검증 항목 남으면 완료 선언 금지. 배포는 별도 사용자 승인 필요.

## ⑩ 갱신 일시 KST·확인 시점·문서 기준
2026-10-18 **19:23 KST** 기준 CI 로그 검증: Windows 54/54 run 39119023745, 실제 Chromium 9/9 run 39119033591. 문서 자체 HEAD는 저장 후 재조회로 검증. 실사이트/사용자 PC/Step 2 전체 미검증.
