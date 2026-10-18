# HANDOFF.md — Fable 5.1 Web Catcher / Step 2 단위 1

## 1. 목표·용도·확정 요구·기술
공개 URL의 기술 단서 수집 CLI. Step 1은 Python requests/BeautifulSoup 정적 스캔, Step 2는 사용자 첨부 fable5.1_step2.txt를 기준으로 Python Playwright/Chromium을 이용한 근거 기반 동적 관찰이다. 로그인, 클릭, 폼 제출, 인증·WAF 우회, 비밀값·원본 응답 저장은 금지한다. Step 2 전체가 아닌 단위 1만 완료.

## 2. 완료 기능·변경·결정 근거
- 기본 정적 scan.py 실행은 그대로 유지하고 --runtime, --headed, --wait 옵션만 추가. wait 기본 10초, DOMContentLoaded 기준.
- scanner/runtime_scan.py: 새 격리 브라우저 컨텍스트, 이동 전 초기 스크립트와 이벤트 리스너, XHR/fetch 요청·응답 개수 관찰(내용·URL 미저장), 제한적 스크롤, 최종 URL·HTTP 상태·현재 script/stylesheets URL의 마스킹된 목록, 타임아웃 부분 보존 및 브라우저 정리.
- scan_mode=runtime, runtime.scope=navigation_only 및 부분 구현 경고. API 실제 목록, JSON 구조, 차트 후보, API 연관·번들 후보는 아직 구현하지 않음.
- requirements.txt에 Playwright 의존성, README에 설치/한계, tests/test_runtime_bootstrap.py 일반 단위 테스트 4건, tests/browser_runtime_check.py 별도 실제 Chromium 테스트 2건, Ubuntu 전용 workflow 추가.
- 선택 근거: 별도 프로그램이 아닌 기존 models/report/sanitize 기반 최소 확장. Playwright 표준 이벤트는 CDP 직접 연동보다 구현·유지보수 비용이 낮음.

## 3. 테스트 명령·성공/실패 수·검증/미검증
- python -m pytest -q: Windows Server 2022 Python 3.11 GitHub Actions run 39114514927, **30/30 PASS**, conclusion success. Step 1 원래 26건 포함.
- python -m pytest -q tests/browser_runtime_check.py: Ubuntu 24.04 Python 3.11 실제 설치한 Playwright Chromium에서 GitHub Actions run 39114514969, **2/2 PASS**, conclusion success. 두 번째 검사는 실제 CLI subprocess의 --runtime --wait 경로.
- 외부 CDN 없는 로컬 HTTP fixture 사용. Chromium 전용 CI에서 python -m playwright install --with-deps chromium 실행 성공.
- 임시 컨테이너의 브라우저 없는 헬퍼 테스트 2/2 PASS. 사용자 PC Windows에서 실제 브라우저 실행, 공개 실사이트 런타임 정확도와 Step 2 전체 완료 기준은 미검증.
- 기존 Step 1 별도 최종 근거: 원본 7/7 PASS, Windows/Linux/macOS 각 26/26 PASS, Python.org/example.com 구조 검사 PASS. docs/STEP1_FINAL_ACCEPTANCE.md 참고.

## 4. 완료/진행/대기/차단·중단 지점
Step 1 완료 유지. Step 2 단위 1 브라우저 실행·CLI·마스킹·부분 결과 보존·해당 테스트 완료. Step 2 전체는 진행 중이고 API 구조/GraphQL/WebSocket/SSE·차트 라이브러리·차트 연결 추정·JS 번들 분석 및 최종 안전성은 미완료. 다음 ㄱ을 받아야 단위 2 착수.

## 5. 오류 근거·원인·시도·재시도 금지·대안
임시 컨테이너의 Playwright 전용 Chromium 바이너리가 없고 시스템 /usr/bin/chromium에서 localhost 이동 시 net::ERR_BLOCKED_BY_ADMINISTRATOR 발생. 관리자 정책이므로 동일 환경 재시도/우회 금지, 독립 GitHub Ubuntu Chromium 실사용 fixture 2/2 PASS로 대체. 기존 Windows cp949/cp1252 테스트 오류는 Step 1에서 이미 수정·검증됨. 서버용 SSRF 차단 프록시가 없어 불특정 사용자의 URL을 서버에 노출시키지 말 것.

## 6. 저장소·브랜치·SHA·주요 경로
비공개 hibi89/fable5.1_web_catcher, main. Step 2 구현 9db9befa4866c73dd80777d8c71191d783737c96, CLI 브라우저 검증 e89bdec994f4bdcbd9132773ed12073c48e9fe4e. Step 1 최종 소스 9d47bdb06b1b42eca9babfe24f3558d49cf84c37, Step 1 완료 문서 b20f3251b21ccdc4d452c082d324ae3e0be566bf. 주요 파일 scan.py, scanner/runtime_scan.py, scanner/report.py, scanner/static_scan.py, scanner/models.py, tests/test_runtime_bootstrap.py, tests/browser_runtime_check.py, README.md.

## 7. Production URL·Vercel 프로젝트·실행 명령·환경
배포 대상이 아니므로 Production/Vercel 미적용. Python 3.11 이상, pip install -r requirements.txt, python -m playwright install chromium. 기본 정적 분석: python scan.py https://example.com --out ./out/static. 브라우저: python scan.py https://example.com --runtime --out ./out/runtime. 화면 표시: python scan.py https://example.com --runtime --headed --wait 10 --out ./out/runtime. 브라우저는 로그인 컨텍스트를 재사용하지 않고 networkidle 대기를 사용하지 않음. GitHub Actions 권한 contents: read.

## 8. 원본 위치·백업·인증 관리·수정 금지
사용자 확정 원본 fable5.1_step1.txt 및 fable5.1_step2.txt(대화 첨부). 소스 단일 기준 GitHub main; 변경 전 커밋으로 복원 가능, force push 금지. HAR·원본 응답·storage state·cookie/auth 헤더·토큰을 GitHub·결과 파일에 저장하지 않음. tests/test_static.py.bak 원본 보존, 사용자 허가 없이 삭제하지 않음.

## 9. 다음 작업 우선순위·절차·완료 기준·승인 사항
다음 ㄱ의 작업 단위는 scanner/network.py를 통한 **실제로 관찰한 XHR/fetch 요청·응답의 마스킹된 endpoint 메타데이터와 제한된 JSON 값 없는 구조 요약**. 요청별 ID/시간/method/status/content-type, 크기 제한, 응답 읽기 실패 시 endpoint 보존, 테스트용 비밀값 비노출·오프라인 fixture 검증. 요청 body·인증 헤더·쿠키·응답 실데이터 저장 금지. 관찰되지 않은 경로를 probing하지 않음. WebSocket/SSE, 차트, API 연관·번들 문자열 분석은 후속 단위로 분리. 다음 ㄱ 전 선행 구현 금지.

## 10. 갱신 일시(KST)·확인 시점·검증 범위·문서 기준 커밋
2026-10-18 18:14 KST 테스트 확인. 최종 테스트 대상 소스 SHA e89bdec994f4bdcbd9132773ed12073c48e9fe4e, Windows run 39114514927 30 PASS, Chromium run 39114514969 2 PASS. 문서를 담은 GitHub 커밋 SHA는 커밋 후 재조회해 확인하며 문서 내부에는 자기 커밋 SHA를 사전 기입하지 않음. User PC와 실제 외부 사이트 동적 분석 미검증.
