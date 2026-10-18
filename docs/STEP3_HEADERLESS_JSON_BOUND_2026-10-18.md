# Step 3 단위 개선: 헤더 없는 JSON 응답의 용량 확인 후 자료형 구조 추출 (2026-10-18)

## 사용자 현장 데이터에서 발견된 문제
- 직전 Windows 실제 사용자 Record: 33.312초, 35 클릭·중복 0, 차트 ID 중복 0, 최종 URL 정상 기록.
- 승인된 외부 API에서 `HTTP 200 application/json` 응답을 확인했지만 `response_body_analysis=size_unknown`으로 JSON 구조를 수집하지 못함. 응답에 신뢰할 Content-Length가 없을 때 기존 파서가 본문을 아예 읽지 않도록 설계되어 있었기 때문.
- 원래 목적인 차트↔API 데이터 연결은 그 사용자 현장 결과에서 여전히 0건. 이번 단위는 **JSON 구조 수집 경로만** 개선한다. 라이브러리 없는 generic SVG/CSS 차트의 연결 판단을 새로 강제하지 않는다.

## 구현 범위 (PR #3)
- 병합 PR: https://github.com/hibi89/fable5.1_web_catcher/pull/3
- 검증 기능 SHA `dc5992391b399e29bcf6167daf455676e3c15ca7`; main 병합 `f7b9bb9c09bc69cd305519b5676af31ff4b2d7ea`.
- 범위: `scanner/network.py`의 `NetworkCollector(..., allow_unknown_length=True)`를 **Step 3 Record에서만** 켠다. 기존 Step 2 `--runtime` 기본값 False를 보존해 헤더 없는 JSON은 여전히 `size_unknown`.
- Step 3: JSON Content-Length가 없을 때 완료 전에는 본문을 읽지 않는다. `requestfinished` 이벤트 이후 `request.sizes().responseBodySize`(전송된 인코딩 본문 바이트)를 보고 결정한다.
- 전송 크기 128KiB 이하인 **비압축** 응답만 본문 검사 후보로 허용한다. 크기가 없거나 오류면 `size_unknown`, 크기 초과면 `too_large`, 압축된 미확인 길이면 `compressed_size_unknown`.
- 실제 `response.body()` 후 다시 디코딩된 크기를 검사하며 128KiB 초과 시 `decoded_too_large`로 값/구조를 보관하지 않는다. 기존 20개 body 상한과 JSON depth/키/배열 제한 유지.
- 응답 값/원문, 인증·쿠키·입력값, 세션은 저장하지 않는다. `_json_shape`를 그대로 사용하여 타입/필드 이름만 저장하고 민감 키는 가린다.
- `ScopedNetworkCollector`의 정확한 `--allow-origin` 검사와 인증 경로 제외 원칙 보존. 명시적 허용이 없는 외부 JSON의 본문은 조회하지 않는다.
- 관찰된 기존 응답만 분석한다. 새로운 URL/API 호출이나 사용자 입력 자동화는 없다.

## 자동 테스트 (실제 GitHub Actions 확인)
- Windows Python 3.11 workflow **39131631123**: `63 passed` (기존 Step 1/2 포함).
- Ubuntu headed Chromium + Xvfb workflow **39131631050**: `20 passed` (Record chunked JSON 동작, 크기 초과, 외부 origin 범위, 기존 runtime 포함).
- 같은 Chromium 워크플로 선택 공개 URL smoke: `4 passed`.
- 해당 결과는 브랜치 기능 SHA `dc5992391b399e29bcf6167daf455676e3c15ca7`에 대한 자동 테스트. 사용자 실사이트 최신 코드 재시험은 수행되지 않았다.

## 남아 있는 한계와 후속 단위
- Playwright 브라우저 및 `response.body()` 자체의 메모리 사용량을 절대 128KiB로 강제하지는 못한다. 전송 크기 검사 후 본문을 메모리로 읽으며 다시 크기를 검사하는 방식이다. 악의적/이상한 콘텐츠나 미검출 인코딩에 대해 하드 메모리 상한을 보장하지 않는다.
- 기존 Step 2의 헤더 없는 응답 `size_unknown` 정책은 유지. 임의 외부 URL을 받는 공개 웹서버로 배포 금지(SSRF 격리 없음).
- 외부 실사이트에서 실제 `request.sizes()`가 유효한 값을 제공하는지, JSON이 지정 상한 내인지 여부는 다음 실제 사용자 실행에서만 확인 가능.
- 해당 API가 실제 그래프를 구동했는지 확정되지 않았다. CSS bar/generic SVG에 속성 갱신 단서가 없어 매핑 후보 0건 문제는 **별도 고도화 단위**로 분리. iframe DOM 분석/브라우저 종료 직전 TargetClosedError 경고도 기존 한계.
- 현재 p3 작업의 다음 단위는 데이터 갱신을 근거로 한 generic SVG/CSS 변화 관찰 강화 또는 현장 JSON 결과 검증 중 하나. 본 단위에서 구현했다고 주장하지 않는다.
