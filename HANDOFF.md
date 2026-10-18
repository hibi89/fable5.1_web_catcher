# HANDOFF.md — Fable 5.1 Web Catcher Step 1

## 1. 목표·용도·확정 요구·기술

공개 URL의 정적 HTML/응답 메타데이터에 기반한 기술 근거 수집 CLI. Python 3.11+, requests/beautifulsoup4/pytest/argparse. 상세 요구 `REQUIREMENTS.md`, 원문 사용자 첨부 `fable5.1_step1.txt`.

## 2. 완료 기능·변경·결정 근거

`scan.py` CLI, `scanner/static_scan.py` bounded GET, `scanner/sanitize.py` redaction, `scanner/fingerprints.py` 휴리스틱 자체 규칙 엔진, `scanner/report.py` JSON/한국어 MD, `rules/fingerprints.json` 16개 기술 규칙, 오프라인 fixture 및 pytest. 서버 내부 구현이나 데이터베이스 추출로 과장 금지. 다중 자산 후보는 URL만 수집하고 추가 요청하지 않음.

## 3. 테스트 명령·성공/실패 수·검증/미검증

- 컨테이너 Python 3.13.5 `python -m pytest -q` → **22/22 PASS** (2026-10-18 KST, 오프라인 fixture).
- 사용자 제공 Windows Python 3.11 `(.venv)` 기록: 첫 실행 **19 PASS / 3 FAIL** (UTF-8 파일을 기본 cp949로 읽는 테스트 오류) → `tests/test_static.py` `read_text(encoding="utf-8")` 수정 후 **22 PASS / 0 FAIL / 5.17초**.
- Windows `python scan.py https://example.com --out ./out/demo` 정상 종료 및 결과 파일 생성 경로 출력 확인.
- **GitHub Actions Windows 2022 / Python 3.11**: `.github/workflows/windows-python311.yml`에서 새 `.venv-ci` 생성, `requirements.txt` 설치, fixture pytest **23/23 PASS / 5.19초** (run 39111101377, 2026-10-18 17:21 KST, 결론 success).
- 최초 CI run 39110748770은 21 PASS / 1 FAIL: 리디렉션 stdout cp1252에서 한글 `print`가 `UnicodeEncodeError` 발생. `scan.py`의 표준 출력·오류에 `errors="backslashreplace"` 적용 및 강제 cp1252 하위 프로세스 회귀 테스트 추가 후 재실행 성공.
- 컨테이너의 새 격리 `.venv`: DNS/wheel 미제공으로 pip 설치 **실패**. 사용자 Windows 환경에서는 활성 가상환경의 CLI 및 pytest 실행 확인. 단 새 가상환경의 `pip install -r requirements.txt` 전체 과정을 기록으로 직접 확인한 것은 아님.
- **GitHub Actions Linux Ubuntu 24.04 / Python 3.11**: 별도 `linux-python311.yml`로 새 `.venv-ci` 생성 → `requirements.txt` 설치 → pytest **23/23 PASS / 5.03초** (run `39111476135`, 2026-10-18 17:27 KST, 결론 success).
- **공개 실사이트 검증 (1곳):** 2026-10-18 17:34 KST GitHub Actions run `39111940046` 결론 success. `https://www.python.org/` 단일 GET, HTTP 200, JSON 스키마 1.0 및 Markdown 생성, evidence ID 참조 PASS, 근거 1개, 경고 0. 프론트/백엔드 unknown, nginx 인프라 추정(헤더 기반). 출력 파일 2,444 / 1,742 bytes. 보고서 artifact `python-org-static-scan` (ID `12130523685`, 7일 유지), 링크 https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39111940046. 
- 미검증: macOS, 추가 공개 URL, 실제 기술 진위(단서 기반 추정만), 네트워크별 보안 프록시. **Windows·Linux GitHub Actions에서 새 가상환경 생성·설치 검증 완료**, 사용자 PC의 가상환경 최초 설치 과정은 별도 미기록.

## 4. 완료/진행/대기/차단·중단 지점

Step 1 CLI·오프라인 fixture 구현 및 Windows Python 3.11 테스트 22/22 통과. **GitHub `main`에 소스 최초 반영 확인**. 독립 새 Windows·Linux 가상환경 설치부터 fixture 테스트까지 각 23/23 PASS 검증 완료. 실제 공개 URL 1곳에 대한 구조·근거 참조 검증 완료; macOS 및 추가 공개 사이트는 선택 미완료. Step 2는 미착수.

## 5. 오류 근거·원인·시도·재시도 금지·대안

컨테이너에서 `pip install --no-index -r requirements.txt`는 wheel 없음, `venv --system-site-packages`에서도 bs4/pytest 미노출, 외부 DNS 불가. 동일 방식 재시도 금지. Windows 테스트 최초 3건 실패는 `pathlib.read_text()` 기본 cp949와 저장된 UTF-8 JSON/Markdown 사이의 불일치였으며, 명시적 UTF-8 읽기 설정으로 수정 확인. 사용자 Windows 활성 `.venv`에서 22/22 PASS. CI 최초 Windows cp1252 출력 실패는 CLI 표준출력의 표현 불가능한 한글이 원인으로 확인, `backslashreplace` 적용·회귀테스트 추가로 해결. GitHub Actions의 새 Windows venv 설치·테스트는 23/23 성공. 컨테이너 DNS/wheel 제약과 혼동하지 말 것.

## 6. 저장소·브랜치·SHA·주요 경로

`hibi89/fable5.1_web_catcher`, `main`. 최초 GitHub 소스 커밋: `cbef84bd388f8b619d2d388bf6cf5a87c617ca45` (2026-10-18 17:03:47 KST); CI 최초 커밋: `6ffb0dc0520d14e7911e0cbe3ebbef5cef568ad8`; 수정·회귀 테스트 소스 커밋: `78fe2ce4739825b8e9a69d471cfaacc03fc7c063`; Linux 검증 workflow 커밋: `d3cd802ce88b6784e5a028dee9915939f66f0506`; 실사이트 smoke workflow 커밋: `706f83c9c48ff299f0e85b3e3c2acba87f186f05` (작성자·커미터 GitHub 계정 `hibi89` 연결 확인). 경로: `scan.py`, `scanner/`, `rules/`, `tests/`, `README.md`, `STATUS.md`, `HANDOFF.md`. 최초 커밋에서 `tests/test_static.py.bak`도 확인(임의 삭제 금지).

## 7. Production URL·Vercel·실행 명령·환경

배포 대상 아님. 실행 `python scan.py https://example.com --out ./out/demo`, 테스트 `python -m pytest -q`. Python 3.11+; 오프라인 fixture는 API 키가 필요 없음. GitHub Actions: `windows-2022`, `actions/checkout@v7`, `actions/setup-python@v7`, clean venv, `requirements.txt` 설치, pytest. 코드·테스트·workflow 관련 push 및 `main` 대상 PR, 수동 dispatch가 실행 트리거. `permissions: contents: read`, job 제한 15분. 성공 run: https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39111101377. Linux: `.github/workflows/linux-python311.yml`, `ubuntu-24.04`, Python 3.11, 10분 제한, `contents: read`; 파일 자체 push 트리거 및 수동 `workflow_dispatch`만 사용(일반 코드 변경 자동 반복 없음). 성공 run: https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39111476135

실사이트 한정 smoke: `.github/workflows/public-website-smoke.yml`는 오직 `https://www.python.org/` 루트 공개 페이지에 GET 요청을 보내고 JSON/Markdown을 검사합니다. 한 번의 workflow 추가 push 또는 수동 workflow_dispatch 시 동작하며 일반 소스 코드 변경 시 자동 실사이트 수집 없음. GitHub Actions artifact에 결과를 7일 보존합니다. 결과는 공개 응답 근거로서 기술을 확정하지 않습니다.

## 8. 원본·백업·인증 관리·수정 금지

확정 원본: 대화 첨부 `fable5.1_step1.txt`. 원본 ZIP과 Windows 수정 전 테스트 백업은 사용자가 보관. 이제 GitHub `main`이 소스 단일 기준. 토큰/인증/쿠키 값과 `.env`를 GitHub에 등록하거나 출력하지 말 것. 첫 커밋에 `tests/test_static.py.bak`가 함께 포함됐음(비밀정보 유무 별도 감사 미수행).

## 9. 다음 작업 우선순위·절차·완료 기준·승인 사항

1. **완료:** GitHub `main` 최초 소스 커밋 및 Windows 가상환경 22/22 PASS 검증; 문서·BOOK 동기화.
2. **완료:** Windows·Linux CI 각 23/23 PASS. 실제 공개 Python 공식 사이트 URL 1곳의 JSON·Markdown 스키마/참조 검증 PASS (`39111940046`). **다음 선택 미완료:** macOS 또는 두 번째 실제 공개 URL 스키마 검증(기술 종류 감지를 필수로 요구하지 않음).
3. **선택 정리:** 백업 `tests/test_static.py.bak` 추적 제외 필요성 확인 후 사용자 승인 시 정리.
4. **승인 대기:** Step 2 Playwright/동적 분석 확장(범위·유지비용·방법 비교 뒤 진행).

## 10. 갱신 일시·확인 시점·검증 범위·문서 기준 커밋

2026-10-18 17:34 KST. 검증 범위: GitHub Windows 23 PASS, Linux 23 PASS, Python 공식 사이트 실제 HTTP 200/스키마/evidence 참조 CI PASS, 이전 Windows PowerShell 22 PASS. 문서 기준 핵심 코드 `78fe2ce4739825b8e9a69d471cfaacc03fc7c063`; 실사이트 테스트 workflow `706f83c9c48ff299f0e85b3e3c2acba87f186f05`. 배포 없음.
