# p3 Step 3: Content-Length 없는 압축 JSON의 디코딩 크기 검증 (2026-10-18)

## 문제 및 기존 관찰
- Windows 실사이트: 승인한 외부 API 200 JSON이 `size_unknown`으로 제외됨. PR #3 이후 Ubuntu headed Chromium 실제 공개 대시보드 읽기 전용 검사에서는 API 1건이 `compressed_size_unknown`으로 제외.
- 전송(압축) 바이트 크기만으로 안전한 JSON 구조 파싱을 허용하면 압축 해제 폭탄에 취약하다. 원본 응답/인증값을 영구 저장하거나 별도 HTTP 요청으로 다시 조회하는 것은 원래 사용자 지침과 맞지 않음.

## 대안 비교와 실제 실험
1. **CDP `Network.streamResourceContent` 실험:** 응답 헤더 직후 빠른 JSON을 대상으로 활성화하려 했으나 `Request with the provided ID has already finished loading` 오류로 실패. 빠른 응답에 일반적으로 안전하게 작동한다고 주장할 수 없어 폐기.
2. **CDP `Network.dataReceived.dataLength`(디코딩 크기) 관찰:** 새 요청이나 원문 추출 없이 브라우저가 원래 발생시키는 XHR/fetch 이벤트의 길이만 합산. GitHub Ubuntu 실제 Chromium 로컬 gzip-chunked/Content-Length 없는 fixture:
   - 작은 JSON 압축된 전송량 **171 bytes**, 디코딩 후 **1,171 bytes** -> `response.body()`로 값 없이 구조 파싱 가능.
   - 압축된 전송량 **461 bytes**, 디코딩 후 **400,015 bytes** -> 128KiB 상한 초과로 `response.body()` **호출 없이 제외**.
   - 검증 run: [39138406625](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39138406625), PASS. 실험 전용 [PR #6](https://github.com/hibi89/fable5.1_web_catcher/pull/6)은 main 미병합 종료.

## 구현 및 허용 범위
- [PR #7](https://github.com/hibi89/fable5.1_web_catcher/pull/7) main 병합 SHA **`4fe091451e3278aab8477abb1913144c9b3d00e5`**; CI 확인 기능 SHA **`c9e735b0d8ac79fc762f533577e582d8c780c04c`**.
- `scanner/cdp_decoded_size.py`: Chromium CDP의 `dataLength` 숫자만 제한 수집. 승인된 정확한 origin, main frame, 인증 경로 제외. 페이지별 같은 URL+HTTP 메서드가 중복되면 정확한 요청-응답 대응을 확정할 수 없으므로 추론 중단. 항목 추적 300건 상한, 데이터 길이 128KiB 초과 시 포화값/거부.
- `scanner/record_scan.py`: Step 3 Record의 원래 `ScopedNetworkCollector`가 길이 없는 gzip/br 응답에만 CDP 판정을 사용. 요청 완료와 디코딩 길이가 모두 확인되고 1~128KiB 내라면 기존 `_json_shape` 파서 사용. API origin·로그인/토큰 경로 차단, Request body 미수집, Page JS 비변경.
- `scanner/network.py`: 실제 body read 후 읽은 바이트 크기가 앞서 확인한 디코딩 크기와 불일치하면 **값/구조 기록 없이 제외**. 기존 128KiB 제한, 20개 body 분석 상한, 비밀키 마스킹 유지.
- CDP의 `Network.streamResourceContent`와 `Network.getResponseBody`, 네트워크 요청 변조/재전송/라우트 인터셉트는 사용하지 않음.
- 새 파일은 Step 3 Record에서만 사용. Step 1 정적 및 Step 2 `--runtime` 정책은 그대로 유지.

## 최종 자동 검증
- GitHub Windows Python 3.11 [39139094290](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39139094290): **67/67 PASS**.
- GitHub Ubuntu 실제 headed Chromium [39139094270](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39139094270): **22/22 PASS**; 선택 공개 사이트 추가 스모크 **4/4 PASS**.
- 첫 CI에서 신규 CDP 초기화 순서가 기존 main-frame navigation 이벤트 관찰을 방해했으므로 기존 navigation 이벤트 핸들러를 먼저 등록하도록 수정. 또한 새 fixture 테스트의 긴 endpoint 경로가 기존 URL 마스킹에 걸려 정당하게 `[REDACTED]`되는 문제를 짧은 고정 경로로 수정. 수정된 최종 SHA에서 전부 PASS.
- 승인 안 된 cross-origin 응답 구조는 여전히 미수집; gzip 압축 JSON 정상/초과, 값과 URL 토큰 비노출, 상태 보수적 거부, browser_closed 및 SVG/CSS 변화 기존 회귀 포함.

## 최종 실제 사용자 데모 사이트 읽기 전용 재검증
- PR #7이 병합된 main을 사용한 실제 Ubuntu Chromium read-only 검사 [39139325141](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39139325141): **SUCCESS, HTTP 200, 12.283초, 문서 1개, 승인 API 1건, SVG2/CSS bar1, 클릭 0, 정상 종료, fatal=False**.
- JSON 분석 상태가 **`compressed_size_unknown` (개선 전) → `decoded_too_large` (개선 후)** 로 바뀜. 즉 헤더 없는 압축 JSON의 디코딩 크기를 확인했지만 **128KiB를 초과해 원문/구조를 저장하지 않았다**.
- API JSON 구조 0, 차트↔API 후보 0, 차트 변화 마커 0. 수동 클릭/필터 미사용이므로 차트 변화 탐지 기능 실패로 판정 불가.
- 검증용 임시 [PR #8](https://github.com/hibi89/fable5.1_web_catcher/pull/8) **closed unmerged**. 공개 사이트 특화 테스트/워크플로는 production main에 넣지 않음.

## 남은 과제 및 보안상의 정확한 한계
1. **해당 실사이트의 대용량 응답은 구조 파싱 미지원**. 지금 상한(128KiB)을 사용자가 명시적 승인 없이 자동 확대하지 않는다. 확장 시 메모리·보안·비용 영향 및 실제 데이터 범위 재검토 필요.
2. CDP 데이터 수신 길이를 기반으로 Python 측의 **불필요한 전체 응답 조회를 피하는 것**이지 Chromium 브라우저 내부에서 그 응답을 압축 해제하는 메모리를 하드 제한하는 것이 **아니다**. 공격적 압축 폭탄에 대한 절대 메모리 안전 보장은 없음. 공개 URL 입력을 받는 서버로 배포 금지(SSRF 격리 없음).
3. URL+메서드 중복 요청, CDN 캐시, 이벤트 누락, 페이지/프레임 불일치, 연결 실패 시 **fail-closed**(미수집)한다. 이 기능은 추정/복구보다 거부를 우선함.
4. 실제 사용자 Windows 개인 PC에서 최신 코드로 직접 필터 조작해 `change_evidence` 기록 및 차트↔API 후보를 확보하는 검증은 아직 하지 않음. 자동 읽기 전용 시험에서 그 결과를 추론하지 않는다.
5. 다음 작업 한 단위는 대용량 API 전체를 받지 않는 **안전한 구조 정보 확보 대안** 검토(승인된 샘플/서버측 필드 목록 제공 등), 또는 사용자 수동 Windows Record 최종 검증. 무근거 lineage 생성 금지.
