# Step 3 Windows 실사이트 재시험 결과 — 2026-10-18

## 검증 대상 및 소스
- 사용자 제공 **result(3).json** (파일 SHA-256 `f501ee54ce773c8f7f1bd22945045371929d8ecf7275a876738595bfcf985067`, 15,860 bytes).
- 실제 사용자 Windows / headed Chromium Record; JSON 시작 `2026-10-18T13:03:10+00:00`, 종료 `13:03:43+00:00` (한국시간 22:03); `duration_seconds: 33.312`, `stop_reason: browser_closed`.
- 기능 수정 소스는 PR #2 (main merge `b5496a61bd82d56204bdab24c984288230a95713`); 기존 CI Windows `39128145838` 60 PASS, headed Chromium `39128145939` 19 PASS 및 선택 공개 페이지 4 PASS.
- 사용자 수집 JSON은 민감정보·사이트 구조를 포함할 수 있으므로 전체 원본 결과물은 GitHub에 추가하지 않는다. 요약/해시만 기록한다.

## 핵심 회귀 검증 판정

| 항목 | 수정 전 result(1)/(2) | 새 result(3) | 판정 |
| --- | --- | --- | --- |
| 실제 완료한 Record | 47.344초 / browser_closed | 33.312초 / browser_closed | PASS |
| 문서 수/navigation ID | 5, SPA 중복 | 1, nav-0001 | PASS |
| 조작 마커 총수 | 228 | 35 | 수치만으로는 PASS 아님 |
| 같은 page_id·timestamp·type·tag·selector 중복 초과 | 153 | **0** | PASS |
| 차트 후보 수 | 4 | 3 | 정보성 |
| 차트 ID 충돌 | 1건 | **0건** | PASS |
| target.final_url | null | 안전 URL 기록됨 | PASS |
| 허용 원본 | 대시보드 1곳 | 대시보드 및 승인된 별도 API origin 2곳 | 범위 설정 PASS |
| 웹훅 API 메타데이터 | 200, application/json | 200, application/json | PASS |
| API JSON 구조 | scope_or_auth_body_excluded | **size_unknown**, null | 아직 구조 미확보 |
| 차트↔API 매핑 | 0 | **0** | 미확인, 추정 금지 |

- 새 기록의 35건은 **모두 click**이며 change 마커는 없다. 클릭한 필터 버튼이 화면 데이터 변경을 유발했는지는 JSON만으로 확정할 수 없다.
- 기록된 외부 API 요청은 `1792328594567ms`에 시작, `1792328595513ms`에 응답 완료. 첫 기록된 클릭은 `1792328597052ms` (**응답 완료보다 1,539ms 뒤**). 즉 상세가 보존된 API 1건은 클릭 전의 초기 로딩 요청이다.
- 차트 첫 등장 `1792328603450ms`는 API 응답보다 7,937ms 뒤. 차트 후보는 `generic_markup_candidate`와 `css_bar_pattern_candidate`뿐이며 `last_observed_update_ms`는 모두 null이다.
- 엄격한 기존 매핑은 인식된 라이브러리 DOM + 갱신 시각 + 시계열 JSON 구조 등이 필요하므로 해당 현장 기록은 `chart_candidates=[]` 및 `mapping_analysis.marked_charts_assessed=0`. 초기 데이터를 메모리에 로드한 후 로컬 필터링하는 앱일 가능성은 있지만, 확인된 사실이 아니므로 단정하지 않는다.
- API origin 허용 후에도 응답 `Content-Length`가 없거나 확인할 수 없어 `response_body_analysis=size_unknown`. 기존 Step 2의 본문 크기 검증 정책에 따라 JSON 값/구조를 읽지 않은 **설계된 안전 제한**이다. 단순히 allow-origin을 더 추가해도 해결되는 상태가 아니다.
- 경고: iframe DOM/상호작용 미지원(기존 한계), 요청 상세 미수집 1건(범위/프레임/상한), `Record 차트 스냅샷 오류: TargetClosedError`(수집 도중 사용자가 창을 닫으며 생긴 최종 스냅샷 경쟁으로 추정; 기록·정상 종료는 성공). 예외 원인의 확정은 별도 재현 필요.

## 판정 및 남은 과제

1. **Step 3 CLI Record/실사이트 핵심 동작 검증 성공**: headed 브라우저에서 수동 조작 기록, 고유 클릭 시간, 같은-document SPA 처리, 유일 차트 ID, 외부 API 메타데이터 수집, 안전한 마지막 URL 보존, 종료 후 산출물 생성을 현장 결과로 확인.
2. 기존 8개 소프트웨어 인수 기준에 대한 자동 테스트 결과는 유지. 터미널 Enter / Ctrl+C / time-limit / popup / 로그인 흐름 등은 **fixture CI 근거**, 이번 현장 실행의 종료 방식은 browser_closed.
3. **원래 지침의 마지막 예시인 '직접 필터 변경 후 대응 API↔차트 연관 후보를 보고서에서 확인'은 이 현장 사이트에서는 미달성.** API JSON `size_unknown` 및 generic SVG/CSS의 갱신 근거 부족 때문에 연결할 수 없으며, 임의로 연결 후보를 만들지 않는다.
4. 추후 별도 개선 후보: 미확인 길이 JSON에 대한 안전한 bounded read 정책 설계(기존 Step 2 정책 변경 시 별도 검증 필수), CSS/SVG 차트의 DOM 갱신 근거 수집, 정상 browser_closed의 불필요한 TargetClosedError warning 억제, iframe 지원 범위 결정. **현재 수정·검증한 기능이라고 주장하지 않는다.**

## 다음 조치
- Step 3의 핵심 수집과 실제 오류 수정은 완료로 표기한다.
- 차트↔API 후보 확보는 미완료 범위로 남기며 Step 4 또는 별도 고도화에서 설계/수용 기준 명확화 후 진행한다.
- 사용자에게 동일 테스트의 반복을 요청하지 않는다. 현장 파일은 이미 충분히 제출되었다.
