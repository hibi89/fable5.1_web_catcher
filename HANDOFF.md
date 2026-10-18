# HANDOFF.md — Fable 5.1 Web Catcher / Step 2 단위 5

## ① 목표·확정 요구·기술
공개 URL 정적 기술 단서와 Chromium 실행 중 API/차트 단서를 수집하는 Python 3.11+ CLI. 요구 원본은 사용자 첨부 fable5.1_step1.txt 및 fable5.1_step2.txt. requests/BeautifulSoup + Playwright Chromium. Step 1 완료, Step 2 단위 1~5 완료(전체 미완료). 서버 내부 코드·DB·확정 데이터 lineage 추출 아님.

## ② 완료 기능·변경·결정 근거
Step 1 기본 정적 CLI 보존. Step 2: (1) 격리 Chromium, (2) XHR/fetch/값 없는 JSON 구조, (3) WebSocket/SSE 메타데이터, (4) 기술 전역 및 SVG/canvas 차트 DOM 후보, (5) **차트↔실제 관찰 API 보수적 연관 후보**.
신규 scanner/chart_mapping.py는 명시적인 차트 라이브러리 DOM 마커, 2xx JSON 수치형 시계열 형태, API 응답 후 1200ms 내 DOM 속성 갱신을 모두 요구. 단순 시간 근접·일반 SVG/canvas는 배제. 적합한 API가 2개 이상이면 연결 보류. api.candidates와 charts[].data_sources에는 endpoint ID만 연결하고, 근거·한계 및 0.55~0.65 비확률적 휴리스틱 점수 표시. 반복 일관성 검증 없음.
대안 A 시간만 비교는 저비용이나 오탐 위험 큼. 대안 B(구조+DOM 마커+순서+경쟁시 보류)는 같은 관찰 데이터만 재사용하고 오탐을 억제하여 채택. 새 네트워크 호출/사이트 변경 없음.

## ③ 테스트 명령·성공/실패·미검증
Windows Python 3.11 `python -m pytest -q`: **49/49 PASS** (run 39118292918). Ubuntu 실제 Chromium `python -m pytest -q tests/browser_runtime_check.py tests/browser_mapping_check.py`: **7/7 PASS** (run 39118292894). 두 실행 모두 기능 SHA **60469e4b8c58a6f188656639a433c22a65675466**. 실브라우저 내 유일 시계열 API와 동시 로그 요청, 동등한 API 2건 경합 시 연결 보류, 결과 마스킹 및 보고서 섹션 검증.
미검증: 실제 공개 사이트 정확도, 상용 차트 라이브러리 전체 통합, 브라우저/네트워크 반복 일관성, 사용자 Windows headed GUI. 테스트는 실제 Chromium이지만 로컬 모의 서버 기반.

## ④ 완료·진행·대기·중단점
Step 1 원본 7/7 완료, Step 2 단위 1~5의 해당 fixture 검증 완료. 단위 6 동일 origin JS 번들 문자열에서 미검증 API 후보 수집은 미착수. 이후 Step 2 보안·오류·전체 통합 검증과 최종 승인 미완료. 사용자 다음 ㄱ 전 추가 단위 진행 금지.

## ⑤ 오류·시도·재시도 금지·대안
이번 단위의 통합 대량 GitHub 변경 요청이 도구 안전 검사에서 차단됨. 정상 브랜치 보존 후 변경 파일을 작게 나눠 반영·CI 검증 성공. 같은 대량 요청 반복 금지.
이전 로컬 개발 컨테이너 Chromium은 net::ERR_BLOCKED_BY_ADMINISTRATOR로 localhost 접근 실패, 우회하지 않음. GitHub Actions 실제 Chromium으로 검증 대체.
동시 응답은 데이터 사용 입증이 아니므로 confidence를 확률 또는 실제 연결로 표시하지 말 것. SSRF 방어·압축 응답 메모리 완전 상한 미구현.

## ⑥ 저장소·브랜치·SHA·경로
비공개 hibi89/fable5.1_web_catcher / main. 검증 소스 SHA **60469e4b8c58a6f188656639a433c22a65675466**. 이전 안정 단위 4 문서 HEAD **2b0b5a3a76fa2749979672916a6726997af753bb**. 주요 scanner/chart_mapping.py, scanner/runtime_scan.py, scanner/runtime_detect.py, scanner/network.py, scanner/report.py, tests/test_chart_mapping.py, tests/browser_mapping_check.py, tests/browser_runtime_check.py.

## ⑦ Production URL·Vercel·실행 환경
배포 대상 아님(로컬 CLI), Vercel/Production SHA·URL 미적용. 설치 `python -m pip install -r requirements.txt` 및 `python -m playwright install chromium`. 정적 `python scan.py https://example.com --out ./out/static`. 동적 `python scan.py https://example.com --runtime --wait 10 --out ./out/runtime`. 테스트는 ③ 두 명령.

## ⑧ 원본·백업·인증 관리·수정 금지
원본 사용자 요구 첨부 fable5.1_step1.txt, fable5.1_step2.txt. GitHub main 단일 기준, 이전 커밋으로 복구 가능(강제 push 금지). 원본 응답/HTML/HAR/쿠키·인증 헤더/storage state·비밀값 GitHub 및 출력 저장 금지. tests/test_static.py.bak 보존. 무단 로그인·경로 probing·인증 우회 금지.

## ⑨ 다음 ㄱ 단위·승인 사항·완료 기준
Step 2 단위 6: 브라우저에서 **이미 로드된 동일 origin JS 번들**의 제한 문자열 증거를 토대로 미검증 API 후보를 수집. 크기·개수·시간 상한, 원본 번들 및 민감정보 비저장, 기존 실제로 관찰한 API와 후보를 분리. 추가 임의 경로 탐색 금지. fixture·Windows·Chromium 회귀 및 보안 검증 통과가 완료 기준. 이후 전체 Step 2 검수는 별도 단위.

## ⑩ 갱신·검증 시각(KST)·기준 커밋
2026-10-18 **19:12 KST** 검증 기록 기준. Windows run 39118292918 49 PASS, Chromium run 39118292894 7 PASS. 기능 SHA 60469e4b8c58a6f188656639a433c22a65675466. 문서 HEAD SHA는 저장 후 재조회로 검증. 사용자 PC·실사이트·Step 2 전체 미검증/미완료.
