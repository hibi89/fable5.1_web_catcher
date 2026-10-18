# 2026-10-19 KST — p3 Step 5 최종 자동 인수 완료 및 후속 업무

- 사용자 지침 `5.1_step5.txt`에 대한 **Step 5 구현/수용 기준 10/10**. [PR #16](https://github.com/hibi89/fable5.1_web_catcher/pull/16) 병합 SHA `7de7e26faec46120bbdfb509892ca267cea514c4`, 검증 source `6f32544299ea5181d4a90321f32e7706857781eb`.
- 파일: `scanner/step5_common.py`, `scanner/batch.py`, `scanner/compare.py`, `scanner/contracts.py`; `scan.py` argparse 3모드 + `--delay`, `--max-urls`, `README.md`, `requirements.txt` jsonschema 테스트 검증; `tests/test_batch.py`, `tests/test_compare.py`, `tests/test_contracts.py` 신규.
- 배치: `python scan.py --batch urls.txt --out ./out/batch` (또는 `--runtime --wait 10`). 순차 실행만, 별도 브라우저 컨텍스트, 기본 2초 지연/상한50, 입력 line 오류·중복 제거, origin 429 skip, Ctrl+C 부분완료 보존, atomic checkpoint; 원본 URL/host/쿼리/경로 비밀은 실행별 익명 pseudo-origin으로 치환, 기존 결과를 조용히 덮어쓰지 않음.
- 비교: `python scan.py --compare old/result.json new/result.json --out ./out/diff`: 파일만 사용, 동일/이종/식별불명 구분, 기술/evidence/API normalized origin+path/JSON shape/차트 후보 및 수집 범위 메타데이터 보수적 diff, 미관찰 != 삭제.
- 계약: `python scan.py --from-result ./out/demo/result.json --export-contracts` (기본 `./out/demo/contracts/`): 관찰 JSON을 status/content-type variant 및 Draft2020-12 참고 schemas와 대시보드 필드 후보 표로 변환. `required`/실제 값/enum/date format 등 임의 확정 금지; 부분 JSON 샘플은 전체 계약으로 승격하지 않음.
- 최종 CI **Windows 123/123 PASS** [39148097390](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39148097390), **실제 headed Chromium 23/23 PASS + 선택 공개 홈페이지 smoke 4/4** [39148097419](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39148097419). 사용자 Step5 완료 요구 순서인 **localhost URL 3개 배치 → 2개 결과 diff → 한 결과 contracts.md 생성**이 연속 fixture로 검증됨. 익명 배치 endpoint가 샘플 스키마를 생성하는 별도 fixture도 PASS.
- **미확인 항목**: 실제 여러 외부 사이트 배치 Runtime의 장기 운영/자격증명·브라우저 현장 분리, 사용자 Windows Step3 수동 필터→차트/API 근거, Step4 실제 OpenAI 모델 API. Step3 CDP 길이 이벤트 미매칭은 여전히 fail-closed. 자동 resume, 공개 SaaS/SSRF 격리, 웹 UI/DB/Docker는 Step5 요구에서 제외.
- 문서 `docs/STEP5_FINAL_ACCEPTANCE_2026-10-19.md`; 이후 `ㄱ`은 사용자 지침 Step1~5 재구현이 아니라 **남은 현장 수용 검증 / 다음 명시 지침 한 단위**부터 이어갈 것.
- 전달된 Step1~5 **구현/자동·Mock 인수 5/5단계**로 진도 유의미 상승, 그러나 실사용 모든 배포환경 100%와 혼동 금지.

---

# 2026-10-19 KST — p3 CDP fail-closed 원인 코드 작업 인수

- 3회×8건 localhost Chromium 조사: `DecodedLengthTracker.decide`의 `no_cdp_match` **4/8, 5/8, 3/8**; 500ms 대기만으로 사라지지 않음. 별도 이벤트 listener 검사는 데이터를 수집하지 못했으므로 **frame ID vs CDP 전달 vs request-key mapping 원인 확정 불가**. [PR #14](https://github.com/hibi89/fable5.1_web_catcher/pull/14) diagnostic-only closed unmerged.
- **[PR #15](https://github.com/hibi89/fable5.1_web_catcher/pull/15) main merge `f6cf9577941fff829cab0b827b5b95fd7e8eac88`**, verified source `385851177b20339c167957d2579bb2a18694b804`. `scanner/cdp_decoded_size.py`의 `refusal_reason(request)`가 값 없는 고정 원인 enum만 산출하고 `scanner/record_scan.py`가 `compressed_decoded_unavailable`인 승인 JSON에 한해 `cdp_decoded_diagnostic` 저장. 원본 URI/요청 ID/응답값/인증정보/원시 헤더 미저장. **성공률/메모리 상한/필터 변경 없음**.
- CI **Windows 99/99 PASS** [39145907566](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39145907566); **Chromium 23/23 PASS + 공개 smoke 4/4** [39145907594](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39145907594). 초기 gzip positive test 22/23에서 기존 안전 거부를 실패로 간주하였던 fixture를 수정, 성공 시 타입 구조 검증·거부 시 원문 null 및 진단 enum 검증을 유지.
- 근거 `docs/STEP3_CDP_MISMATCH_DIAGNOSTICS_2026-10-19.md`. 사용자 Windows 필터/차트/API 인과 후보 실증 및 실제 OpenAI API smoke 미실시. 다음 `ㄱ`은 이슈 재실행보다 **CDP 미매칭 발생 이유를 깊게 추적할 별도 명확한 접근** 또는 실제 현장 Record로 한 단위 진행. 현재 제품 전체 완료율 변동 없음; Step1~4 원본 자동/Mock 인수 4/4 그대로.

---

# 2026-10-19 KST — p3 Step 4 공식 SDK 오프라인 HTTP 인수

- 다음 `ㄱ` 진행 결과: 실제 OpenAI Python SDK를 설치한 상태에서 `httpx2.MockTransport`로 모든 요청을 메모리 내부에서 종료하는 end-to-end 테스트를 7개 추가. **실제 OpenAI API 0회, 비용 0**. `responses.create` POST, JSON schema strict, 도구 미제공, `store=false`, 개인정보 정제, 400/401/429/500 retry 1회 상한, refusal/incomplete 및 usage 읽기 확인.
- [PR #13](https://github.com/hibi89/fable5.1_web_catcher/pull/13) main merge **`1339baf0a76e291a8f7fea2698b053cf9351c1a2`**; tested source `42f481c821189e54c3b66b00dff17d767351b376`. 제품 코드 수정 없음. 테스트 `tests/test_llm_sdk_transport.py`, `tests/browser_record_check.py` 기대값 보완.
- 최종 **Windows 98/98 PASS** run `39144159568`, **Chromium 23/23 PASS + 공개 smoke 4/4 PASS** run `39144159553`.
- 초기 Chromium gzip CDP 본문 길이 관찰에서 **2회 연속 22/23**, `compressed_decoded_unavailable`이 각각 작은/큰 gzip에서 발생. 이는 브라우저 decoded length 이벤트 미확정 시 안전하게 본문을 거부하는 기존 **fail-closed** 정책으로 비밀/대용량 데이터 노출 없이 종료. 기존 fixture가 언제나 positive 성공을 강제해 과도했다. 최종 테스트는 이 보수적 거부를 **별도 상태로 인정**, 정상 구조 검출이 발생했을 때 내용 검증은 유지. **CDP 성공률 문제 자체는 해결됐다고 주장하지 말 것.**
- 별도 `docs/STEP4_OFFICIAL_SDK_OFFLINE_2026-10-19.md` 참조. 사용자 실사이트 Record 필터 조작 검증 및 실제 OpenAI 유료 모델 smoke는 모두 미실시. 다음 `ㄱ`에서는 반복 재실행이 아니라 CDP 이벤트 누락 원인의 **값 없는 진단/정량화** 또는 Windows 사용자 현장 실증 범위를 한 단위 진행.
- Step 1~4 전달 원본 자동/Mock 구현은 4/4 단계 통과 유지; 실제 제품 종합 %는 최종 출시 범위 미확정이라 부풀리지 않음.

---

# 2026-10-19 KST — Fable Web Catcher Step 4 구현/Mock 검증 후 인수

- 사용자 제공 파일 `5.1_step4.txt`의 요구 Step 4 완료 기준 **10/10**을 코드/Mock·기존 회귀로 검증. [PR #12](https://github.com/hibi89/fable5.1_web_catcher/pull/12) main 병합 SHA `0fb2effcf1be3504d323231120cce70d23491d82`; 검증 소스 `3061db1b8fc7706a715975b4fe7e077eb05e3ff9`.
- 새 파일 `scanner/llm_payload.py`, `llm_client.py`, `llm_validate.py`, `llm_report.py`, `llm_flow.py`; `scan.py` opt-in `--llm [--model]`, `--from-result`, `--llm-dry-run`. OpenAI API는 공식 SDK Responses structured JSON만 사용(도구 없음); 누락 키/모델, 401/429/5xx/timeout, refusal/incomplete/invalid reference 실패는 종료 3, 기존 결과 불변.
- payload strict allowlist, host alias·경로 식별자·값 없는 구조, evidence 우선/중복제거/상한; 수정된 JSON 스키마 로컬 검증, 기존 confidence 소싱, 7개 한국어 구획 로컬 렌더. raw result/HTML/JS/session/쿠키 값/개인정보 후보 외부 미전송을 목표로 하나 익명화 완벽 보장하지 않음; 사용자 dry-run 검수 권장.
- `rules/fingerprints.json` 총 **35기술 50규칙 신호** (기존 16/30 보존, 신규20 고유 패턴); 각 규칙 ID/weight/note/검증 memo + synthetic 양성·음성 fixture.
- **Windows 91/91 PASS** run `39142853498`; **Ubuntu headed Chromium 23/23 PASS**, 공개사이트 smoke 4/4 run `39142853476`. Step 4의 API 응답/실패 테스트는 **mock**, *실제 OpenAI 유료 API 호출 전혀 없음(0건)*. 키·실모델이 제공되지 않아 라이브 smoke와 prompt-injection 모델 내성은 미검증.
- 실행 시작: `python -m pip install -r requirements.txt` → `python scan.py --from-result ./out/demo/result.json --llm-dry-run` → preview 파일 검토 → 환경변수 `OPENAI_API_KEY`, `OPENAI_MODEL` 설정 → 선택적으로 `--from-result ... --llm --model ...`. CLI 비용·에러·한계 README 참고. 기존 `result.json`/`report.md` 불변, 별도 `llm_report.json`/`llm_report.md`.
- 문서 `docs/STEP4_MOCK_ACCEPTANCE_2026-10-19.md`. 원본 Step 1~3 자동 인수 통과 유지. 미완: (a) 실제 OpenAI API opt-in smoke, (b) 실제 사용자 Windows Step3 수동 필터 조작→차트/API 근거, (c) 배포/서버 보안은 범위 밖. 다음 `ㄱ`은 새 검증/보완 단위로만 처리, 기존 테스트 반복 생산 금지.
- 진행률: **전달된 Step 1~4의 자동/Mock 완료 기준 4/4 단계 구현**, 단 실제 API 성공·사용자 Windows 수동 실증은 미확인. 최종 상용제품 완성 %는 별도 범위 확정 전 계산 금지.

---

# 2026-10-19 KST — Fable 5.1 Web Catcher Step 3 대용량 JSON 부분 구조 인수

- **PR #10 https://github.com/hibi89/fable5.1_web_catcher/pull/10 병합 완료**, source `df887d02c6602b3214c3aea9b8a6061e51611da6`, merge `07fb7ed6fd0b7fb095eb1710e4432557d5cffae5`.
- 새 `scanner/json_prefix_hints.py`: 32KiB 제한 JSON prefix의 처음 완성된 객체를 찾아 기존 민감키 마스킹 및 `_json_shape`로 필드/타입만 요약. 새 `json_prefix_structure` (completeness `partial_prefix_only`)는 완전한 API `json_structure`와 **분리**; API→차트 매핑 판정에 투입하지 않음.
- `scanner/cdp_decoded_size.py` 단일 CDP 세션을 이용, 요청 시작 시 `Network.streamResourceContent` 활성화 후 최초 32KiB까지만 임시 샘플, 20 스트림/10 힌트 상한. `scanner/record_scan.py`에서 승인 exact-origin/main-frame, HTTP200 JSON & 기존 `decoded_too_large`에만 별도 샘플 부착. `scanner/report.py`에 '부분 샘플/전체 아님' 표시. 불확실/중복/미완성 이벤트는 힌트 없음. 인증값/본문/화면 원문 영구 저장 없음.
- **Windows fixture 70/70 PASS** [39140626259](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39140626259), **실제 headed Chromium 23/23 PASS** 및 공개 홈페이지 4/4 [39140626261](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39140626261). 초기 두 CDP 세션 충돌은 실제 회귀로 확인, 수정해 최종 PASS.
- **실사이트 read-only 12.395초** [39140868626](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39140868626): HTTP200/승인 API1·차트3, 128KiB 초과 본문은 읽지 않은 채 **`partial_prefix_hint_count=1`** (기존0). `json_shape_count=0`, 클릭0, `chart_api_candidate_count=0`. 부분 힌트 원본·키 목록은 GitHub 로그에 출력 안 함. 실사이트 전용 [PR #11](https://github.com/hibi89/fable5.1_web_catcher/pull/11) 및 실험 [PR #9](https://github.com/hibi89/fable5.1_web_catcher/pull/9) closed unmerged.
- 문서 `docs/STEP3_PARTIAL_LARGE_JSON_PREFIX_2026-10-19.md`. **원래 Step 1/2/3 CLI 자동 인수 기준은 완료**, 사용자가 제공한 최종 전체 제품 스코프(후속 단계/배포 범위)는 확정된 문서가 없어 *전체 %를 임의 산정하지 않는다*. 그러나 실제 사이트 부분 구조 0→1은 유의미한 진도 상승.
- 후속 범위: 실제 사용자 Windows 최신 main 수동 필터 조작 후 `change_evidence`/차트↔API 후보 검사, iframe 미지원·서버 SSRF 격리·브라우저 내부 압축 메모리 하드제한 없음 유지. 추가 로그인/외부 endpoint 자동 탐색 금지.

---

# 2026-10-19 00:14 KST — p3 무길이 압축 JSON CDP decoded-length 단계 완료 및 실사이트 검증

- **PR #7** https://github.com/hibi89/fable5.1_web_catcher/pull/7 main merge `4fe091451e3278aab8477abb1913144c9b3d00e5`, tested source `c9e735b0d8ac79fc762f533577e582d8c780c04c`.
- Windows fixture **67/67 PASS** run `39139094290`, 실제 Ubuntu Chromium **22/22 PASS**, 보조 공개 smoke **4/4 PASS** run `39139094270`. 본문값/세션 수집·새 URL probing 없음, 승인 main-frame origin과 인증 경로 제외 유지.
- 새 `scanner/cdp_decoded_size.py`가 CDP Network.dataReceived `dataLength`만 합산(128KiB까지 포화)해 Content-Length 없는 gzip/br의 디코딩 크기 상한 확인. `scanner/record_scan.py` 승인 `ScopedNetworkCollector`만 적용, `scanner/network.py` 측에서 body 실제 크기 동일성·128KiB 재검사. 측정 실패/중복 URL+메서드/이벤트 누락/큰 응답은 본문 미수집. Step 1/2 원본 구현·정책 변경 없음.
- 실험 [39138406625](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39138406625): gzip 171B→1171B 분석; 461B→400015B 거절. 실패한 `streamResourceContent` 실험은 [PR #6](https://github.com/hibi89/fable5.1_web_catcher/pull/6) closed unmerged.
- 최신 사용자 공개 대시보드 read-only 검증 [39139325141](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39139325141) SUCCESS: HTTP200, 12.283초, 3 charts/API1. API JSON 분석 결과 `compressed_size_unknown`에서 **`decoded_too_large`로 개선**, 여전히 `json_structure=null`/차트↔API 0. 데이터 디코딩 후 크기가 128KiB를 초과. 필터 클릭을 안 했으므로 실제 변경/계보 미검증. 실사이트 시험용 PR #8 closed unmerged.
- 완전한 브라우저 내부 decompression 메모리 하드 한도 아니므로 압축 폭탄에 대한 절대 메모리 보장 불가. 사용자 동의 없는 cap 상향 금지, SSRF 격리 없는 서버 배포 금지. 원본 스크린샷/세션/응답 본문/GitHub 실사이트 자료 업로드 없음.
- 근거: `docs/STEP3_COMPRESSED_JSON_DECODED_BOUND_2026-10-18.md`. 다음 `ㄱ`: **새 단위**로 대용량 승인 JSON에서 안전하게 필드/시계열 구조를 얻는 다른 방법 설계 또는 사용자 Windows Record 최종 시험. 이미 검증된 수집/압축 상태 로직 반복 개발 금지.

---

# 2026-10-18 23:46 KST — p3 실사이트 읽기 전용 Record 확인 인수

- 이전 마지막 `ㄱ`: PR #4 병합 이후 사용자가 실사이트 검증을 요청. 기존 소스를 재개발하지 않고 임시 브랜치 `probe/p3-live-readonly-20261018`에서 실제 웹사이트 1회 관찰.
- [Actions 39137433372](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39137433372) SUCCESS: Ubuntu Playwright headed Chromium/Xvfb, HTTP 200, 12.397초, 문서 1, SVG 2/CSS bar 1, API 1건, stop_signal, fatal false.
- **API 분석 `compressed_size_unknown` 1건, JSON shape 0건**: 압축 JSON인데 Content-Length가 없으므로 보수적 보안 차단. `--allow-origin`은 이전 사용자가 승인한 `https://practice02.61-107-199-22.sslip.io` 정확한 origin 사용. 압축 해제 메모리의 하드 상한 보장 없는 상태에서 무리하게 우회하지 말 것.
- 수동 상호작용 0/changed_chart 0/chart-api 후보 0. **읽기 전용 검증**이므로 PR #4의 실제 데이터 변화 검출 성공/실패를 판정하지 않는다. 사용자 Windows 최신 코드 검증 전.
- 민감값/로그인/원본 응답/화면 캡처/결과 JSON 파일 업로드 없음, GitHub에 집계만 남김. 원격 테스트 전용 [PR #5](https://github.com/hibi89/fable5.1_web_catcher/pull/5)는 **closed unmerged**, main에 테스트용 URL/워크플로 미반영.
- 자세한 근거는 `docs/STEP3_LIVE_READONLY_2026-10-18.md`. 다음 `ㄱ`에서는 **한 단위**만 진행: 안전한 압축 미확인 길이 응답 분석 타당성·개선 또는 사용자 최종 Windows Record 확인. generic CSS/SVG의 API 계보를 무근거로 확정하지 않는다.
- 기존 PR #3/#4 기능 main 병합 및 CI Windows 65/65, Chromium 21/21, 공개 홈페이지 4/4 PASS 상태 유지.

---

# 2026-10-18 23:37 KST — p3 PR #4 병합 후 인수인계

- **PR #4 main 병합 완료**: `67e72529be4d5e6a190d7c63fc0c840878301965`, 검증 기능 SHA `30a59be00d473a1040d67aa0d3166f41b70f5e70`. GitHub 저장소 Public 전환 후 Actions가 정상 동작해 CI 차단이 해소됨.
- 최신 테스트 GitHub Windows [39136596883](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39136596883) **65/65 PASS**, Ubuntu 실제 headed Chromium [39136596876](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39136596876) **21/21 PASS**, 같은 workflow 선택 공개 사이트 **4/4 PASS**. 최초 Chromium fixture의 optional `chart_candidates` 필드 검증 오류는 테스트 수정 후 재시험 통과.
- `scanner/runtime_detect.py`: SVG geometry/childList, CSS bar 그룹 변형 시간과 `change_evidence` 세 분류를 읽기 전용 관찰. hover CSS class-only는 제외. `scanner/record_scan.py`: 동일 구조 selector에 대한 이전 시각 보존. `scanner/report.py`: 변화 증거를 분리 표기. `tests/test_record.py`, `tests/browser_record_check.py`: 원문 비저장/중복 분기/실제 Chromium 테스트.
- **과거 'PR #4 open/CI 차단' 구간은 보존 이력이며 현 최종 상태 아님**. 상세: `docs/STEP3_GENERIC_CHART_GEOMETRY_PENDING_2026-10-18.md`의 '후속 검증 확정' 섹션.
- **후속 미확인 사항**: Windows 사용자 실사이트에서 새 기능의 `change_evidence` 발생 여부, 헤더 없는 외부 API의 JSON 구조 수집 여부, 데이터 JSON↔실제 CSS/SVG 차트 계보는 미검증. iframe main-frame 한정, browser_closed 스냅샷 경고 가능, 절대 브라우저 메모리 상한 없는 JSON 바디, SSRF 격리 없는 공개 서버 배포 금지 유지.
- 다음 `ㄱ`은 **새 작업 단위**로만 처리. 필요하면 사용자 실사이트 1회 Record 검수 또는 generic chart 연결 근거를 신중하게 보강. 기존 CI 재실행/중복 구현은 불필요.

---

# p3 Step 3 SVG/CSS 변경 증거 강화 — PR #4 CI 보류 인수 (2026-10-18 22:44 KST)

- 사용자의 `r`을 한글 `ㄱ`으로 해석하여 1단위 개발 진행. PR #4 https://github.com/hibi89/fable5.1_web_catcher/pull/4, 브랜치 `fix/step3-generic-chart-change-evidence-20261018`. **main 미병합**.
- `scanner/runtime_detect.py`에서 실제 SVG geometry attr/내부 구조 변경과 CSS bar 그룹 퍼센트 차이를 관찰해 원문 없는 `change_evidence` 및 UTC ms만 생성. `scanner/record_scan.py`의 동일 chart key 이전 변화 시각 보존, `scanner/report.py` 변화 근거 표시. 테스트 `tests/test_record.py`, `tests/browser_record_check.py`.
- V8 순수 JS 문법 검사 성공. 모의 DOM CSS baseline/동일/변화, SVG class-only/geometry 변경 관찰 성공. 실제 전체 fixture 미검증.
- PR #4 workflow runs **39132765417 Windows**, **39132765458 Ubuntu Chromium**은 실행 단계 0개로 실패, 로그 다운로드 BlobNotFound. Windows 재실행도 단계 0개 실패. GitHub 실행 환경/러너 제약 가능성; 정확한 원인 확인 전 'CI PASS' 주장 금지, PR 병합 금지. 동일 방식 무한 재시도 하지 말 것.
- branch 상세 문서 `docs/STEP3_GENERIC_CHART_GEOMETRY_PENDING_2026-10-18.md`. 다음 할 일: CI 실패 원인 확인, GitHub runner 회복 또는 별도 실제 Python/Chromium 환경 확보 후 전체 회귀 검증. 통과하면 그때만 병합 및 BOOK 완료 표기.
- main의 이전 PR #3 완료: Windows 63/63, headed Chromium 20/20, 공개 smoke 4/4 PASS. 사용자 실사이트 신규 JSON 성공과 SVG/CSS↔API 연결은 여전히 미검증. iframe 미지원/SSR F 보안 제한 보존.

---

# Step 3 후속 1단위 완료 — Content-Length 없는 외부 API JSON (2026-10-18 22:30 KST)

## 새 구현/검증
- PR #3 https://github.com/hibi89/fable5.1_web_catcher/pull/3 main 병합 SHA `f7b9bb9c09bc69cd305519b5676af31ff4b2d7ea`, 기능 테스트 SHA `dc5992391b399e29bcf6167daf455676e3c15ca7`.
- 기존 NetCollector의 `size_unknown` 분기에서 Step 3 Record만 `allow_unknown_length=True`로 허용해 Playwright 요청 완료 이후 실제 전송 바이트 측정. 128KiB 초과, 크기 측정 실패, 미확인 길이 압축 데이터는 분석 거절. 응답 본문을 일시적으로만 읽고 길이 재검사 후 타입 구조만 저장. 구조/값/접근 범위/인증 보호 규칙 유지. Step 2는 opt-in False로 회귀 방지.
- GitHub Windows Python 3.11 `39131631123`: 63/63 PASS. 실제 Ubuntu headed Chromium/Xvfb `39131631050`: 20/20 PASS; 선택 공개 URL smoke 4/4 PASS. 회귀/인가/압축/실제 HTTP chunked 테스트 포함.
- 문서 근거 `docs/STEP3_HEADERLESS_JSON_BOUND_2026-10-18.md`. 사용자 PC에서 신규 기능 재시험 전. **사용자 기존 result(3).json**으로 확인한 33.312초·35 클릭/중복 0·차트 3/ID 중복 0 결과는 지난 코드 기준이며 그대로 기록 보존.
- 한계: 브라우저의 실제 디코딩 메모리 사용을 128KiB로 하드 제한하는 구현은 아님. size_unknown이 현장에선 계속 유지될 수 있으며, 차트↔API 매핑 0건 문제와 iframe, 종료 시 TargetClosedError 경고는 별도 작업.
- 다음 `ㄱ`: 별도 한 단위만 진행(후보: generic SVG/CSS의 상태 변경 증거 강화). 사용자 Windows 개입 요구 없이 fixture·GitHub CI 중심 구현을 우선. 공개 서비스 배포 금지.

---

# Step 3 Windows 현장 재시험 검증 완료 (2026-10-18 22:03 KST)

- 새 사용자 제출 `result(3).json`은 33.312초 새로운 headed Record이며 `stop_reason=browser_closed`, 클릭 35건/중복 0, SPA navigation 1, 차트 후보 3개/ID 중복 0, target.final_url 보존, 승인한 API origin 2개. PR #2 기능 수정의 실제 Windows 핵심 회귀는 통과한 것으로 판정.
- API 자체는 200 JSON이지만 `response_body_analysis=size_unknown`이므로 JSON 구조 미분석. 차트는 generic SVG/CSS(갱신 시각 미확인)이어서 차트↔API 후보 0개. 보존된 API 완료 후 첫 클릭까지 1,539ms; 문서상 타이밍/자료형을 토대로 인과적 매핑을 만들 근거 없음. 마지막 Step 3 예시의 '필터 변경→API↔차트 연관 후보'는 이 사이트에서 미달성.
- 경고: iframe DOM 미지원, 요청 세부 1건 생략, 사용자 browser_closed 시 TargetClosedError 스냅샷 경고(기록/종료 성공). 신규 수정으로 해결했다고 주장하지 말 것.
- 상세 근거: `docs/STEP3_WINDOWS_REAL_SITE_VERIFICATION_2026-10-18.md` (사용자 결과 원본은 GitHub에 업로드하지 않음). 기존 Windows CI 60/60, Chromium CI 19/19, 공개 URL smoke 4/4 모두 완료 상태 유지.
- 다음 개발 범위는 기존 수집 정책 변경 동의를 전제로 한 미확인 Content-Length의 안전 제한형 JSON 구조 인식, 그리고 CSS/SVG 차트 갱신 근거 확보. 사용자가 이 재시험을 반복할 필요 없음. 아래의 이전 '실사이트 미확인'은 과거 기록.

---

# Step 3 실제 사용자 Record 후속 인수인계 (2026-10-18)

## 테스트에서 확인된 현상과 원인
사용자가 로컬 headed Record로 실제 대시보드 47.344초 조작. HTTP 200 및 4개 차트 후보, 사용자 조작 마커 228건, nav-0001~0005 반복. 같은 클릭 타임스탬프가 여러 nav에 다시 나타나 SPA fragment/history 변경을 새 document로 취급하는 결함이 의심되었고 local Chromium fixture로 재현·수정했다. 사용자 종료 방식 browser_closed는 정상이나 target.final_url unknown 문제가 있어 마지막 마스킹 URL 보존 수정. 같은 nav의 SVG/CSS 차트 후보에 같은 chart ID가 생성될 위험도 수정.

## 수정/정확도/보안
Playwright framenavigated에 포함되는 same-document SPA URL 변경은 performance.timeOrigin으로 판별하고 실제 새로운 문서만 새 navigation_id 배정. 조작 마커의 cursor/seq 중복 방지. 구조별 안정적 차트 ID 사용. 외부 n8n JSON API는 기본 허용 scope 밖이므로 메타데이터만 기록한 것이 올바른 동작이다. 권한 있는 API origin만 반복 --allow-origin으로 허용. 추가한 Chromium fixture에서 외부 응답은 허용되지 않으면 구조 null, 허용하면 값 없는 JSON 자료형만 수집됨을 검증했다. generic SVG/CSS bar의 차트↔API 연관을 근거 없이 억지 생성하지 않는다.

## SHA·테스트·남은 작업
- PR #2 병합 main 기능: b5496a61bd82d56204bdab24c984288230a95713.
- 검증 SHA: 173d42d3a33d29bf80c2dc5a137daccf0992216d.
- Windows Python 3.11 run 39128145838: 60/60 PASS. Ubuntu 실제 headed Chromium run 39128145939: 19/19 PASS, 선택 공개 페이지 4/4 PASS.
- 상세: docs/STEP3_REAL_RECORD_FEEDBACK_2026-10-18.md.
- 사용자 Windows의 수정 후 실사이트 재시험 **아직 진행 전**. API와 차트의 확정된 인과 데이터 계보는 검증 대상이 아니며, 엄격한 generic chart heuristic 때문에 매핑 후보가 여전히 0건일 수 있다.
- 다음 수행: GitHub 최신 main 코드 적용. Git clone이면 git pull, ZIP 폴더면 새 ZIP 수동 압축 해제. 권한이 있으면 --allow-origin https://practice02.61-107-199-22.sslip.io 로 외부 webhook 응답 구조 승인. Record 실행→대시보드 필터 조작→Enter→result.json/report.md의 문서/마커 중복·final_url·API 응답 처리 확인.
- 기존 원본 Step 1/2, Record 보안 원칙, 과거 이력은 아래에 보존.

---

# HANDOFF.md — Fable 5.1 Web Catcher / Step 3 CLI MVP

> 최신 인수인계(2026-10-18 KST). 아래 기존 Step 2 HANDOFF는 보존한 과거 이력이다. 최신 개발 기준은 이 Step 3 섹션 및 docs/STEP3_FINAL_ACCEPTANCE.md.

## ① 목표·용도·확정 요구·기술
권한 있는 공개·자체 사이트를 로컬 headed Chromium으로 사용자가 직접 탐색·로그인·조작하는 동안 기술·API·차트 근거를 수집한다. 사용자 원본 5 .1_step3.txt. Python 3.11+ Playwright, 기존 Step 1 static 및 Step 2 runtime 분석 유지. 자동 로그인·WAF 우회·LLM·웹 UI·영구 세션 저장은 범위 밖.

## ② 완료 기능·변경·결정 근거
--record/--max-duration(기본900초)/반복 --allow-origin 추가. --runtime과 중복 브라우저 실행 금지. input 스레드는 종료 신호만 송신하고 메인 Playwright 이벤트는 계속 처리. Enter·Ctrl+C·시간 만료·창 종료·EOF 처리. 새 비영구 context, 팝업/탭·main frame 문서 ID, origin 허용/응답 구조 구분, 클릭·변경 시각/구조 selector, 미수집 카운트, 원본 Step 2 collector 재사용. 차트 ↔ API 후보는 동일 page/navigation에서만 시계열 구조·DOM 갱신에 근거해 점수화하며 인과관계 확정이 아니다. cross-navigation 응답을 잃지 않도록 NetworkCollector에 완료 응답 점진적 JSON 구조 처리 도입. 새로운 네트워크 분석 엔진 대신 기존 구조 재사용 선택(유지보수·보안·회귀 영향 최소화).

## ③ 테스트 및 미검증
Windows Server 2022 Python 3.11 run 39126644441 → **60/60 PASS**. Ubuntu 24.04 실제 headed Chromium(Xvfb) run 39126644405 → **16/16 PASS**. 동일 Ubuntu 선택 공개 URL smoke **4/4 PASS**. 검증 소스 SHA 80f71d2b7de0f7a803872e76a616fe70f974e192, main merge SHA e28ea7f1f5a91d2f7a69160377558c6bc72e836d. 사용자 PC에서 사람의 실제 로그인·필터 변경은 미검증. 원본 Step 1 7/7·Step 2 9/9 완료 유지.

## ④ 완료·진행·대기·차단
Step 3 자동 fixture 기반 CLI MVP 완료(8/8 수용항목에 대한 자동 테스트 근거, 각 범위 docs/STEP3_FINAL_ACCEPTANCE.md). 사용자 로컬 Windows headed 실제 사이트 점검 **검증 대기**. Production 배포는 계획 및 구현 대상 아님. 사용자 원본을 모른 채 무단 기능 확장하지 않는다.

## ⑤ 오류 근거·원인·시도·재시도 주의
초기 headless와 다르게 headed Chrome 자원 정리 순서 오류 수정(Playwright stop 전 context/browser close). 종료 사유 덮어쓰기·finally 분기 들여쓰기 오류를 실브라우저 CI로 확인해 수정. 필터 후 차트는 DOM 관찰됐으나 최종 결과 누락됨 → 종료 시 스냅샷 항상 수행하도록 수정. JSON 구조가 페이지 이동 이후 보류될 수 있어 완료 응답을 이동 전에 점진적 요약하도록 수정. 마지막 실제 CI 60/16/4 성공. 이미 해소한 실패 재시도/무의미한 재배포 금지. SSRF 보호 없는 CLI를 외부 입력 URL 서버로 전환 금지.

## ⑥ 저장소·브랜치·SHA·주요 경로
비공개 hibi89/fable5.1_web_catcher main. 병합 PR #1. 코드: scan.py, scanner/record_scan.py, scanner/network.py, scanner/chart_mapping.py, scanner/report.py 및 기존 Step 2 모듈. 테스트: tests/test_record.py, tests/browser_record_check.py. 자동화: .github/workflows/runtime-python311.yml, windows-python311.yml. 기록: README.md, REQUIREMENTS.md, docs/STEP3_FINAL_ACCEPTANCE.md. 기능 테스트 소스 SHA 80f71d2b... / main 병합 SHA e28ea7f1....

## ⑦ 실행·배포·환경
배포 미적용(로컬 CLI). Vercel/Production URL 없음. 설치: python -m pip install -r requirements.txt; python -m playwright install chromium. 실행: python scan.py URL --record --max-duration 900 --out ./out/record. 기본 origin 외 필요시 --allow-origin 정확한 origin 추가. 결과 result.json/report.md. 테스트 명령: python -m pytest -q; Linux headed: xvfb-run -a python -m pytest -q tests/browser_record_check.py.

## ⑧ 원본·백업·인증·수정 금지
첨부 요구 파일 fable5.1_step1.txt, fable5.1_step2.txt, 5 .1_step3.txt 원본 우선. GitHub 기존 main 이력과 병합 PR을 원복 지점으로 사용, 강제 push 금지. 토큰·세션·cookie 값·입력값·원본 응답·HAR·storage_state·스크린샷·영상 저장 금지. 로그인은 사용자가 소유·권한 있는 사이트에서 직접만 수행. Playwright 비영구 context는 종료 시 파기.

## ⑨ 다음 작업·절차·완료 기준·승인
1순위: 사용자 Windows 로컬 git pull 후 --record 실제 사이트 로그인→필터 변경→Enter→result.json/report.md에서 해당 API와 차트 **연관 후보**·마스킹 확인(기능 검증 마지막 항목). 실제 데이터 연결 인과성은 결과만으로 확정할 수 없다. 필요 시 데이터/인증 처리 범위 확대, iframe 지원, 공개 서비스·배포는 별도 보안 설계와 사전 승인 필수.

## ⑩ 갱신 일시·검증 범위·문서 기준
2026-10-18 21:20 KST 부근. 기능 SHA 80f71d2b...에서 Windows/Ubuntu CI 직접 확인, main 병합 SHA e28ea7f1... 확인. 이후 HANDOFF/STATUS/BOOK 문서 커밋 HEAD는 따로 재조회하고 갱신한다. 사용자 로컬/임의 상용 사이트 완전 탐지율은 미검증.

---

# Step 2 HANDOFF — 보존 이력 (2026-10-18)

## ① 목표·용도·확정 요구·기술
공개 URL의 근거 기반 기술 스캔 CLI. Step 1 = requests/BeautifulSoup 정적 분석, Step 2 = Python 3.11+ Playwright Chromium 런타임 관찰. 사용자 원본 요구 fable5.1_step1.txt 및 fable5.1_step2.txt. 비공개 GitHub `hibi89/fable5.1_web_catcher` main. **Step 1 완료 7/7; Step 2 완료 기준 9/9 PASS (공개·무인증 CLI MVP 범위).**

## ② 완료 기능·변경·결정 근거
- 기존 Step 1 CLI 그대로 보존. Step 2 --runtime/--headed/--wait, 격리 컨텍스트·DOMContentLoaded·제한 스크롤·부분 실패 결과 및 종료 자원 정리.
- XHR/fetch 실제 메타데이터, 제한된 JSON 자료형 구조, GraphQL 후보, WS/SSE 연결의 값 없는 정보.
- 런타임 기술 전역 및 MutationObserver SVG/canvas 차트 후보, 실제 라이브러리/DOM 마커와 일반 후보 구분.
- 시차·시계열 JSON·DOM 마커를 조합한 보수적 chart↔API **연관 후보**, 경합 요청은 보류; HTML 내장 데이터/반복 검증 부재 한계 표시.
- 브라우저가 이미 로드한 같은 origin JS 문자열만 수동 검사, 최대 **10개 JS 파일 / 파일당 128KiB**. 새 경로 요청 없이 미검증 API 경로만 기록. `source_script`·`discovered_by=bundle_string` 포함.
- 데이터 모델: `api.endpoints` 실제 요청, `api.connections` 실제 WS/SSE, `api.candidates` JS 문자열 미검증 후보, `api.chart_candidates` 차트 연관 후보 및 `charts[].data_sources` ID 참조. 기존 정적 결과의 3개 api 키는 불변.
- 대안 선택: URL/probing·CDP 원시 추적보다 Playwright 사전 리스너와 완료된 응답 재사용 방식이 비용·보안·유지보수 우위. 추가 인증·사이트 조작·LLM 호출 없음.

추가 실사이트 개선(2026-10-18): 사용자 제공 공개 대시보드 URL의 #v-dash가 Chromium 탐색에서 손실되는 것을 발견해 브라우저 내 fragment 유지(결과 비저장)로 수정. generic SVG를 연결 DOM/100×70px 이상/도형 2개 이상일 때만 후보로 유지해 작은 아이콘을 억제. CSS의 서로 다른 퍼센트 높이/너비를 가진 반복 bar 그룹(4개 이상)을 css_bar_pattern_candidate(library unknown/confidence 0.5)로 추가. 실사이트 실제 실행: HTTP 200, XHR/fetch 2, 기존 차트 후보 14~15개에서 3개(큰 SVG 2 + CSS 막대 그룹 1), 에러 0. chart↔API 연결은 근거 부족으로 0. docs/DASHBOARD_LIVE_ACCURACY_2026-10-18.md에 증거 정리.

## ③ 테스트 명령·실제 성공/실패·미검증
- Windows 2022 Python 3.11: `python -m pytest -q` → **55/55 PASS**, run `39120274152`.
- Ubuntu 24.04 실제 Playwright Chromium: `python -m pytest -q tests/browser_runtime_check.py tests/browser_mapping_check.py tests/browser_bundle_check.py tests/browser_final_check.py` → **11/11 PASS**, run `39120274247`.
- 같은 Ubuntu 러너 공개 홈페이지 smoke: `python -m pytest -q -s tests/public_runtime_smoke.py` → **4/4 PASS**, example.com/python.org 각각 정적·런타임에서 HTTP 200/exit 0·결과 구조 검사.
- 최종 검증 소스 SHA: `e743e8c2b208940e66e03cfd6fc799031d7cc337`. 문서 HEAD는 검증 후 추가 변경으로 별도 재조회. 완료 기준 9개 및 한계 `docs/STEP2_FINAL_ACCEPTANCE.md`.
- 실제 상용 차트 라이브러리 통합은 일부 명시적 stub, 모든 실사이트 정확도·사용자의 Windows headed는 **미검증**.

실사이트 확장 검증: Windows Python3.11 57/57 PASS (run 39123343492), Ubuntu Chromium 12/12 PASS (run 39123322129), 대상 사이트 일회성 read-only 진단 PASS (run 39123343463). 검증 기능 HEAD b7c707386034a14c44820709b4a13388dfcf7e7e. 후속 커밋은 문서 변경만. 실제 전체 대시보드의 모든 시각화 탐지율과 데이터 lineage는 미검증.

## ④ 완료·진행·대기·차단·중단점
원본 Step 1 완료 및 Step 2 9/9 완료. **필수 남은 구현 없음.** 사용자 추가 요청이 없는 한 다음 단위 자동 개발·배포하지 않음. 실사이트 범위 확장, 실제 차트/라이브러리 정확도 검증, 배포는 별도 요청·승인 필요.

## ⑤ 오류 근거·시도·재시도 금지·대안
- 최종 보안 검수에서 원본 상한 10개와 과거 코드의 12개 불일치, 번들 후보가 api.bundle_candidates에 있었던 불일치, 차트 후보의 reasons 누락, HTML 내장 데이터 가능성 보고 누락을 확인. 한정된 소스/테스트 수정 및 최종 55/11/4 PASS로 검증. 이전의 중간 실패 CI를 최종 성공으로 오인하지 말 것.
- 한 번의 대형 GitHub 호출은 도구 호출 수 상한으로 중단됨. 소규모 변경 그룹별 트리 커밋으로 성공. 같은 대형 호출 반복 금지.
- 이전 컨테이너 Chromium localhost 접근은 ERR_BLOCKED_BY_ADMINISTRATOR 환경 정책 차단; 우회/반복 금지, GitHub Ubuntu Chromium fixture로 검증.
- Playwright decoded body 메모리 절대 상한 불가, 서버용 SSRF 방어 미구현. 이 CLI를 무신뢰 입력을 받는 외부 서비스로 공개하지 않는다.

## ⑥ 저장소·브랜치·SHA·주요 파일
`hibi89/fable5.1_web_catcher`, `main` (private). 최종 테스트 소스 SHA `e743e8c2b208940e66e03cfd6fc799031d7cc337`. 직전 단위 6 문서 HEAD `1184a4fc6a18ba377123406f30cdae535d686b9d`로 이력 확인 가능. `scan.py`, `scanner/runtime_scan.py`, `scanner/network.py`, `scanner/connections.py`, `scanner/runtime_detect.py`, `scanner/chart_mapping.py`, `scanner/bundle_scan.py`, `scanner/report.py`, `tests/browser_final_check.py`, `tests/public_runtime_smoke.py`, `docs/STEP2_FINAL_ACCEPTANCE.md`.

## ⑦ Production URL·Vercel·실행 명령·환경
배포 미적용(로컬 CLI), Production/Vercel URL 없음. 설치: `python -m pip install -r requirements.txt` 및 `python -m playwright install chromium`. 정적: `python scan.py https://example.com --out ./out/static`. 런타임: `python scan.py https://example.com --runtime --wait 10 --out ./out/runtime`; `--headed`는 표시 환경에서 선택. 결과는 지정 폴더의 result.json 및 report.md. 테스트 명령 ③ 참조.

## ⑧ 원본·백업·인증 관리·수정 금지
사용자 첨부 fable5.1_step1.txt/fable5.1_step2.txt가 최종 요구 원본. GitHub main이 코드 기준, git history로 복구 가능, 강제 push 금지. tests/test_static.py.bak 보존. API token, URL 인증 쿼리, cookie, raw response/JS, HAR, storage state, 비밀 로그 저장 금지. 로그인·WAF 우회·임의 경로 probing 금지.

## ⑨ 다음 작업 우선순위·완료 기준·승인
**Step 2는 원본 기준 9/9 완료 판정.** 첫 실사이트 정확도 개선까지 별도 확인했지만 모든 차트 형식의 완전한 탐지나 사용자 Windows 최신 개선 코드 설치는 입증하지 않았음. 향후 더 높은 실제 사이트 정확도/사용자 로컬headed/서버 배포는 새 범위로 취급하고 사용자 지시를 받은 뒤 시작. 배포 시 보안 격리·SSRF·리소스 상한을 새로 설계해야 한다. 지금 단계에서 추가 개발·배포 필수 작업 없음.

## ⑩ 갱신 일시·검증 범위·문서 기준 커밋
2026-10-18 KST. 최종 CI run 39120274152 (Windows 55 PASS), 39120274247 (Chromium 11 + 공개 사이트 4 PASS), 소스 SHA e743e8c2b208940e66e03cfd6fc799031d7cc337. 문서 커밋 HEAD 및 중앙 BOOK.md 갱신은 최종 재조회 확인 후 상태 보고. 실제 사이트 전체 탐지 정확도와 사용자 개인 PC는 미검증.
