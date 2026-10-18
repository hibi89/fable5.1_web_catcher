# STATUS.md — Step 1 진행 상태

- 상태: **로컬 구현/오프라인 테스트 통과, 새 격리 가상환경 설치 검증 대기, GitHub 전체 소스 업로드 미반영**.
- 범위: 첨부 `fable5.1_step1.txt`의 정적 기술 근거 스캐너.
- 구현: CLI, 수집/마스킹/판별/보고서/자체 규칙 파일, fixture 서버, pytest.
- 테스트: 2026-10-18 KST, 기본 런타임 Python 3.13.5에서 `python -m pytest -q` **22/22 PASS**.
- 오프라인 설치: 격리 `.venv` 내 `pip install --no-index -r requirements.txt`는 설치 가능 wheel 부재로 실패. `--system-site-packages` 가상환경도 bs4/pytest 미노출로 실패. 인터넷 가능한 사용자 시스템에서 확인 필요.
- 검증 제한: 인터넷 실제 사이트 동작, Windows PowerShell, macOS, Python 3.11, 방화벽·환경별 프록시, 독립 가상환경 설치는 미검증.
- 산출: `result.json`, `report.md`; HTTP/HTML 차단 및 크기 초과 시 경고/부분 결과.
- 배포: 해당 없음. 앱 공개/브라우저/Production 없음.
- 다음 단계: 의존성 설치 가능한 환경에서 새 venv 설치 → pytest → fixture CLI 실행 및 비밀 문자열 검색. 이후 사용자 승인된 Step 2 정의 시만 확장.

- GitHub 소스: 로컬 컨테이너가 GitHub DNS에 접근 불가. 연결된 GitHub API는 사용 가능하나 로컬 파일 대량 전송 인터페이스 부재로 전체 소스 커밋 미반영. 사용자 ZIP 다운로드 가능.
