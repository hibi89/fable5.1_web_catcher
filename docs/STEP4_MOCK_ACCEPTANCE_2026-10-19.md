# Fable 5.1 Web Catcher — Step 4 Mock/회귀 인수 결과 (2026-10-19 KST)

## 기준과 범위
- 사용자 원본: `5.1_step4.txt` (2026-10-19 수령).
- 역할: 원래 Step 1~3이 수집한 근거를 **안전하게 최소 정제해 OpenAI API에 명시적으로 제공**하고, 로컬 검증된 구조화 응답만 별도 한국어 분석 보고서로 렌더링.
- **[PR #12](https://github.com/hibi89/fable5.1_web_catcher/pull/12) main 병합 완료:** `0fb2effcf1be3504d323231120cce70d23491d82`. 검증 소스 SHA `3061db1b8fc7706a715975b4fe7e077eb05e3ff9`.
- 실제 OpenAI 유료 API에 대한 요청 **0회**. 사용자의 API 키/모델 ID가 제공되지 않아 smoke 미실행; 자동 CI는 실제 서비스 호출 대신 Mock SDK 응답만 테스트함.
- 공식 OpenAI Python SDK `openai>=3.13,<4`; `OpenAI(...).responses.create(model=...,input=[...],text={format:{type:json_schema,...}},store=False)` Structured Outputs 경로. SDK 자동 재시도 0, 429/5xx만 코드 내 최대 1회 재시도.
- 설치 모델 ID는 `OPENAI_MODEL` 또는 `--model`에서만, 키는 `OPENAI_API_KEY` 환경변수에서만 가져온다. 코드에 임의 모델명·키를 하드코딩하지 않음.

## 구현 파일
- 신규 `scanner/llm_payload.py`: `result.json` allowlist 재구성. 증거 우선·중복 제거, 근거 참조 무결성, host `origin_n` 별칭, 경로 사용자 식별자/비인가 JSON key 일반화. 원본 evidence 값/HTML/JS/쿠키/사용자 입력/주소/경고 원문 전송 배제. 근거 최대45, 탐지 최대35, API24, 차트16, 매핑20, 28KiB 제한. 생략 건수·이유 기록.
- 신규 `scanner/llm_client.py`: OpenAI Responses API 사용, system/user 데이터 분리, untrusted prompt injection 금지 지시, tool 접속 제공 없음, 오류 분류 및 제한 재시도.
- 신규 `scanner/llm_validate.py`: JSON schema 추가 필드 거부, 설명 길이, finding/evidence/endpoint/chart ID 참조 제한, 기존 기술 카탈로그 외 임의 기술 명시 검사. confidence는 LLM 출력에 허용하지 않으며 기존 엔진에서만 읽음.
- 신규 `scanner/llm_report.py`: 입력 Markdown/HTML/링크 이스케이프하고 7개 한국어 섹션 로컬 렌더링. 기존 엔진 점수, 관찰·추정·추천 별도 표기, 차트↔API 끝까지 연관 후보만 제시.
- 신규 `scanner/llm_flow.py`: `--llm-dry-run` 전송 예정 JSON 미리보기(외부 API 호출 없음), 결과 sha256, 프롬프트/스키마 버전, SDK usage·생략 경고를 별도 `llm_report.json`/ `llm_report.md`로 저장. 오류 시 원본 `result.json`/`report.md` 보존.
- 변경 `scan.py`: 기존 `scan(URL)`, `--runtime`, `--record` CLI 보존. 신규 `--from-result FILE --llm|--llm-dry-run`, `--model`; 모델 호출은 명시적 `--llm`에 한정.
- `requirements.txt`에 공식 SDK, `.gitignore`에 `.env`·임시 미리보기/LLM 산출물, 신규 `.env.example`에 빈 환경 변수명. `README.md`에 프라이버시, 비용, 설정, dry-run 검수·명령/실패 안내.
- `rules/fingerprints.json`: **기존 16기술·30신호 → 35기술·50개 서로 구분되는 패턴 신호**. 고유 규칙 ID/분류·근거 source/정규식·휴리스틱 weight·한계 note·검증 memo 추가. 신규 CMS/프런트 자산/서버 헤더 등은 **관찰 단서에 한정**, CDN/쿠키를 앱 백엔드 확정으로 승격하지 않음.
- `tests/test_fingerprint_rules_v4.py`, `test_llm_payload.py`, `test_llm_validation.py`, `test_llm_report.py`: 총 50개 신호에 대한 **synthetic 양성/음성 fixture**, 샘플 개인정보/호스트/URL 차단, 미리보기 호출 0회, payload 한도/중복/참조, 401/429/5xx/타임아웃/거절/잘림/불량 JSON, confidence 추가 필드 거부, 로컬 Markdown 안전 처리, 기존 보고서 보존 등. `tests/test_fingerprints.py`의 구 16개 기술 필수 검사를 정확한 집합 고정에서 **기존 16개 모두 필수 포함**으로 바꿔 추가 규칙을 수용.

## 사용자 실행 명령 (PowerShell)
```powershell
python -m pip install -r requirements.txt
python scan.py --from-result ./out/demo/result.json --llm-dry-run
notepad ./out/demo/llm_payload.preview.json

# 실제 API 호출은 이용자가 사용 모델과 키를 준비한 경우만:
$env:OPENAI_API_KEY = "사용자 본인 키" 
$env:OPENAI_MODEL = "본인 API 접근 가능한 모델 ID"
python scan.py --from-result ./out/demo/result.json --llm --model $env:OPENAI_MODEL

# 또는 처음부터 스캔:
python scan.py URL --runtime --llm --model $env:OPENAI_MODEL --out ./out/demo
python scan.py URL --record --llm --model $env:OPENAI_MODEL --out ./out/demo
```
- `--llm-dry-run`: 실제 전송과 **동일한** sanitizer/payload builder를 이용하여 `llm_payload.preview.json` 생성, LLM 네트워크 호출 0회. **미리보기 검토 후 유료 API 호출** 권장. 키가 환경변수에 존재한다는 이유만으로 자동 호출하지 않음.
- `--llm`에서 모델 또는 키 누락·401/403·429·5xx·시간 초과·모델 거절·출력 스키마 오류 등은 종료 코드 **3**; 기초 스캔 오류는 기존 **2**, 성공은 **0**. 실패 시 원본 `report.md`가 기본 보고서.

## 실제 자동 검증
- GitHub Actions Windows Python 3.11: [run 39142853498](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39142853498) **91/91 PASS**.
- Ubuntu headed Chromium 실제 브라우저 fixture: [run 39142853476](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39142853476) **23/23 PASS**.
- 같은 Ubuntu 실행의 공개 웹페이지 선택적 smoke: **4/4 PASS**.
- 이 테스트는 Step 4 모델 호출 관련해서는 **Mock SDK + 로컬 fixture**이며, 외부 실제 OpenAI 모델의 응답 충실도/프롬프트 주입 방어를 직접 증명하지 않음.
- 테스트 전 과정에 실제 `OPENAI_API_KEY`를 제공하거나 실제 LLM 호출을 수행하지 않음.

## Step 4 완료 기준 10개 항목
1. 키 없이 기존 Step 1~3 기능 — **PASS** (회귀 자동 테스트)
2. `--llm-dry-run` 전송 예정 파일 — **PASS** (offline mock)
3. 명시적 `--llm`에서만 API 호출 경로 — **PASS** (코드+mock)
4. 스키마 검증 후 별도 JSON/Markdown 생성 — **PASS** (mock)
5. 무근거 기술/버전/참조/score 차단 — **PASS(구현한 로컬 검증 범위)**, 모든 환각 완전 차단 보장은 아님
6. 원 사이트 기술과 재구현 제안 별도 — **PASS** (mock/renderer)
7. API 실패에도 기존 파일 보존 — **PASS** (mock)
8. 신규 Mock 및 기존 회귀 통과 — **PASS (91 / 23 / 4)**.
9. 실제 API 테스트 결과 구분 — **PASS (실제 API 미실행 명시)**.
10. README 데이터 전송·비용·설정·한계 — **PASS**.

**판정**: Step 4의 **API 비호출 모드·Mock 자동 인수 기준 10/10 구현 및 테스트 완료**. 실서비스 OpenAI API 요청/실제 모델 품질 평가는 *아직 검증 안 됨*. 이 구분을 제외하고 '실사용 LLM 통합 100%'라고 표현하지 않는다.

## 남아 있는 제한
1. regex/허용목록은 개인정보/기업 비밀의 완벽한 익명화를 보장하지 못함. 실제 민감 프로젝트는 dry-run 결과를 인간이 검토하고 명시적으로 승인한 뒤 API 호출.
2. 생성형 모델 설명의 모든 사실/환각을 정적으로 증명할 수 없다. 구조적 참조·허용 기술/score 검증만 강제하고 모순 설명 가능성은 별도로 경고.
3. 약 50개 신호는 synthetic 양성/음성 테스트 통과한 **휴리스틱 룰 수**이지 50개 실서비스 독립 성공 사례나 모든 사이트 탐지율 검증이 아님.
4. Step 3 실제 사용자의 수동 필터 변화→차트/API 후보 검증은 독립 미완 사항으로 그대로 유지. Step 4를 추가했다고 이 실사용 검증이 대체되지 않음.
5. 공공 서버 배포/SSRF 격리, 웹 UI, 자동 원사이트 소스 복제, 모델 코드 실행은 범위 밖.
