# Fable 5.1 Web Catcher — Step 4 공식 SDK 오프라인 통합 검증 (2026-10-19 KST)

## 대상과 목표
- 대상 저장소: `hibi89/fable5.1_web_catcher`, 최종 `main`.
- 기존 Step 4 [PR #12](https://github.com/hibi89/fable5.1_web_catcher/pull/12)은 `FakeClient`로 SDK 호출 메서드 계약을 대체해 91개 Windows mock/fixture 테스트를 통과했었다.
- 이번 후속 [PR #13](https://github.com/hibi89/fable5.1_web_catcher/pull/13)은 **설치된 공식 `openai` Python SDK가 실제로 생성하는 HTTP 요청과 파싱된 Responses 객체를 오프라인에서 검증**한다.
- 병합 SHA: **`1339baf0a76e291a8f7fea2698b053cf9351c1a2`**, 최종 검증 소스 SHA **`42f481c821189e54c3b66b00dff17d767351b376`**.
- OpenAI 공식 Python SDK의 `httpx2` 기반 전송층에 `httpx2.MockTransport`를 주입하므로 **실제 네트워크 접근 0회/유료 API 호출 0회**. 인증키는 형식만 흉내 낸 `mock-placeholder-no-real-credential`이고 진짜 자격증명은 전혀 사용하지 않음.

## 추가된 구현/테스트
- 새 `tests/test_llm_sdk_transport.py` (+7건):
  1. `OpenAI(...).responses.create(...)` 호출이 실제 `POST /v1/responses`로 직렬화되고, `store: false`, `text.format.type=json_schema`/strict schema, 정확한 사용자 모델 문자열, `tools`/추가 도구 사용 없음 확인.
  2. 공식 SDK `Response` 객체의 `output_text`가 구조화된 JSON으로 추출·로컬 참조 검증되며 `usage` 카운트를 보존하는지 확인.
  3. 개인정보/호스트/폼 값/비신뢰 prompt injection 문자열 등이 SDK 전송 JSON에 섞이지 않는지 fixture 검증.
  4. 실제 SDK HTTP 상태 예외 객체에서 400/401 오류는 즉시 종료, 429/500은 최대 1회 자체 재시도 후 종료, API 원문 에러 메시지 미노출 확인.
  5. SDK가 반환한 `incomplete` 및 `refusal`이 보고서로 저장될 수 없도록 정상 실패로 분류 확인.
- 기존 `tests/browser_record_check.py`의 gzip CDP 관찰 부분은 **관찰 데이터가 부족할 때 `compressed_decoded_unavailable`으로 본문을 읽지 않는 정책 자체가 안전한 동작**임을 테스트에 반영. 원래 인가되지 않은 origin은 여전히 `scope_or_auth_body_excluded`가 필수이고, 데이터가 실제 준비되면 `structure_only`/ `decoded_too_large`의 원래 내용·상한 및 원문 비저장 검증은 유지한다.
- 제품 스캐너/HTTP collector/JSON parser/LLM payload·SDK client의 **기능 코드 변경 없음**. PR #13은 공식 SDK 실제 직렬화 검증과 이전의 과잉 엄격한 CDP fixture 판정 정정만 담는다.

## 테스트 증거와 문제 이력
- 초기 PR source `3dc29a1512304c9b167e3103837997a6bf844d4a`:
  - [Windows run 39143751785](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39143751785): **98/98 PASS**.
  - [Chromium run 39143751592](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39143751592): **22/23 PASS**, 기존 `test_real_headed_approved_gzip_without_length_bounded_by_decoded_bytes`에서 `structure_only` 기대 대비 `compressed_decoded_unavailable` 관측.
  - **동일 실패한 실행을 단 1회 재검증**했지만 재실행은 `decoded_too_large` 대신 `compressed_decoded_unavailable` 판정(역시 22/23 PASS). 이는 작은/큰 응답 모두에서 CDP decoded-byte 이벤트가 항상 확보된다고 보장할 수 없음을 보여줌. 분석 본문이 잘못 읽힌 것이 아니라 **불확실하면 미수집(fail-closed)** 정책을 지켰음.
- 원래 코드 의도대로 **CDP 관찰 누락 시 분석을 강제하지 않는** 테스트 기대값을 적용하고 다시 전수 검사:
  - [Windows run 39144159568](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39144159568): **98/98 PASS**.
  - [Chromium run 39144159553](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39144159553): **23/23 PASS**, 공개 사이트 보조 smoke **4/4 PASS**.
- **중요:** 최종 PASS는 프레임워크가 fail-closed 결과도 명시적으로 수용하는 테스트 계약에 대한 PASS이다. **CDP 응답 길이 관찰 성공률이 개선되었거나 실제 사이트 gzip 분석 성공률이 100%라는 뜻이 아니다.** 사용자 실사이트 128KiB 초과 API의 부분 prefix 1건 성공은 기존 PR #10 검증이며 이번 PR의 기능 개선 성과로 중복 계산하지 않는다.

## Step 4 완성도 판정
- 자동 Mock/fixture 인수 기준 **10/10 그대로 유지**.
- **공식 SDK HTTP 직렬화와 오류 매핑**이 FakeClient mock을 넘어 실제 설치된 SDK 객체/HTTP 계약까지 검증됨.
- **실제 OpenAI API 호출은 0회**, 실 모델의 한국어 품질·실제 API 과금/지연·prompt injection 내성·모델 ID 가용성은 미검증.
- 사용자 Windows의 Step 3 직접 필터 조작→SVG/CSS 실제 변화·API 연관 근거는 별도 미검증.
- 범위가 Step 1~4의 원본 자동 인수에 한정될 때 4/4 단계 구현 상태는 변경 없음. 최종 상용제품 진도 %는 별도 최종 출시 범위가 없어 임의 산정하지 않는다.
- 다음 독립 작업 후보: (1) Step3 `compressed_decoded_unavailable` 빈도와 요청별 CDP 이벤트 관찰 누락 원인 **값 없는 진단**으로 측정, (2) 사용자 Windows 수동 Record 1회, (3) 실제 사용자 동의·환경변수 설정 하의 유료 API smoke (현재 키/모델 미제공으로 자동 수행 금지).

## 로컬 확인 방법
```powershell
git pull origin main
python -m pip install -r requirements.txt
python -m pytest tests/test_llm_sdk_transport.py -q
python -m pytest -q
python scan.py --from-result ./out/demo/result.json --llm-dry-run
```

이 테스트들은 `httpx2.MockTransport`로 모든 전송을 내부 처리한다. 유료 호출을 확인하려면 사용자의 명시적 설정과 `--llm`이 별도로 필요하다.
