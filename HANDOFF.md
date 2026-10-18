# HANDOFF.md — Fable 5.1 Web Catcher Step 1

## 1. 목표·용도·확정 요구·기술

공개 URL의 정적 HTML/응답 메타데이터에 기반한 기술 근거 수집 CLI. Python 3.11+, requests/beautifulsoup4/pytest/argparse. 상세 요구 `REQUIREMENTS.md`, 원문 사용자 첨부 `fable5.1_step1.txt`.

## 2. 완료 기능·변경·결정 근거

`scan.py` CLI, `scanner/static_scan.py` bounded GET, `scanner/sanitize.py` redaction, `scanner/fingerprints.py` 휴리스틱 자체 규칙 엔진, `scanner/report.py` JSON/한국어 MD, `rules/fingerprints.json` 16개 기술 규칙, 오프라인 fixture 및 pytest. 서버 내부 구현이나 데이터베이스 추출로 과장 금지. 다중 자산 후보는 URL만 수집하고 추가 요청하지 않음.

## 3. 테스트 명령·성공/실패 수·검증/미검증

- `python -m pytest -q` (Python 3.13.5) → **22 passed** (2026-10-18 KST). 추후 변경 시 재실행.
- 새 격리 `.venv`: 네트워크와 wheel 미제공으로 pip 설치 **실패**, 런타임 코드 실패로 판단하지 말 것.
- 미검증: 실제 인터넷 사이트, Windows/macOS, Python 3.11, 네트워크별 보안 프록시, 새 가상환경 설치.

## 4. 완료/진행/대기/차단·중단 지점

로컬 Step 1 구현/fixture 테스트 완료. 독립 가상환경 설치 검증 대기. GitHub 대상 저장소는 이 시점에서 빈 상태로, 로컬 전체 소스 커밋 미반영.

## 5. 오류 근거·원인·시도·재시도 금지·대안

`python -m venv .venv` 다음 `pip install --no-index -r requirements.txt`: requests 패키지 wheel 없음. `venv --system-site-packages`에서도 bs4/pytest 미노출. 이 환경의 패키지 저장소가 없고 외부 DNS 접근이 불가함. 동일 오프라인 설치 무의미 반복 금지; 인터넷 사용 가능한 사용자 환경에서 표준 pip 설치 권고.

## 6. 저장소·브랜치·SHA·주요 경로

`hibi89/fable5.1_web_catcher`, `main`. GitHub 소스 커밋 SHA 없음(미반영). 경로: `scan.py`, `scanner/`, `rules/`, `tests/`, `README.md`.

## 7. Production URL·Vercel·실행 명령·환경

배포 대상 아님. 실행 `python scan.py https://example.com --out ./out/demo`, 테스트 `python -m pytest -q`. Python 3.11+; 오프라인 fixture는 별도 API 키가 필요 없음.

## 8. 원본·백업·인증 관리·수정 금지

확정 원본: 현재 대화에 첨부된 `fable5.1_step1.txt`. GitHub 빈 저장소였으므로 기존 코드 수정 없음. 출력에 쿠키값/Authorization/토큰 저장 금지, `.env` 포함하지 않음.

## 9. 다음 작업 우선순위·절차·완료 기준·승인 사항

1. GitHub API와 연결된 실행 환경에서 ZIP 소스 업로드, 커밋 검증 및 중앙 BOOK 기록 확인.
2. 인터넷 가능한 독립 새 가상환경에서 `pip install -r requirements.txt`, `python -m pytest -q`, fixture CLI 재검증.
3. 필요 시 Step 2 동적 브라우저 수집은 범위·비용·설계를 승인받은 뒤 별도 구현.

## 10. 갱신 일시·확인 시점·검증 범위·문서 기준 커밋

2026-10-18 KST. 검증 범위: 컨테이너의 로컬 테스트 및 파일. 문서 기준 커밋: 미반영.
