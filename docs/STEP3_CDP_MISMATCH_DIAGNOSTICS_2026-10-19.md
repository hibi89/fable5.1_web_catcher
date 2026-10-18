# Step 3 — CDP 길이 관찰 누락 진단 및 안전한 사유 코드 (2026-10-19 KST)

## 목표와 최초 증상
- 이전 Chromium 자동 테스트에서 일부 gzip/브라우저 세션이 `structure_only` 또는 `decoded_too_large` 대신 `compressed_decoded_unavailable`로 종료됨.
- 예외적인 CDP 길이 정보 미확정 시 본문을 **읽지 않고** 거부하는 보안 정책은 유지하되, 어떤 단계가 부족한지 값 없는 진단을 추가하려는 작업.
- 기존 Step 1~4 구현/Mock 검증은 유지. 외부 유료 API·사용자 실제 사이트 접근은 이번 실험에서 **0회**.

## 임시 실험: 요청 시각·크기·CDP 매칭 (PR #14, main 미병합)
- 임시 전용 PR [#14](https://github.com/hibi89/fable5.1_web_catcher/pull/14), localhost Chromium fixture `/gz-small`, `/gz-large`. 각 실행 8건(작은/큰 gzip × 요청 완료 후 0ms/500ms × 2회). 인증·응답원문·URL/키·화면 내용은 로그에 미기록, 숫자/안전상태 enum만 사용.
- [Run 39145052430](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39145052430): `DecodedLengthTracker.decide` 시점 **no_cdp_match 4/8**, 정상 범위 2/8, decoded cap 초과 2/8.
- [Run 39145239370](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39145239370): **no_cdp_match 5/8**, 정상 1/8, cap 초과 2/8.
- [Run 39145407563](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39145407563): **no_cdp_match 3/8**, 정상 3/8, cap 초과 2/8.
- 총 24건 실험 중 **12건이 판정 시점에 요청 키와 CDP 추적 상태를 연결할 수 없었음**. 작은/큰 gzip 양쪽에서 재현; 500ms 대기만으로 일관되게 사라지지 않음. 실험 건수가 적고 독립 표본 추출이 아니므로 이를 모든 사용자 사이트의 실제 실패율(50%)로 일반화하지 않는다.
- 별도 감시 콜백은 결과에 이벤트 카운트를 남기지 못함(`P3_CDP_DIAGNOSTIC_REQUEST_EVENTS {}`). **이 테스트로 frame ID 불일치/Playwright/CDP 이벤트 자체 유실/메서드·URL 대응 실패 중 어느 항목이 원인인지 확정하지 못함**. 판정 시점의 *미매칭*만 확인.
- 임시 진단 브랜치 및 workflow는 제품 main에 **미병합**. 동일 방식 반복 재시도는 종료.

## 제품 기능 반영: PR #15
- [PR #15](https://github.com/hibi89/fable5.1_web_catcher/pull/15) main 병합 `f6cf9577941fff829cab0b827b5b95fd7e8eac88`, 검증 source `385851177b20339c167957d2579bb2a18694b804`.
- `scanner/cdp_decoded_size.py`: `refusal_reason(request)`는 CDP 추적 상태에서 아래 enum만 반환:
  - `request_unmatched`, `request_ambiguous`
  - `loading_failed`, `invalid_data_length`, `loading_incomplete`, `no_data_events`
  - `exceeds_decoded_cap`, `nonpositive_decoded_length`, `ready`, `diagnostic_unavailable`
- `scanner/record_scan.py`: 승인된 JSON이 기존 `compressed_decoded_unavailable`로 제외될 때만 `cdp_decoded_diagnostic` 속성을 추가. **기존 `response_body_analysis` 값, 본문 수집 128KiB 제한, origin/main-frame/auth 필터, CDP 응답 처리 흐름은 변경하지 않음**. URL/호스트·requestId·본문·필드명·쿠키·인증정보 같은 원문은 진단 속성에 절대 넣지 않음.
- 신규 `tests/test_cdp_decoded_size.py` 사유 코드 유닛 테스트, Chromium `tests/browser_record_check.py`에서 안전 거부의 구조 null/원문 미수집 및 허용 enum 확인.
- Chromium fixture의 정상 positive 탐지가 가능한 경우 기존 필드·자료형 구조/부분 구조를 검증. 해당 단위에서 CDP 요청 자체가 매칭되지 않는 경우에는 기존 제품이 안전 거부하는 것이 맞으므로 **이를 별도 합법적 결과로 판정**. 이 조정은 CDP 성공 확률 개선을 의미하지 않음.

## 최종 CI 결과
- [Windows run 39145907566](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39145907566): **99/99 PASS**.
- [실제 Chromium run 39145907594](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39145907594): **23/23 PASS**, 보조 공개사이트 smoke **4/4 PASS**.
- 첫 PR #15 테스트 run `39145703191`은 22/23으로 실패: 대용량 gzip 부분 구조 positive만 기대하던 테스트가 `compressed_decoded_unavailable`로 끝남. 안전하게 거부한 경우의 상태/진단 코드/본문 null도 함께 검사하도록 테스트를 분기한 후 위 CI 전체 통과.
- 실제 데이터 탐지율·CDP 이벤트 성공률 개선을 과장하지 않으며, **진단 가능성이 높아진 것**을 이번 작업의 완료 지표로 삼는다.

## 인수 및 다음 작업
- `result.json`에서 해당 API가 `compressed_decoded_unavailable`이면 `cdp_decoded_diagnostic`을 추가 확인해 상태가 요청 미매칭/불완전 이벤트/실패 중 어디인지 구별한다. 이 값은 기술 아키텍처의 확정 근거도 아니고 사용자가 수동 복구할 키도 아니다.
- 사용자의 Windows 실제 사이트에서는 새 진단 코드의 분포와 필터 변화→차트 갱신 증거를 아직 테스트하지 않았음.
- 구조적 성공률 개선은 별도 검증된 CDP 추적 설계 또는 추가 관측 필요. 실패 시 안전 거부/개인정보 보호를 제거하지 않는다.
- Step 1~4 원본 자동/Mock 기준은 4/4 완료 유지. **최종 상용제품 전체 진도 %의 분모는 아직 확정되지 않았으므로 별도 퍼센트를 임의로 제시하지 않는다.** 이번 진도는 성공률이 아니라 실패 사유 설명력 개선이다.
