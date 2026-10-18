# Fable 5.1 Web Catcher — Step 5 수용 검사 (2026-10-19 KST)

## 범위 및 사실 확인
- 사용자 제공 지침서: `5.1_step5.txt`. 목표는 **권한 보유 URL 순차 배치 / 두 저장된 result.json 비교 / 기존 관찰 JSON 구조로 참고 계약 내보내기 / 한국어 배치 요약**. 독립 웹 UI, DB, 작업 큐, Docker, 자동 로그인, 인증 우회, 비공개 데이터 수집, 소스코드 복제 없음.
- [PR #16](https://github.com/hibi89/fable5.1_web_catcher/pull/16) **main 병합 완료** SHA `7de7e26faec46120bbdfb509892ca267cea514c4`. 최종 검증 소스 SHA `6f32544299ea5181d4a90321f32e7706857781eb`.
- 신규 `scanner/batch.py`, `scanner/compare.py`, `scanner/contracts.py`, `scanner/step5_common.py`; `scan.py` CLI 옵션 추가; `README.md` 사용 예제, `requirements.txt` 오프라인 JSON Schema 검증 의존성, `tests/test_batch.py`, `tests/test_compare.py`, `tests/test_contracts.py` 추가.
- 기존 Step1~4 기본 명령, `scan()`, `--runtime`, `--record`, `--llm`, `--from-result --llm-dry-run` 경로는 유지. Step5 모드에는 **실제/Mock LLM 호출 자체가 없음**.

## CLI
```powershell
# UTF-8 파일에 URL 한 줄 하나, 빈 줄/주석 생략
python scan.py --batch urls.txt --out ./out/batch
python scan.py --batch urls.txt --runtime --wait 10 --out ./out/batch-runtime
python scan.py --batch urls.txt --delay 3 --max-urls 50 --out ./out/batch-other

python scan.py --compare old/result.json new/result.json --out ./out/diff
python scan.py --from-result ./out/demo/result.json --export-contracts
# 기본 contracts 위치: ./out/demo/contracts/
```
- **배치**: 순차 실행만 지원. 2초 기본 대기(최소1), 50 URL 기본 상한(옵션 최대500), 완전히 동일한 정규화 URL만 중복 제거. 원래 query/path 순서는 메모리에서 보존, fragment 삭제. 잘못된 줄은 행 번호와 error enum 기록. 사이트별 매번 별도 기존 `scan()` 호출 (runtime은 각 사이트별 새 격리 Chromium 컨텍스트/쿠키 공유 없음). 개별 실패 후 나머지 계속, 429 이후 동일 origin 후속 대상 skip (추가 우회/재시도 없음).
- **상태 저장**: `batch_manifest.json` / `batch_summary.json` / `batch_report.md` / `targets/001-site/{result.json,report.md}`. pending→running→success/partial/failed/interrupt/skipped, UTC 시각/경과·상대 파일 링크/비식별 오류, 각 대상마다 atomic replace 체크포인트. Ctrl+C는 기존 결과 보존/현재 interrupted/나머지 pending/exit130. 출력 폴더가 이미 있으면 명확한 오류 (조용히 덮어쓰기 안 함). 자동 resume/병렬 작업은 미지원.
- **프라이버시**: 배치 데이터 원본은 임시 스캔 폴더에서 처리하고, 각 결과에 실행별 무작위 비식별 origin 별칭(예: `https://batch-<run>-origin-001.batch.invalid/`)과 표준 path segment만 남긴 후 저장. query 값, 원본 hostname, 임의 식별 경로, evidence 원문·로그·민감 JSON key 등 삭제/일반화. 따라서 배치 개별 결과는 원본 데이터 전체 재현용이 아닌 보수적 결과이며, 서로 다른 배치 run끼리 동일 origin임을 **확정하지 않음**. 외부 공유 전 사람 검토 권장; 모든 PII 탐지 완전 보장 아님.
- **저장 결과 비교**: 파일만 읽고 API/브라우저·LLM 통신 없음. 타입/버전 `schema_version=1.0` 또는 버전 누락 구버전만 허용, 6MB 상한. 동일 사이트/다른 사이트/식별불명 구분, 기술 버전·점수·evidence 종류, HTTP method + 정확한 기존 origin + 일반화 path, query key 허용목록, HTTP status/content type/JSON 구조 차이, 차트 라이브러리·개수·연관 후보 개수 비교. evidence ID/배열 순서/실행 시각/차트 ID·selector 차이만으로 기술 변화 확정 안 함. 다른 origin 동일 path는 매칭 안 함, 경로 일반화 충돌은 모호성 표시. **미관찰 ≠ 삭제**, JSON 차이 ≠ breaking change.
- **관찰 기반 데이터 계약**: 오직 `json_structure`가 실제 저장된 응답 표본만 JSON Schema Draft 2020-12로 변환. 같은 origin/path/method 내에서도 status/content type별 variant 유지; 타입 충돌 anyOf, null·빈 배열 unknown, 표본 미확인 required/빈도는 unknown. `additionalProperties:false`, `required`, 값 기반 enum/default/examples, 값 범위/format/단위/차트 x-y 자동 확정 금지. `json_prefix_structure`는 미완성 부분 힌트이므로 전체 Schema 승격 안 함. 출력: `contracts.json`, `contracts.md`, `schemas/endpoint-NNN.schema.json` (전체 구조가 있을 때만 생성). 포괄적 API 계약이 아니라 참고 자료.

## Step 5 완료 확인 (사용자 지침서 필수 3연속)
- **로컬 fixture URL 3개 순차 스캔 → 3개 대상 폴더·manifest·요약/개별 결과 확인**: 통과
- **생성된 결과 2개를 `run_compare`에 넣어 `diff.json`, `diff.md` 생성**: 통과
- **생성된 결과 1개를 `run_contracts`에 넣어 `contracts.md`/JSON 생성**: 통과 (정적 스캔 fixture에는 API 구조가 없어 스키마 파일은 0개, 관찰 구조 없음으로 표시)
- 추가 별도 fixture: 배치 결과에서 **API JSON 구조가 관찰된 경우** 무작위 호스트 별칭으로 익명화한 결과를 다시 계약으로 변환해 JSON Schema 파일 1개와 Draft2020-12 문법 확인: 통과.
- 다양한 단위 fixture: 중복 URL/fragment 제거, query 순서 유지, 잘못된 줄 번호, 429 동일 origin 건너뛰기, 일부 실패 후 다음 진행, Ctrl+C로 기존 결과 보존/나머지 pending, 기존 폴더 덮어쓰기 방지, 세션 격리 코드 경로, 개인정보 포함 샘플 값·호스트·경로·콘솔 비노출, 스키마 버전 거부, 타입 충돌·null·빈 배열·중첩, 서로 다른 origin 비교, LLM 옵션 상호 배타 및 기존 회귀.

## 자동 테스트 증거
- 최신 최종 소스 `6f32544299ea5181d4a90321f32e7706857781eb` 기준:
  - [Windows GitHub Actions run 39148097390](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39148097390): **123/123 PASS** (Step 1~4 + Step 5 로컬 unit/CLI/fixture).
  - [Ubuntu headed Chromium run 39148097419](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39148097419): **23/23 PASS**, 선택 공개 페이지 smoke **4/4 PASS**.
- Chromium의 23개는 **기존 Step 2~3 회귀 검증**이다. Step 5의 다중 실제 외부 사이트 runtime 브라우저 수집은 새로 실증하지 않았고, 배치 `--runtime`은 기존 브라우저 재사용 코드와 옵션 전달을 로컬 테스트로 검증했다. 실제 OpenAI API 요청도 없음.
- 초기 CI 117 PASS/3 FAIL이 있었으나 계약 테스트의 설명 문구 required 혼동, Windows UTF-8 읽기 누락, 안전한 필드명 allowlist 미비를 수정. 그 후 개인정보를 유지하면서 익명화된 배치 endpoint가 계약에 재사용될 수 있도록 임시 pseudo-origin으로 변경하고 통합 테스트 보완. **최신 run 성공 결과만 최종 PASS로 인정.**

## 사용자 완료 조건 10개 판정
1. UTF-8 urls.txt 복수 사이트 순차 스캔: **PASS (3개 localhost fixture)**.
2. 일부 실패해도 다음 대상/기존 결과 보존: **PASS (fixture)**.
3. 배치 manifest·summary·대상 보고서: **PASS**.
4. 저장된 두 result.json 오프라인 비교: **PASS**.
5. 미관찰과 실제 삭제 구분: **PASS**.
6. 이미 관찰한 JSON 구조 계약과 참고 Schema: **PASS**.
7. unknown/표본·상한/혼합 타입 불확실성 표시: **PASS**.
8. 새 출력 개인정보/원문 비노출: **PASS (synthetic 개인정보 fixture 범위에서 검증; 모든 비밀 자동 탐지 보장 아님)**.
9. 이전 Step1~4/신규 Step5 CI: **PASS (Windows123/Chromium23/선택 공개4)**.
10. README 사용 예제와 종료코드·한계: **PASS**.

**결론:** 사용자 Step 5 구현/자동 수용 기준 **10/10**, 전달된 Step 1~5의 구현/자동·Mock 기준 **5/5 단계 완료**. 실제 OpenAI 유료 API smoke, 실제 사용자 Windows 수동 Record 필터→차트/API 연관성, 공개 사이트 전체 배치 runtime 현장 시험은 별도 **미검증**. 최종 상용제품 100%라는 뜻은 아니다.

## 남은 제한
- 각 배치 대상의 임시 처리 파일은 정상/예외 처리 때 삭제되나 예기치 않은 프로세스 강제 종료 등에서 OS 임시 파일이 남을 가능성을 완전히 배제할 수 없다.
- 권한 없는 URL을 서버에서 실행하면 SSRF 등 위험이 생길 수 있다. 개인용 로컬 도구이며 인터넷 공개 서버 배포용이 아니다.
- 구버전 결과의 `json_structure`에 없는 필드 존재 빈도·표본별 필수여부를 재구성할 수 없다. 혼합 타입/경로 정규화는 보수적으로 표현한다.
- 배치 저장 결과의 무작위 origin 익명화 때문에 **별도 실행끼리 동일 origin 판정을 확정할 수 없다**. 비교 모드에서 모호성 경고가 발생한다.
- Step3 CDP 미매칭 발생 이유의 완전한 수정은 미진행; 기존 안전거부 및 `cdp_decoded_diagnostic` 기록 유지.
