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
- 미검증: macOS/Linux, 공개 URL 다수의 실제 결과, 네트워크별 보안 프록시. **Windows GitHub Actions의 새 가상환경 생성·설치는 검증 완료**; 사용자 개인 PC의 venv 최초 설치 과정은 별도로 확인하지 않음.

## 4. 완료/진행/대기/차단·중단 지점

Step 1 CLI·오프라인 fixture 구현 및 Windows Python 3.11 테스트 22/22 통과. **GitHub `main`에 소스 최초 반영 확인**. 독립 새 Windows 가상환경 설치부터 fixture 테스트까지 CI 검증 완료(23/23). 다른 운영체제 및 다수 실제 사이트는 검증 대기. Step 2는 미착수.

## 5. 오류 근거·원인·시도·재시도 금지·대안

컨테이너에서 `pip install --no-index -r requirements.txt`는 wheel 없음, `venv --system-site-packages`에서도 bs4/pytest 미노출, 외부 DNS 불가. 동일 방식 재시도 금지. Windows 테스트 최초 3건 실패는 `pathlib.read_text()` 기본 cp949와 저장된 UTF-8 JSON/Markdown 사이의 불일치였으며, 명시적 UTF-8 읽기 설정으로 수정 확인. 사용자 Windows 활성 `.venv`에서 22/22 PASS. CI 최초 Windows cp1252 출력 실패는 CLI 표준출력의 표현 불가능한 한글이 원인으로 확인, `backslashreplace` 적용·회귀테스트 추가로 해결. GitHub Actions의 새 Windows venv 설치·테스트는 23/23 성공. 컨테이너 DNS/wheel 제약과 혼동하지 말 것.

## 6. 저장소·브랜치·SHA·주요 경로

`hibi89/fable5.1_web_catcher`, `main`. 최초 GitHub 소스 커밋: `cbef84bd388f8b619d2d388bf6cf5a87c617ca45` (2026-10-18 17:03:47 KST); CI 최초 커밋: `6ffb0dc0520d14e7911e0cbe3ebbef5cef568ad8`; 수정·회귀 테스트 소스 커밋: `78fe2ce4739825b8e9a69d471cfaacc03fc7c063` (커밋 작성자·커미터 GitHub 계정 `hibi89` 연결 확인). 경로: `scan.py`, `scanner/`, `rules/`, `tests/`, `README.md`, `STATUS.md`, `HANDOFF.md`. 최초 커밋에서 `tests/test_static.py.bak`도 확인(임의 삭제 금지).

## 7. Production URL·Vercel·실행 명령·환경

배포 대상 아님. 실행 `python scan.py https://example.com --out ./out/demo`, 테스트 `python -m pytest -q`. Python 3.11+; 오프라인 fixture는 API 키가 필요 없음. GitHub Actions: `windows-2022`, `actions/checkout@v7`, `actions/setup-python@v7`, clean venv, `requirements.txt` 설치, pytest. 코드·테스트·workflow 관련 push 및 `main` 대상 PR, 수동 dispatch가 실행 트리거. `permissions: contents: read`, job 제한 15분. 성공 run: https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39111101377

## 8. 원본·백업·인증 관리·수정 금지

확정 원본: 대화 첨부 `fable5.1_step1.txt`. 원본 ZIP과 Windows 수정 전 테스트 백업은 사용자가 보관. 이제 GitHub `main`이 소스 단일 기준. 토큰/인증/쿠키 값과 `.env`를 GitHub에 등록하거나 출력하지 말 것. 첫 커밋에 `tests/test_static.py.bak`가 함께 포함됐음(비밀정보 유무 별도 감사 미수행).

## 9. 다음 작업 우선순위·절차·완료 기준·승인 사항

1. **완료:** GitHub `main` 최초 소스 커밋 및 Windows 가상환경 22/22 PASS 검증; 문서·BOOK 동기화.
2. **완료:** GitHub Actions Windows 3.11 새 venv 설치·pytest 23/23 PASS. 추가 검증은 선택: macOS/Linux 및 외부 URL 결과 스키마만 확인(기술 명칭 강제 금지).
3. **선택 정리:** 백업 `tests/test_static.py.bak` 추적 제외 필요성 확인 후 사용자 승인 시 정리.
4. **승인 대기:** Step 2 Playwright/동적 분석 확장(범위·유지비용·방법 비교 뒤 진행).

## 10. 갱신 일시·확인 시점·검증 범위·문서 기준 커밋

2026-10-18 17:21 KST. 검증 범위: GitHub `main` 최신 커밋/작성자·커미터, CI 2회 결과·Windows Actions step별 로그·23 PASS, 사용자 Windows PowerShell 22 PASS, 이전 컨테이너 fixture. 문서 기준 소스 커밋: `78fe2ce4739825b8e9a69d471cfaacc03fc7c063`. Vercel/Production 미적용.
