# Step 3 대용량 JSON의 제한된 부분 필드 힌트 — 2026-10-19 KST

## 목적과 이전 한계
- 사용자 승인 대시보드 실제 API는 HTTP 200 JSON 1건을 관찰했지만 디코딩된 크기가 **128KiB 초과**하여 `decoded_too_large`로 본문을 분석하지 않았다.
- 설계 원칙: Step 1/2/3의 기존 보안·용량 제한과 권한 범위를 유지, 임의 새 API 요청/로그인/입력/원문·세션 저장 금지. 전체 API 구조라고 오인하게 만들지 않는다.

## 실험 및 구현
- 빠른 gzip 응답에서 CDP `Network.streamResourceContent`를 응답 후반에 활성화하면 `Request ... already finished loading` 오류가 발생. **requestWillBeSent 때 활성화**하는 국소 Chromium fixture [run 39139975182](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39139975182)에서는 작은 압축 JSON 1,171바이트를 성공적으로 기록했고, 큰 응답에서는 길이 제한을 적용할 수 있었다. 이 실험 전용 [PR #9](https://github.com/hibi89/fable5.1_web_catcher/pull/9)는 병합하지 않고 종료.
- **[PR #10](https://github.com/hibi89/fable5.1_web_catcher/pull/10)**: 검증 기능 SHA `df887d02c6602b3214c3aea9b8a6061e51611da6`, main 병합 SHA `07fb7ed6fd0b7fb095eb1710e4432557d5cffae5`.
- `scanner/cdp_decoded_size.py`: 기존 CDP 단일 세션에 원래 decoded-length 추적과 **최초 32KiB까지만** 응답 부분 스트리밍을 함께 실행. 같은 URL+메서드 중복/미완료/실패·CDP 오류는 부분 힌트 생성 금지. 먼저 받은 raw bytes는 프로세스 메모리에만 일시 보관.
- `scanner/json_prefix_hints.py`: JSON 루트 확인, 따옴표·escape·중첩 괄호를 구분하여 접두부 안에서 처음 **완전히 닫힌 JSON 객체**만 파싱. 기존 `_json_shape`를 사용해 값은 버리고 민감 키명은 마스킹한 필드명/자료형만 표기.
- `scanner/record_scan.py`: **독립적으로** `response_body_analysis=decoded_too_large` 판정을 받은 HTTP200 JSON만 대상. `json_structure`(전체 구조)와 별개인 `json_prefix_structure`을 선택적으로 부착. 이 필드에 `completeness:partial_prefix_only`, `sample_kind:first_complete_object`를 명시.
- `scanner/report.py`: **'부분 샘플 필드(전체 JSON 구조 아님, 연관 API 추정 근거 아님)'**을 보고서에 구별해 표시. `scanner/chart_mapping.py` 변경하지 않았으며 부분 힌트로 차트↔API 연결을 확정하거나 후보로 승격하지 않는다.
- 제한: 승인된 exact-origin main-frame Fetch/XHR 중 처음 최대 **20개 스트림**, 스트림당 접두부 **32KiB**, 부분 힌트 출력 최대 **10개**. 기존 전체 JSON 파서 **128KiB 및 20개 본문** 제한은 그대로 유지. 데이터 원본/HAR/스크린샷/인증정보/응답값 저장 없음.

## 초기 통합 회귀 문제와 해결
- 최초 구현은 별도 CDP 세션을 병렬 생성해 기존 소형 gzip 응답이 `compressed_decoded_unavailable`로 제외되는 **회귀** 발견; 대용량 부분 힌트도 불발. 이 구현은 병합하지 않음.
- CDP 기존 `DecodedLengthTracker`의 **동일 세션**에 streamResourceContent를 합쳐 브라우저 이벤트 순서를 안정화했고, 기존 소형 응답/차트 수집과 신기능을 다시 검증함.

## 검증 결과
- Windows Python 3.11: [run 39140626259](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39140626259) **70/70 PASS**.
- Ubuntu headed Chromium/Xvfb: [run 39140626261](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39140626261) **23/23 PASS**, 선택 공개 홈페이지 보조 검사 **4/4 PASS**.
- Chromium fixture는 128KiB 초과 압축 JSON에서 정상 JSON `json_structure=null`, **제한된 첫 객체 부분 필드 구조**가 `json_prefix_structure`에만 생성되고 개인값이 결과에 남지 않는지 검사. 기존 인증/인가 origin 제한, JSON 크기 초과, Record 종료, SVG/CSS, CLI 회귀 유지.
- 실제 사용자가 예전에 승인한 공개 대시보드 읽기 전용 재시험: [run 39140868626](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39140868626) **SUCCESS**, HTTP200, 12.395초, 문서1, API1, SVG2·CSS bar1, user-interactions0, `response_body_analysis=decoded_too_large`(정상), `json_shape_count=0`, **`partial_prefix_hint_count=1`**. 따라서 이전 **부분 구조 0 → 실제 1**로 개선.
- 실사이트 전용 검증 [PR #11](https://github.com/hibi89/fable5.1_web_catcher/pull/11)은 **closed/unmerged**. 로그에 필드 이름조차 공개하지 않고 집계만 남김.

## 범위와 보수적 판정
1. 첫 객체에 우연히 포함된 키만 표본이며, 마지막 요소/다른 객체/전체 JSON 데이터 형태를 증명하지 않는다. 접두부에 닫힌 객체가 없으면 부분 힌트도 생성되지 않는다.
2. 원래 128KiB를 초과하는 본문은 **전체 내용을 여전히 읽지 않으며**, `json_structure`는 null이다. 원래 제한을 우회해 용량을 늘리지 않았다.
3. CDP 이벤트 자체는 브라우저/프로토콜 메모리로 전달되며, Chromium 내 압축 해제의 절대 메모리 상한은 보장하지 않는다. 샘플용 Python bytearray만 32KiB로 제한한다.
4. 마스킹은 기존 `_json_shape`와 동일하며 임의의 개인정보로 보일 수 있는 **키 이름 전부가 보안 분류된다는 보장은 없다**. 민감한 업무 계정/비공개 도메인에는 허가받은 로컬 사용만 권장. Public 저장소에 민감한 result.json이나 원문 본문 업로드 금지.
5. 수동 필터·차트 실제 갱신의 사용자 Windows 검증, chart↔API 계보, iframe 분석은 이 단위에서 완료되지 않았다. 사용자 개입을 요구한 적 없음.
6. Step 1/2/3 원본 자동 인수 기준은 이미 통과했고 여기 추가 개발은 품질 고도화. 최종 '전체 진행률 %'의 분모가 되는 전체 출시 스코프/후속 단계는 공식 확정 문서에 없으므로 임의로 수치를 확정하지 않는다. 대신 **대용량 API 부분 구조 실사이트 확보 0→1건**을 이번 유의미한 진전으로 기록.

## 다음 단위
- 사용자 Windows에서 최신 main으로 필터 변화 재검증해 실제 `change_evidence`, API·차트 후보의 근거를 확인(사용자 개입 최소화); 또는 generic CSS/SVG와 직접 UI 이벤트 변화 시각 비교만 별도의 낮은 confidence 보조 단서로 시도하되 인과를 단정하지 않는다.
- 사용자 목표의 최종 Stage 4+ 요구사항을 받으면 그때 전체 완료율 산정 분모를 확정한다.
