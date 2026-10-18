# STATUS.md — Step 1 진행 상태

- 상태: **Step 1 구현 완료, GitHub `main` 최초 소스 반영 확인, Windows Python 3.11 가상환경 테스트 22/22 PASS**. 실제 인터넷 사이트 전체 호환성 및 다른 OS 미검증.
- 범위: 첨부 `fable5.1_step1.txt`의 공개 HTTP/HTML 정적 기술 근거 스캐너.
- 구현: CLI, 수집/마스킹/판별/보고서/자체 규칙 파일, 오프라인 fixture 서버, pytest.
- Windows 검증(사용자 제공 터미널 기록, 2026-10-18 KST): `python scan.py https://example.com --out ./out/demo` 성공, `result.json` 및 `report.md` 생성 메시지 확인. `python -m pytest -q` 최초 19 PASS·3 FAIL(cp949 UnicodeDecodeError) → 테스트의 `read_text(encoding="utf-8")` 수정 후 **22 PASS / 0 FAIL / 5.17초**.
- 컨테이너 검증(2026-10-18 KST): Python 3.13.5, 오프라인 fixture pytest **22/22 PASS**. 단 독립 격리 `.venv` 설치는 패키지 wheel/DNS 부재로 검증 불가(동일 방법 재시도 불필요).
- 의존성: 사용자 환경에서 `(.venv)` 활성화와 CLI/pytest 실행은 확인됨. `requirements.txt`의 새 가상환경 설치 과정 자체를 기록으로 재확인하지 않았으므로 신규 설치 재현성은 **미검증**.
- 보안: 테스트용 민감 쿼리/쿠키/헤더 값 비노출을 포함한 fixture 테스트 통과. 임의 경로 probing, 로그인, 동적 JS 실행 없음. 신뢰할 수 없는 URL의 SSRF 보호 프록시는 구현되지 않았음.
- 배포: **미적용**(로컬 CLI 프로젝트, Vercel/Production 없음).
- GitHub 소스: `hibi89/fable5.1_web_catcher` `main`, 최초 소스 커밋 `cbef84bd388f8b619d2d388bf6cf5a87c617ca45` (2026-10-18 17:03:47 KST), GitHub 직접 재조회 확인.
- 확인된 정리 항목: `tests/test_static.py.bak`가 최초 커밋에 포함됨. 원본 보존을 위해 임의 삭제하지 않음; 추후 필요 시 `*.bak` 추적 제외 및 저장소 정리 검토.
- 다음 단계: (1) 현재 GitHub 기준으로 로컬 `git pull` 동기화 여부 확인, (2) 독립 새 환경 및 다양한 공개 URL에서 구조 검증, (3) Step 2는 별도 설계·비용·승인 후 진행.
- 상태 확인: 2026-10-18 17:04 KST. 문서 근거: 최초 소스 커밋 SHA 및 사용자 제공 PowerShell 실행 로그.
