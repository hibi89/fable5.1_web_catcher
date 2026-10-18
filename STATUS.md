# 2026-10-19 KST — p3 Step 5 구현 및 자동 수용 기준 완료

- **[PR #16](https://github.com/hibi89/fable5.1_web_catcher/pull/16) main 병합** `7de7e26faec46120bbdfb509892ca267cea514c4`, tested source `6f32544299ea5181d4a90321f32e7706857781eb`. Step 5 원본 10/10 자동 인수 기준 PASS.
- 신규 `scanner/batch.py`: UTF-8 URL 목록 순차 실행(기본 50개/대기 2초), 새로운 타깃마다 `scan()` 재사용·브라우저 격리, 실패 후 계속, 429 이후 동일 origin skip, Ctrl+C 완료분 보존/현재 interrupted/나머지 pending, 안전한 실행별 origin별 별칭·원자적 manifest/summary/Markdown 및 개별 결과. 자동 재개·LLM 호출·병렬 실행 없음.
- 신규 `scanner/compare.py`: 저장된 두 `result.json`의 기술/버전/점수/evidence/API/JSON 구조/차트 집합 비교. 별도 인터넷·API 호출 0. 서로 다른 원래 origin 자동 연결 금지, 미관찰을 실제 삭제라고 주장하지 않음. 새 `scanner/contracts.py`: 관찰 기반 JSON Schema Draft 2020-12, null/union/빈 배열/부분 구조 unknown, status/mime variant. 서버 required/actual breaking change 확정하지 않음.
- `scan.py`에 `--batch`, `--compare`, `--export-contracts`, `--delay`, `--max-urls` 추가, 기존 Step1~4 CLI는 그대로 동작. `README.md`에 배치·비교·계약 명령, 종료 정책·보안·한계 설명.
- **최종 Windows 123/123 PASS** [run 39148097390](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39148097390). **기존 headed Chromium 23/23 PASS + 공개 smoke 4/4 PASS** [run 39148097419](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39148097419).
- Step5 **3 URL localhost fixture 실제 스캔 → 그중 두 저장 결과 로컬 비교 → 한 결과 contracts.md 생성** 연속 통합 수용 테스트 성공. 추가 익명화된 배치 API 표본으로 실제 Draft2020-12 schema 생성/검증 성공. 이 3 URL은 실제 외부 사이트가 아니라 **localhost fixture**임을 명시.
- 사용자 제공 지침서 Step1~5 구현·자동/Mock 기준 **5/5 단계 완료**로 유의미하게 상승. 단 Step3 사용자 Windows 실사이트 필터 조작, Step4 실제 OpenAI 유료 API smoke, Step5 복수 실제 외부 사이트 runtime 배치는 여전히 미검증. **상용 제품 모든 환경에서 100%라는 주장은 금지**.
- 상세 `docs/STEP5_FINAL_ACCEPTANCE_2026-10-19.md`. 다음 단계는 추가 개발 지침 또는 사용자 Windows 최소 1회 최종 수용 검사 선택. 기존 보안·origin 상한·SSRF 경고 유지.

---

# 2026-10-19 KST — p3 Step 3 CDP 미매칭 진단 코드 완료

- 임시 localhost Chromium 진단 [PR #14](https://github.com/hibi89/fable5.1_web_catcher/pull/14) **closed/unmerged**. 세 번의 8건 샘플에서 판정 시점 `no_cdp_match` 4/8, 5/8, 3/8. 합계 12/24 미매칭이며 500ms 추가 대기로 일관되게 회복되지 않음. **요청 매칭 누락 재현**은 확인했으나 frame/filter/이벤트 배달 등 정확한 원인은 미확정. 24건을 일반 사이트 실패율로 일반화 금지.
- **[PR #15](https://github.com/hibi89/fable5.1_web_catcher/pull/15) main 병합** `f6cf9577941fff829cab0b827b5b95fd7e8eac88`, tested `385851177b20339c167957d2579bb2a18694b804`: `compressed_decoded_unavailable` 응답에만 **값 없는 CDP 진단 enum `cdp_decoded_diagnostic`**을 추가. 예: `request_unmatched`, `loading_incomplete`, `no_data_events`. 기존 응답 원문 미수집, origin 제한, decoded cap 128KiB 및 성공 분석 판정 불변.
- 최종 Windows **99/99 PASS** [39145907566](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39145907566), 실제 Chromium **23/23 PASS + 공개 smoke 4/4 PASS** [39145907594](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39145907594). 초기 Chromium 테스트가 22/23 실패한 것은 기존 대용량 gzip 부분 힌트 단위가 CDP 미매칭으로 안전 거부되었기 때문; 안전 거부와 원문 null/진단을 별도 합법 결과로 구별하도록 변경 후 재시험 통과.
- **성공률 개선이 아니라 실패 이유 가시화** 완료. 실제 사용자 Windows 필터→차트/API 연결과 실제 OpenAI 유료 API는 여전히 미검증. Step1~4 자동/Mock 기준 4/4 유지. 상용제품 총진도 % 미확정.
- 상세 `docs/STEP3_CDP_MISMATCH_DIAGNOSTICS_2026-10-19.md`. 다음에는 **CDP 요청 추적 개선안의 근거 기반 비교** 또는 사용자 Windows 1회 현장 실증, 동일 임시 실험 반복 금지.

---

# 2026-10-19 KST — p3 Step 4 공식 SDK HTTP 계약 오프라인 검증 (PR #13)

- **[PR #13](https://github.com/hibi89/fable5.1_web_catcher/pull/13) main 병합** SHA `1339baf0a76e291a8f7fea2698b053cf9351c1a2`, 검증 기능 SHA `42f481c821189e54c3b66b00dff17d767351b376`.
- 신규 `tests/test_llm_sdk_transport.py`는 실제 설치된 공식 OpenAI Python SDK `OpenAI(...).responses.create`를 **`httpx2.MockTransport`**로 차단하여 외부 네트워크/실제 모델 API 없이 HTTP 요청 JSON 직렬화·`store=false`·strict schema·도구 없음·정제 payload·응답 파싱/usage/401·429·500·거절·잘림을 점검하는 7개 테스트 추가.
- 최종 [Windows run 39144159568](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39144159568) **98/98 PASS**, [Ubuntu headed Chromium run 39144159553](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39144159553) **23/23 PASS** 및 공개 사이트 smoke **4/4 PASS**.
- 초기 Chromium [39143751592](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39143751592) 22/23 실패. **1회 재실행 역시 22/23 실패**, 그러나 다른 gzip 응답에서 CDP decoded-length 데이터 미완성으로 `compressed_decoded_unavailable` (본문 미수집 안전 거부). 코드의 명시적 fail-closed 정책이므로 이 가능성을 테스트에 반영. 기능 코드 변경 없음. **CDP 수집 성공률 향상을 달성한 것은 아님**; 원인 진단은 추후 과제.
- **유료 OpenAI API 0회**, 진짜 모델의 응답 품질/주입 내성/비용 미검증. 이전 Step 1~4 자동·Mock 인수 기준 4/4 단계 유지, 상용 제품 총 % 별도 스코프 미정으로 산출하지 않음.
- 상세 `docs/STEP4_OFFICIAL_SDK_OFFLINE_2026-10-19.md`; 다음 후보: CDP 관찰 빈도 진단 또는 사용자 Windows 수동 필터 실조작 1회, 실제 유료 API 검증은 명시적 사용자 키/모델과 승인 필요.

---

# 2026-10-19 KST — Step 4 선택적 OpenAI 보고서 Mock 인수 완료

- **PR #12 main 병합 성공**: `0fb2effcf1be3504d323231120cce70d23491d82` (테스트 기능 SHA `3061db1b8fc7706a715975b4fe7e077eb05e3ff9`).
- 사용자 Step 4 원본 지침서 기준 **10/10 항목 Mock·로컬 자동검증 충족**. 실제 OpenAI 유료 API **미호출(0회)**, 프롬프트 주입 내성/모델 품질의 라이브 검증은 아직 미수행.
- 명시적 `--llm`만 외부 API 호출, `--from-result ... --llm-dry-run`은 전송 예정 정제 payload 확인 및 외부 LLM 네트워크 호출 0회. `OPENAI_API_KEY`/모델 없으면 안내만 하고 기존 스캔 보존. `--runtime`/`--record`/정적 CLI 호환.
- official Python SDK Responses API `json_schema` structured output을 로컬 엄격 검증, confidence는 기존 규칙 엔진, backend finding/evidence 및 차트↔API 원래 후보 ID만 허용, 7개 한국어 섹션 로컬 렌더링. 원본 결과 덮어쓰기 금지.
- 대외 데이터: 내부 호스트 `origin_#` 별칭, 민감 경로/JSON key 일반화, 전체 result/raw body/쿠키/인증값/폼·원문 제외, 근거 우선 정렬·중복 제거·상한/생략 사유 기록. 완벽한 개인정보 익명화 보장 없음 → 사용 전 dry-run 검토 권장.
- 기존 **16개 기술/30신호 → 35개 기술/총 50개 유효 구분 규칙 신호** (고유 ID/출처/한계/검증 memo 및 **50개 synthetic 양성·음성 fixture**). 실제 사이트별 탐지율을 입증하는 수치는 아님.
- **최종 GitHub Actions Windows 91/91 PASS** [39142853498](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39142853498), **실제 Chromium 23/23 PASS**, 선택 공개사이트 **4/4 PASS** [39142853476](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39142853476). Step 4 API 실패 처리 등은 *mock SDK/fixture* 테스트임.
- 상세 근거 `docs/STEP4_MOCK_ACCEPTANCE_2026-10-19.md`. 남은 검증: 본인 API 키/실제 모델 선택 후 명시적 opt-in smoke(비용 발생 가능) 및 사용자 Windows Step 3 수동 필터→차트 연관 근거 1회.

---

# 2026-10-19 KST — p3 대용량 JSON 부분 필드 힌트 기능 완료 (PR #10)

- **PR #10 main 병합** `07fb7ed6fd0b7fb095eb1710e4432557d5cffae5` (검증 브랜치 SHA `df887d02c6602b3214c3aea9b8a6061e51611da6`). 기존 CDP의 decoded-length와 같은 세션에서 요청 시작 시 스트리밍을 켜서 승인 JSON의 처음 **32KiB까지만** 일시 관찰하고, 실제 전체 디코딩 크기가 **128KiB 초과**인 응답에서 첫 번째 완성된 객체의 **값 없는 필드·자료형 구조**를 별도 `json_prefix_structure`로 보존.
- `completeness=partial_prefix_only` 및 보고서 '전체 JSON 아님/연관 API 판단 근거 아님' 필수. 원래 `json_structure=null`, 전체 본문 읽기 금지와 상한 유지. 허용 main frame/origin, 인증 경로 제외, 최대20 스트림/32KiB 표본/10개 힌트, CDP 이벤트 자체 브라우저 메모리 제한 아님.
- 첫 구현의 다중 CDP 세션 충돌 회귀가 실제 Chromium에서 확인되어 **단일 CDP 세션으로 수정한 최종 테스트**를 사용함. Windows [39140626259](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39140626259) **70/70 PASS**. 실제 Chromium [39140626261](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39140626261) **23/23 PASS**, 보조 공개사이트 **4/4 PASS**.
- **실사이트 유의미한 진전**: 사용자가 제공한 대시보드에서 [39140868626](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39140868626) HTTP200/12.395초/승인 API1·차트3·클릭0. API의 128KiB 초과 상태 `decoded_too_large`는 유지하면서 **부분 구조 검출 0 → 1건** 성공. 필드 이름/원문/스크린샷 로그 미출력. 검증 전용 [PR #11](https://github.com/hibi89/fable5.1_web_catcher/pull/11) closed/unmerged; 연구 [PR #9](https://github.com/hibi89/fable5.1_web_catcher/pull/9) closed/unmerged.
- **실제 필터 변경→차트 변화→API 계보**는 미확인, 인과 추정 금지. 전체 개발 진행률의 분모가 되는 후속 스텝/최종 출시 기능 목록이 확정되어 있지 않아 임의 % 대신 **부분 구조 확보 0→1**을 정량 진전 지표로 사용.
- 상세: `docs/STEP3_PARTIAL_LARGE_JSON_PREFIX_2026-10-19.md`. 다음은 사용자 최신 Windows 실조작 1회로 변형 증거 확인 또는 별도 차트 데이터 연관 근거의 엄격한 보완.

---

# 2026-10-19 00:14 KST — p3 압축·무길이 JSON 디코딩 크기 관찰 완료 (PR #7 main)

- **PR #7 병합 성공**: `4fe091451e3278aab8477abb1913144c9b3d00e5`, 기능 검증 SHA `c9e735b0d8ac79fc762f533577e582d8c780c04c`.
- `scanner/cdp_decoded_size.py`가 브라우저 CDP `Network.dataReceived.dataLength` 숫자만 추적하여, 승인 main frame origin의 **압축 해제 후 크기 ≤128KiB**임을 확인한 응답에 한해 기존 JSON 자료형 구조 분석. 큰 압축 JSON은 본문을 읽지 않는다. Request URL+메서드 중복/이벤트 불완전/기타 불확실성은 fail-closed. Step 1/2 변경 없음.
- 공식 실험 [39138406625](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39138406625): gzip 압축 171 B → 디코딩 1,171 B 분석, 압축 461 B → 디코딩 400,015 B 분석 금지. `streamResourceContent`는 빠른 요청에서 실패하여 폐기([실험 PR #6](https://github.com/hibi89/fable5.1_web_catcher/pull/6) 미병합 종료).
- **최종 CI Windows 67/67 PASS** [39139094290](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39139094290), **실제 headed Chromium 22/22 PASS + 공개 smoke 4/4 PASS** [39139094270](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39139094270). 신규 CDP setup 순서 회귀 및 마스킹 fixture 경로는 수정 후 재검증.
- **실제 사용자 공개 데모사이트** 읽기 전용 [39139325141](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39139325141) SUCCESS: 12.283초, HTTP200, 차트 3/API1, JSON 상태 `compressed_size_unknown`(전)→**`decoded_too_large`(후)**. 즉 API 디코딩 크기가 128KiB 초과이므로 원문/구조 분석하지 않음. JSON shape0/chart-api0, 사용자 클릭0. 실사이트 차트 변화/라인리지 미검증 유지.
- 검증 전용 PR #8 [closed unmerged](https://github.com/hibi89/fable5.1_web_catcher/pull/8). 사용자 실사이트 원문/토큰/스크린샷/전체 결과 저장하지 않고 aggregate만 수집. Chromium의 브라우저 내부 압축 해제 자체에 **절대 메모리 제한은 걸지 못함**. 사용자 승인 없이 128KiB 상향·추가 요청·임의 연결 생성 금지.
- 상세 `docs/STEP3_COMPRESSED_JSON_DECODED_BOUND_2026-10-18.md`. 다음 단위: 대용량 JSON의 안전한 필드 정보 확보 대안 또는 사용자 최신 Windows 수동 Record 검증.

---

# 2026-10-18 23:46 KST — p3 실제 대시보드 읽기 전용 Record 검증 1단위 완료

- 사용자 지정 URL `https://daily-dashboard-ldh-1013.clevertide128.chatgpt.site/#v-dash`를 최신 main의 PR #3/#4 기능을 사용하여 GitHub Ubuntu 24.04 headed Chromium/Xvfb에서 **실제 접근**. [Actions run 39137433372](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39137433372) SUCCESS.
- **12.397초, HTTP 200, 정상 stop_signal 종료, main-frame 문서 1개, XHR/fetch API 1건, SVG 후보 2개, CSS bar 후보 1개, fatal=False**. 0회 사용자 조작, 차트 변화 증거 0건, JSON 구조 수집 0건, chart↔API 후보 0건, 경고 집계 2건.
- 한계 원인 확인: API 응답이 `compressed_size_unknown`으로 제외됨. Content-Length 없는 압축 JSON은 안전상 PR #3 분석 범위 밖. 강제 본문 읽기/의미 없는 강제 연결 금지.
- **읽기 전용** 시험이라 차트 변화 증거 0건은 새 기능 미검증이지 실패가 아니다. 사용자 실제 Windows PR #3/#4 적용 후 수동 필터 조작 시험은 미실시.
- 테스트용 임시 PR [#5](https://github.com/hibi89/fable5.1_web_catcher/pull/5) **병합 없이 closed**, 전용 소스와 임시 workflow는 main 미포함. 전체 result/페이지 텍스트/인증 정보/스크린샷 저장 없이 집계만 GitHub CI 로그에 기록.
- 상세 `docs/STEP3_LIVE_READONLY_2026-10-18.md`. 다음 작업은 압축·길이 미확인 JSON의 **안전한 분석 방안 검토** 또는 사용자 수동 Windows 최종 검사. 이번 작업에서 본문 구조 분석이나 차트↔API 연결을 완료했다고 주장하지 않음.

---

# 2026-10-18 23:37 KST — PR #4 SVG/CSS 변경 증거 보강 검증 완료 및 main 병합

- **p3 다음 1단위 완료**. [PR #4](https://github.com/hibi89/fable5.1_web_catcher/pull/4) `main` 병합 SHA `67e72529be4d5e6a190d7c63fc0c840878301965`; 브랜치 검증 소스 `30a59be00d473a1040d67aa0d3166f41b70f5e70`.
- 원인: Private Actions 사용량 초과로 기존 Windows `39132765417`·Chromium `39132765458`가 job steps 0개로 실패했음. 저장소 Public 전환 후 작업 단계가 정상 실행됨.
- 최종 CI **Windows 65/65 PASS** [39136596883](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39136596883), **실제 headed Chromium 21/21 PASS + 공개 사이트 smoke 4/4 PASS** [39136596876](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39136596876).
- 새 기능: 일반 SVG의 선/도형/기하 속성 및 자식 구조 변경, CSS bar 그룹의 길이 변화 증거를 UTC ms와 제한된 `change_evidence`로 기록. 호버 클래스 변화는 일반 SVG 갱신으로 간주하지 않음. CSS bar 숫자는 브라우저 문서 안에서만 임시 비교, 값/원본/스타일은 결과에 비저장.
- 이전 스냅샷의 정상 chart 갱신 시각을 유지하고 보고서에 변화 증거 구분 표시. **API↔차트 실제 인과관계/확정 데이터 계보 추정은 여전히 하지 않음**. 무허가 origin·인증 값 수집 제한, Step 1/2 회귀 보존.
- 첫 Chromium 재시도에서 20/21 PASS였으나 마지막 실패는 **API가 없을 때 `chart_candidates` 키가 생략될 수 있음을 테스트에서 고려하지 않은 기대값 문제**. 키 생략을 허용하는 테스트만 수정한 최신 SHA로 21/21 PASS 검증. 이력상 실패를 최종 성공과 혼동 금지.
- **사용자 Windows 실제 대시보드에서 새 SVG/CSS 변화 감지가 성공하는지는 미검증**. 일반 CSS/SVG 변화가 반드시 실제 데이터 변화를 뜻하는 것도 아님. 해당 사이트의 API 연결 후보 0건 문제는 여전히 별도 데이터 근거가 필요.
- 상세 근거: `docs/STEP3_GENERIC_CHART_GEOMETRY_PENDING_2026-10-18.md` 상단의 최종 판정 섹션. 기존 문서에 남아 있는 'CI 차단/PR4 미병합' 내용은 과거 이력.

---

# 2026-10-18 22:44 KST — p3 다음 1단위 구현, CI 차단으로 병합 대기

- `r`을 한글 자판의 `ㄱ`으로 해석해 다음 범위 단위 시작: 일반 SVG와 CSS bar 그룹의 기하적 변화 단서 수집.
- PR #4 (branch `fix/step3-generic-chart-change-evidence-20261018`): https://github.com/hibi89/fable5.1_web_catcher/pull/4, 기능 SHA `48312f0e6a7a21d138f083af9194e57d7b651ae1`, 문서 SHA `2cc411bb4fd309a541ef1b9b8204427bae8af31b`.
- 코드: SVG path/d/geometry/childList 변화 시각과 분류형 change_evidence, CSS bar 퍼센트 그룹의 동일 요소 내 모양 변화 비교, 무의미한 호버 이벤트 제외, 수집 값/스타일 원문 미저장, generic chart의 무근거 API 매핑 금지.
- 비브라우저 V8 JS 문법 검사와 모의 DOM에서 CSS baseline→변화, SVG class-only→geometry-change 분기 확인. **Python/Chromium CI는 PASS 아님.** PR 호출된 Windows `39132765417` 및 Chromium `39132765458` 실패, job steps 0개/로그 BlobNotFound. Windows 1회 재실행도 작업 단계 시작 전 실패. 해당 오류를 코드 테스트 실패로 확정할 근거 없음.
- 검증 전 변경을 `main`에 병합하지 않았다. 기존 PR #3 코드 및 CI 63/20/4 PASS 그대로 유지. **이번 단위 상태: 구현과 모의 JS 검증 완료, CI 실제 회귀 검증 차단, 병합 보류.**
- branch 문서: `docs/STEP3_GENERIC_CHART_GEOMETRY_PENDING_2026-10-18.md`. 다음 실행은 GitHub Actions runner/계정 상태 확인 또는 동일 소스의 직접 Python·Chromium 회귀 검증이 우선. 사용자 Windows 테스트 반복 불필요.

---

# Step 3 후속 단위: 헤더 없는 JSON 안전 구조 수집 추가 (2026-10-18 22:30 KST)

- **PR #3 main 병합 완료**: `f7b9bb9c09bc69cd305519b5676af31ff4b2d7ea` / 검증 기능 `dc5992391b399e29bcf6167daf455676e3c15ca7`. 사용자 Windows Record에서 외부 JSON이 `size_unknown`으로 제외됐던 원인에 대응.
- 새 기능은 `--record`에서만 수행. 응답에 Content-Length가 없을 때 requestfinished 후 Playwright 전송 크기 측정, 비압축·128KiB 이하만 JSON 값 없는 구조 분석. 크기/압축/본문 건수/민감키/origin 제한 유지. 기존 `--runtime`은 헤더 없는 JSON `size_unknown` 정책 유지.
- GitHub Actions 실제 확인: Windows Python 3.11 run **39131631123**, **63/63 PASS**. Ubuntu headed Chromium run **39131631050**, **20/20 PASS**, 보조 공개 사이트 **4/4 PASS**. 초기 CI 실패(대기열 정리·기존 Step 2 회귀·테스트 HTTP 버전)는 같은 PR에서 수정했고 최신 두 run만 합격 근거로 사용.
- **사용자 실제 대시보드의 해당 API가 구조 분석 성공하는지는 미검증**. Playwright 본문 처리의 절대 메모리 상한 보장은 없으며 JSON이 여전히 과대/압축/구조 오류일 수 있다. CSS/SVG 차트↔API 연결 후보 0개 문제와 iframe 미지원, browser_closed 시 스냅샷 경고는 변경 안 함.
- 상세: `docs/STEP3_HEADERLESS_JSON_BOUND_2026-10-18.md`. 다음 `ㄱ`은 별도 1단위로 generic CSS/SVG 변경 관찰 근거 보강을 검토할 수 있다. 이 단위에서 미구현.

---

# 2026-10-18 22:03 KST — Step 3 Windows 실제 사이트 재시험 결과 (result(3).json)

- **핵심 Record 동작 및 PR #2 현장 회귀 검증 통과.** 실제 33.312초 수집, browser_closed 정상 종료, 35건 실제 click, 복합키 기준 중복 **0건**, SPA 문서 1건/nav-0001, 차트 후보 3건/ID 충돌 0건, target.final_url 기록 성공.
- 승인한 외부 API origin을 포함해 2곳 허용. 기록된 API 200 application/json, `response_body_analysis=size_unknown` → Content-Length 미확인으로 JSON 구조 분석 보류, `chart_candidates=0`. 차트 후보는 generic SVG/CSS, 관찰 갱신 시각 없음. 첫 기록 클릭은 보존된 API 응답보다 1,539ms 뒤. 데이터 흐름을 임의 연결하면 안 된다.
- 본 실사이트 검사에선 클릭으로 인한 실제 필터 변화나 차트↔API 대응 후보는 미검증. Step 3 CLI 실사용/중복 수정 검증은 완료이지만 사용자 지침의 최종 예시인 'API와 차트 연관 후보 표시'는 이 사이트에서 충족되지 않았다.
- 경고: iframe 미지원, 네트워크 상세 1건 생략, browser_closed에 따른 TargetClosedError 차트 스냅샷 오류(정상 종료 자체는 성공).
- 현장 검사 원본 `result(3).json` SHA-256 `f501ee54ce773c8f7f1bd22945045371929d8ecf7275a876738595bfcf985067`; 전체 원본 결과는 GitHub 저장 금지. 상세: `docs/STEP3_WINDOWS_REAL_SITE_VERIFICATION_2026-10-18.md`.
- 이전 상태의 '실사이트 최종 재시험 미확인' 문구는 역사적 기록이며, **이번 새 현장 자료가 해당 확인을 대체한다**.

---

# 2026-10-18 사용자 업로드 후속 판정 — 새 실사이트 재시험 미확인

- 사용자가 추가 제출한 `result(2).json`은 직전 `result(1).json`과 바이트 단위로 완전히 동일 (SHA-256 `f47e088964ee947c7c3daf6be90d66565190ccb94f868491450036e2d1a29d0f`).
- JSON 내부 시작/종료 UTC: `2026-10-18T12:29:14`~`12:30:01`; 47.344초, 사용자 조작 총 228건, 실제 고유 조작 식별자 75건, 중복 초과 153건. 차트 4건 중 동일 id 중복 1건. 마지막 URL null. allowed_origins는 대시보드 하나이며 외부 API response_body_analysis는 `scope_or_auth_body_excluded`.
- 이는 **수정 전 동일 실행 결과**를 다시 첨부한 것으로, PR #2 병합 이후 Windows 실사이트 테스트가 성공 또는 실패했다는 새 근거는 아님. 자동 테스트 PASS 근거는 기존 문서대로 유지. STEP 3 실사이트 최종 검증 **보류**.
- 다음 검수는 로컬 최신 `main`을 `git rev-parse --short HEAD`로 확인 후 새 `--out ./out/record-after-fix`로 실행한 **그 경로의** `result.json`을 제출받을 것. 결과 파일이 새 실행 시간/명시적 API origin/고유 클릭을 포함하는지 재검토.

---

# Step 3 실제 사용자 대시보드 피드백 반영 (2026-10-18)

- 기존 Step 1/2 및 Step 3 CLI MVP 통과 상태 유지.
- 실제 사용자 테스트 기록: 약 47.344초, 4개 차트 후보, 조작 228건, 문서 5건, API 상세 1건, 차트↔API 후보 0건, browser_closed 종료. 외부 n8n webhook의 응답 구조는 origin 미허용으로 분석 제외.
- 수정: SPA hash/history 변경을 실제 새 JS 문서와 구분하고 중복 마커를 방지. chart ID 안정성 및 browser_closed 이후 last final_url 보존.
- [검증 완료] PR #2 소스 SHA 173d42d3a33d29bf80c2dc5a137daccf0992216d / main 병합 SHA b5496a61bd82d56204bdab24c984288230a95713.
- Windows CI run 39128145838: 60/60 PASS. Ubuntu headed Chromium CI run 39128145939: 19/19 PASS. 같은 run의 선택 공개 페이지 smoke: 4/4 PASS.
- [미검증] 위 코드를 사용자 Windows 실사이트에 적용한 재시험; 명시적 --allow-origin 사용 이후 외부 JSON 구조 확보 여부; 실제 CSS/일반 SVG 차트↔API 계보 확정.
- 보안: cross-origin 응답 구조 허용은 명시적으로 지정한 정확한 origin만. 일반 SVG/CSS 차트에 매핑 결과를 강제하지 않음. 공개 URL 서비스 배포 금지 유지.
- 인수 근거: docs/STEP3_REAL_RECORD_FEEDBACK_2026-10-18.md, 기존 docs/STEP3_FINAL_ACCEPTANCE.md.

---

# STATUS.md — Fable 5.1 Web Catcher / Step 3 자동 인수검사 완료

## 현재 검증된 기준 (2026-10-18 KST)
- Step 1 정적 CLI: 원본 7/7 PASS (유지).
- Step 2 Chromium runtime CLI: 원본 9/9 PASS (유지).
- **Step 3 headed Record CLI: 자동 fixture 인수검사 8/8, Windows 60 PASS / Ubuntu 실제 headed Chromium 16 PASS / 보조 공개 URL 4 PASS.** 실제 사람의 Windows 실사이트 로그인·필터·Enter 시나리오는 미검증.
- 검증 소스 80f71d2b7de0f7a803872e76a616fe70f974e192; PR #1 → main 병합 e28ea7f1f5a91d2f7a69160377558c6bc72e836d. 문서 변경 HEAD는 별도.
- 배포 없음: Python 로컬 CLI, Vercel/Production 미적용.

## 새 구현
--record, --max-duration (기본 900초), 반복 --allow-origin, 터미널 Enter·Ctrl+C·시간 만료·창 종료/EOF. 신규 tabs/main frames 문서 ID, 클릭·변경 마커, 승인 origin만 DOM/값 없는 응답 구조, 인증 요청 본문 보호, 이벤트 상한 생략 경고. Playwright 비영구 context. Step 2 수집기 유지 + 완료 JSON 구조 점진적 분석으로 페이지 이동 전 반영. result.json/report.md의 record 섹션 및 차트↔API **연관 후보**.
주요 경로: scanner/record_scan.py, scanner/network.py, scanner/chart_mapping.py, scanner/report.py, scan.py, tests/test_record.py, tests/browser_record_check.py, docs/STEP3_FINAL_ACCEPTANCE.md.

## 실제 검증
- Windows workflow run 39126644441: python -m pytest -q → 60 passed.
- Ubuntu run 39126644405: Xvfb Chromium 브라우저 fixture → 16 passed.
- 선택 공개 홈페이지 smoke → 4 passed. 모든 테스트는 해당 SHA에서 PASS.
- 원본 Step 1/2 회귀 포함. 개인정보/외부 origin/브라우저 중단/종료 시점 및 API 연관 후보 검증. 테스트용 login은 fixture에서 자동화한 것으로 실제 서비스 계정 로그인과 구별.

## 남은 한계 및 다음 순서
사용자의 Windows 표시 Chrome에서 직접 로그인→차트 필터 변경→Enter 확인 **검증 대기**. iframe DOM 분석 미지원(경고), 모든 사이트 차트 감지 및 API 인과 계보 확정 불가, Playwright decoded body 순간 절대 메모리 상한 미보장. 외부 URL을 받는 서버 배포 금지(SSRF 격리 없음). 필요하면 보안/범위/인증 변경은 먼저 승인. 인수인계 상세 HANDOFF.md, 증거 docs/STEP3_FINAL_ACCEPTANCE.md.

---

# Step 2 STATUS — 보존 이력

## 최종 판정 (2026-10-18 KST)
- **Step 1 완료 7/7 (100%)**: 정적 CLI 회귀 유지.
- **Step 2 원본 완료 기준 9/9 (100%) PASS**: 공개·무인증 페이지 CLI MVP 범위. 상세 기준/근거 `docs/STEP2_FINAL_ACCEPTANCE.md`.
- GitHub 비공개 `hibi89/fable5.1_web_catcher`, `main`. 기능 최종 검증 SHA **`e743e8c2b208940e66e03cfd6fc799031d7cc337`**. 배포/Production/Vercel 없음.

## 구현한 Step 2 범위
1. --runtime/--headed/--wait 기본 10초, 새 격리 Chromium, 이동 전 리스너, 제한 스크롤, 자원 정리.
2. XHR/fetch 관찰 endpoint, HTTP 메타데이터, 크기 제한 JSON 값 없는 구조, GraphQL 후보.
3. WebSocket 프레임 개수 및 SSE 연결 메타데이터(내용 미저장).
4. 알려진 JS 차트 라이브러리 런타임 마커, DOM+MutationObserver 기반 SVG/canvas 후보(확정 아님).
5. 차트↔API 근거 기반 보수적 **연관 후보**, 동시 적격 API 경합 시 보류.
6. 이미 로드된 동일 출처 JS 파일 10개 이하/개별 128KiB 이하의 문자열 기반 **미검증 API 후보**; 새 경로 요청 안 함.
- **출력 구분:** `api.endpoints`는 실제 XHR/fetch, `api.connections`는 실제 WS/SSE, `api.candidates`는 미검증 JS 문자열(source_script/discovered_by=bundle_string), `api.chart_candidates`는 차트 연관 후보(reasons/limitations). `charts[].data_sources`는 확정 lineage 아님.

## 최종 실행 테스트
- Windows Server 2022 / Python 3.11: `python -m pytest -q` → **55/55 PASS**, run **39120274152**.
- Ubuntu 24.04 / 실제 Playwright Chromium: 4개 독립 fixture 테스트 파일 → **11/11 PASS**, run **39120274247**.
- 공개 `https://example.com/`, `https://www.python.org/`의 정적 및 Chromium 런타임 각 1회 → **4/4 PASS**; HTTP 200, exit 0 및 구조/근거 검사 통과. 같은 Chromium run 로그.
- 모두 소스 SHA **`e743e8c2b208940e66e03cfd6fc799031d7cc337`**. 최종 완료 문서/README 커밋은 테스트 후 별도 문서 변경.
- 중간 실패·옛 스키마는 최종 성공과 혼동하지 말 것. 최종 원본 스키마/10개 상한/이유(reasons)·HTML 내장 가능성 문구를 수정하고 재검증.

## 한계 / 비목표
- 실제 라이브러리 통합은 일부 stub, 임의 공개 사이트의 탐지 정확도는 미검증. 차트↔API 매핑은 실제 데이터 흐름 확인이 아닌 연관 후보.
- Playwright 본문 압축 해제 메모리의 절대 상한 보장 불가. 브라우저 미설치나 사이트 차단 시 부분 결과 및 안내.
- 개인 Windows PC headed 동작 및 SSRF 서버 방어 미검증/미구현. 외부 사용자 URL 서비스로 배포 금지.
- Record 모드, LLM, 웹 UI, 다중 페이지 크롤러, Production 배포는 범위 밖.

## 다음 진행
**필수 Step 2 작업 없음.** 새 사용자 요청이 있을 때에만 실사이트 확대 검증·정확도 개선·후속 Step 3/배포 등을 별도로 계획. `HANDOFF.md`에 10항 인수인계.

## 추가 실사이트 정확도 검증 1차 (2026-10-18 KST)
대상: https://daily-dashboard-ldh-1013.clevertide128.chatgpt.site/#v-dash
- 확인된 기존 약점: SPA URL fragment 손실, 18~60px 장식 SVG 다수의 과다 차트 후보 수집, CSS 막대 그룹 미감지.
- 최소 수정: --runtime 브라우저 탐색의 hash 유지(결과에는 미노출), 실제 DOM 크기/도형 수 기반 generic SVG 필터, 가변 퍼센트 높이/너비의 반복 막대 그룹에 css_bar_pattern_candidate(library unknown, confidence 0.5) 보수적 탐지.
- 해당 대시보드 실사이트: HTTP 200, XHR/fetch 2, 기존 차트 후보 14~15 -> **3건**(큰 SVG 2 + CSS 그룹 1), 알려진 라이브러리 0, 차트↔API 연관 후보 0(충분한 증거 없음), 오류/경고 0.
- Windows Python 3.11 **57/57 PASS** run **39123343492**, 실제 Chromium regression **12/12 PASS** run **39123322129**, 사용자 지정 URL 실사이트 진단 성공 run **39123343463**. 실사이트 검증 코드 SHA **b7c707386034a14c44820709b4a13388dfcf7e7e**. 이후 문서 수정만 이뤄짐.
- 실사이트 전체 그래프의 정밀 탐지율·데이터 API lineage는 미검증. 상세한 원인/회귀/출력 차이: docs/DASHBOARD_LIVE_ACCURACY_2026-10-18.md.
- Step 2 원본 기준 9/9 PASS 판정 유지. 다음 실제 대시보드 확장 검증은 별도 지시 시 진행. 개인 Windows에 이번 개선사항이 적용됐는지는 미확인.
