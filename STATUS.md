# STATUS.md — Step 1 진행 상태

- 상태: **Step 1 구현 및 GitHub 반영 완료, Windows·Linux Python 3.11 독립 새 가상환경 설치 및 pytest 각각 23/23 PASS**. macOS·다수 실제 공개 사이트 결과 미검증.
- 범위: 첨부 `fable5.1_step1.txt`의 공개 HTTP/HTML 정적 기술 근거 스캐너.
- 구현: CLI, 수집/마스킹/판별/보고서/자체 규칙 파일, 오프라인 fixture 서버, pytest.
- Windows 검증(사용자 제공 터미널 기록, 2026-10-18 KST): `python scan.py https://example.com --out ./out/demo` 성공, `result.json` 및 `report.md` 생성 메시지 확인. `python -m pytest -q` 최초 19 PASS·3 FAIL(cp949 UnicodeDecodeError) → 테스트의 `read_text(encoding="utf-8")` 수정 후 **22 PASS / 0 FAIL / 5.17초**.
- GitHub Actions: `.github/workflows/windows-python311.yml` · `windows-2022` · Python 3.11 · `.venv-ci` 새 생성 · `pip install -r requirements.txt` → `pytest -q`. **2026-10-18 17:21 KST, run 39111101377, 23/23 PASS / 5.19초, 결론 success**. GitHub 로그에서 설치와 테스트 단계 각각 success 확인. 읽기 전용 토큰 권한만 요청, 배포/외부 사이트 탐색 없음.
- 최초 CI 실패(run 39110748770): 21/22 PASS, 리디렉션된 Windows cp1252 표준출력에 한글 출력 시 `UnicodeEncodeError`. `scan.py` 출력 오류 정책을 `backslashreplace`로 정정하고 강제 cp1252 회귀 테스트 1건 추가 후 재실행 성공.
- 컨테이너 검증(2026-10-18 KST): Python 3.13.5, 오프라인 fixture pytest **22/22 PASS**. 단 독립 격리 `.venv` 설치는 패키지 wheel/DNS 부재로 검증 불가(동일 방법 재시도 불필요).
- GitHub Actions Linux 1회 검증: `.github/workflows/linux-python311.yml` · `ubuntu-24.04` / Python 3.11 · 새 `.venv-ci` 생성 · 의존성 설치 · pytest **23/23 PASS / 5.03초** (run `39111476135`, 2026-10-18 17:27 KST, `conclusion=success`). 자체 workflow 파일 push 시 실행 및 수동 `workflow_dispatch`만 허용하며 일반 소스 변경의 Linux 자동 반복 검증은 설정하지 않음. 권한 `contents: read`, 제한 10분. https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39111476135
- 의존성: GitHub Actions Windows·Linux Python 3.11 새 가상환경에서 pip 설치·전체 테스트 재현성 **확인**. 사용자의 로컬 가상환경 설치 과정 자체는 로그 미확보.
- 보안: 테스트용 민감 쿼리/쿠키/헤더 값 비노출을 포함한 fixture 테스트 통과. 임의 경로 probing, 로그인, 동적 JS 실행 없음. 신뢰할 수 없는 URL의 SSRF 보호 프록시는 구현되지 않았음.
- 배포: **미적용**(로컬 CLI 프로젝트, Vercel/Production 없음).
- GitHub 소스: `hibi89/fable5.1_web_catcher` `main`, 최초 소스 커밋 `cbef84bd388f8b619d2d388bf6cf5a87c617ca45` (2026-10-18 17:03:47 KST), GitHub 직접 재조회 확인. CI 구현 `6ffb0dc0520d14e7911e0cbe3ebbef5cef568ad8`, 인코딩·회귀 테스트 수정 `78fe2ce4739825b8e9a69d471cfaacc03fc7c063`.
- 확인된 정리 항목: `tests/test_static.py.bak`가 최초 커밋에 포함됨. 원본 보존을 위해 임의 삭제하지 않음; 추후 필요 시 `*.bak` 추적 제외 및 저장소 정리 검토.
- 다음 단계: (1) 로컬은 필요 시 `git pull origin main`으로 동기화하고 pytest 23개 재검증, (2) macOS 및 실제 공개 URL 1개 이상의 결과 스키마 검증은 선택 미완료, (3) Step 2 동적 분석은 설계·비용·승인 후 별도 구현. 추적 중인 `.bak`는 보존(임의 삭제하지 않음).
- 상태 확인: 2026-10-18 17:27 KST. 문서 근거: 사용자 PowerShell, GitHub Windows CI run `39111101377` 23/23, Linux CI run `39111476135` 23/23 로그. Linux 검증용 코드 변경 없음; workflow 추가 커밋 `d3cd802ce88b6784e5a028dee9915939f66f0506`. Windows CI 보존; Vercel 미적용.
