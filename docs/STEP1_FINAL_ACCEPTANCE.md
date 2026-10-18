# Fable 5.1 Web Catcher — Step 1 최종 인수·완료 판정

- 판정: **Step 1 완료 (명시된 완료 기준 7/7 충족, 100%)**
- 검증 일자: 2026-10-18 KST
- 기준: 사용자 원본 `fable5.1_step1.txt`; 프로젝트 `REQUIREMENTS.md`와 `AGENTS.md`
- 프로젝트: `hibi89/fable5.1_web_catcher`, `main`
- 최종 구현·테스트 근거 커밋: `9d47bdb06b1b42eca9babfe24f3558d49cf84c37`
- Step 2: **지침 미제공, 구현 미착수**. 후속 채팅에서 지침 원본을 받은 뒤 별도 범위 확정

## 원본 완료 기준 7개 대조

| 원본 완료 기준 | 판정 | 검증 근거 |
| --- | --- | --- |
| 1. 새 가상환경에 requirements 설치 후 실행 | PASS | GitHub Actions Python 3.11 Windows, Ubuntu, macOS 모두 새 venv 생성/설치/pytest 통과 |
| 2. 로컬 fixture CLI에서 result.json과 report.md 생성 | PASS | `test_subprocess_cli`, 실제 fixture의 CLI 실행 및 두 보고서 존재 검사 |
| 3. LLM/API 키/원격 규칙 다운로드 없이 기본 분석 | PASS | 내장 `rules/fingerprints.json` 규칙 16종, 로컬 fixture 네트워크 외부 호출 불필요; 패키지 최초 설치용 pip 다운로드와는 별개 |
| 4. 테스트 모두 통과 | PASS | **최신 코드 기준 26/26** — Windows·Linux·macOS 세 환경 각각 재실행 성공 |
| 5. JSON·Markdown·콘솔에 테스트 비밀값 미노출 | PASS | 기존 민감 쿼리·쿠키·헤더·에러 마스킹 테스트 및 신규 `tests/test_final_acceptance.py`의 토큰·userinfo·리다이렉트 3개 경계 테스트 통과 |
| 6. README에 Windows 및 macOS/Linux 명령 제공 | PASS | `README.md`의 PowerShell 및 macOS/Linux 설치·실행 예시 확인 |
| 7. 실사이트에서 구조를 검증하고 기술 탐지를 강제하지 않음 | PASS | `https://www.python.org/`, `https://example.com/` 각각 HTTP 200 및 JSON·Markdown·evidence 참조 검증 성공; 기술명을 PASS 조건으로 삼지 않음 |

## 최신 최종 테스트 증거

| 환경 | 버전 | 테스트 | GitHub Actions |
| --- | --- | --- | --- |
| Windows Server 2022 | Python 3.11 | **26 passed, 6.73초** | [실행 39112750832](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39112750832) |
| Ubuntu 24.04 | Python 3.11 | **26 passed, 6.58초** | [실행 39112888488](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39112888488) |
| macOS 15 | Python 3.11 | **26 passed, 41.63초** | [실행 39112888546](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39112888546) |

기존 23개 테스트에 마지막 검증 3개를 추가했다. 추가 시나리오: 리다이렉트 5회 상한, `file://`로의 리다이렉트 거부, URL userinfo·민감 쿼리 비노출. Windows·Linux·macOS에서 모두 같은 **26개**를 검사했다.

## 실제 공개 URL 두 곳 — 추가 경로 탐색·인증 없이 GET

| 대상 | 상태 | 실제 저장·스키마 결과 | GitHub Actions |
| --- | --- | --- | --- |
| `https://www.python.org/` | HTTP 200 / 성공 | JSON 2,444 bytes·Markdown 1,742 bytes, evidence 1, 경고 0, nginx 인프라 **추정** | [실행 39111940046](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39111940046) |
| `https://example.com/` | HTTP 200 / 성공 | JSON 1,513 bytes·Markdown 1,676 bytes, evidence 2, 경고 0 | [실행 39112750908](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39112750908) |

두 검증 모두 필수 schema, `static` 모드, `api`·`charts` 비활성 구조, evidence IDs의 실제 참조, confidence 0~1, Markdown 보고서 생성 등을 확인했다. 실제로 사용된 내부 기술이나 서버 코드의 정확성을 확인한 것은 아니다.

결과 아티팩트는 GitHub Actions에 7일 보관: Python 공식 사이트 `python-org-static-scan` (ID `12130523685`), example.com `step1-example-com-report` (ID `12131455685`). 만료 후에도 검사 로그 및 이 완료 문서가 남는다.

## 범위 한계와 남겨둘 주의사항

- Step 1은 **정적 단일 페이지 GET**, 제한적 리다이렉트, 읽기 전용 공개 단서 분석만 수행한다. 로그인, 임의 API/민감 경로 probing, 자바스크립트 실행, 다중 페이지 크롤링, Playwright, LLM, 웹 UI는 구현하지 않았다.
- 기술 탐지는 가시적 응답 근거의 휴리스틱 추정이다. `unknown`은 정상적인 결과이며 `confidence`는 실제 확률이 아니다.
- 무작위·비신뢰 URL 입력에 대한 네트워크 격리/SSRF 프록시는 구현되어 있지 않다. 따라서 사설망·민감 서버에서 불특정 URL을 무감독 실행하는 운영 형태는 금지한다. 이는 원본 Step 1의 완료 조건에 없는 **운영 배포 보안 확장** 항목이다.
- 최초 GitHub 커밋에 포함된 `tests/test_static.py.bak`는 백업 보존 원칙에 따라 그대로 둔다. 선택적 정리이며 Step 1 필수 완료 기준의 미달 항목이 아니다.
- 별도 배포/Vercel/Production URL은 없다. 이 결과물은 실행 가능한 **로컬 CLI**다.

## 새 채팅방에서 Step 2 시작 절차

1. `p3`로 `hibi89/fable5.1_web_catcher`의 최신 `main`을 복원한다.
2. `AGENTS.md`, `HANDOFF.md`, `STATUS.md`, `REQUIREMENTS.md`, **본 문서** 및 현재 소스를 읽는다.
3. 사용자에게서 **아직 제공되지 않은 Step 2 지침 원본**을 전달받는다. 내용을 미리 추정해 코딩하지 않는다.
4. Step 1 완료 상태와 CI를 유지한 채 Step 2 범위·구현·테스트를 계획한다. Step 2는 이 문서와 별개의 단계다.

**최종 판정:** 원본 `fable5.1_step1.txt`의 7개 완료 조건을 모두 충족했다. Step 1 작업 종료. Step 2의 지침은 아직 받지 않았다.
