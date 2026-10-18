# Fable 5.1 Web Catcher — Step 1 정적 + Step 2 런타임 + Step 3 수동 Record

**Python 3.11+에서 동작하는 공개 웹페이지 기술 단서 정적/Chromium 런타임 분석 CLI**입니다. 읽기 전용 GET 요청으로 URL 한 페이지의 HTML과 응답 메타데이터를 조사한 뒤, 근거 기반으로 프론트엔드 / 백엔드 **추정** / 인프라·CDN 정보를 JSON과 한국어 Markdown으로 기록합니다.

백엔드 소스코드, DB, 비공개 API를 복원하는 도구가 아닙니다. 근거가 없다면 `unknown`입니다. `confidence`는 휴리스틱 점수(0–1)이며 통계적 확률이 아닙니다. 헤더와 쿠키는 변경·위조가 가능하므로 기술 확정 증거가 아닙니다.

**현재 인수검사 (2026-10-18): Step 1 7/7, Step 2 9/9 PASS.** Windows 55/55, 실제 Chromium 11/11, 공개 홈페이지 정적·런타임 4/4 PASS. [Step 2 최종 수용 검사](docs/STEP2_FINAL_ACCEPTANCE.md)를 참조하세요. 기록된 연관 점수는 실제 데이터 lineage가 아닌 휴리스틱 추정입니다.

## Step 3: 수동 Record (권한 있는 사이트에서만)

Record는 새 비영구 Chromium 창을 띄웁니다. 사용자가 직접 로그인·클릭·필터 조작을 수행하는 동안 Step 2의 네트워크·차트·JS 번들 수집기를 재사용합니다. 자동 로그인·클릭·WAF 우회·세션 보존은 하지 않습니다.

Windows PowerShell (화면이 보이는 데스크톱에서 실행):

~~~powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
python scan.py "https://example.com/#dashboard" --record --out ./out/record
python scan.py "https://example.com/" --record --max-duration 900 --allow-origin https://api.example.com --out ./out/record-allowed
~~~

조작 후 원래 터미널로 돌아와 Enter를 누르면 result.json/report.md가 생성됩니다. Ctrl+C, 모든 창 종료, 시간 만료도 종료 신호입니다. --record --runtime은 브라우저 하나만 띄우고, --wait는 Record 종료에 사용되지 않습니다. 입력 URL의 origin만 기본 허용하며 --allow-origin은 경로·와일드카드 없는 정확한 origin을 반복 지정할 수 있습니다. 허용 밖 사이트로 사용자가 이동할 수는 있지만 DOM/상호작용 및 외부 API 응답 구조는 분석하지 않습니다. 인증/토큰 경로의 본문은 허용 여부에 관계없이 분석하지 않습니다.

출력 record에는 시작/종료 시간, 종료 원인, 마스킹된 문서 목록, click/change 시각·구조적 selector, 수집 한도 생략 건수가 저장됩니다. 비밀번호, 입력값, 쿠키 값, 인증 헤더, 요청·응답 원문, HAR, 스크린샷, 브라우저 세션은 저장하지 않습니다. API 경로·JSON 필드명에도 업무상 정보가 포함될 수 있으니 공유 전 점검해야 합니다.

제약: 비대화형 stdin/EOF(오류), 디스플레이 없는 환경, iframe 내부 DOM/행동 분석, 완전한 인과적 차트↔API 증명은 지원하지 않습니다. JSON 구조는 값 없는 유형 정보이며 일부 이벤트는 제한 때문에 누락될 수 있습니다. Playwright의 압축 해제 순간 메모리 절대 상한은 보장되지 않습니다.

테스트:

~~~bash
python -m pytest -q
# Linux의 실제 headed 브라우저 fixture는 가상 디스플레이 필요
xvfb-run -a python -m pytest -q tests/browser_record_check.py
~~~

Step 3 자동 fixture 검증: Windows 60/60, Ubuntu 실제 headed Chromium 16/16, 선택 공개 사이트 4/4 PASS. 사용자 Windows에서 실제 사이트 로그인·필터 변경·Enter까지의 수동 실사용 확인은 여전히 미검증입니다. 상세 근거: docs/STEP3_FINAL_ACCEPTANCE.md.

## 최종 인수 — 새 설치 및 Windows 수동 확인

새 Python 가상환경 설치 시 의존성 설치 후 **브라우저 바이너리를 별도 설치**해야 합니다.
Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m pytest -q
```

Linux CI에서는 `python -m playwright install --with-deps chromium`을 사용해 OS 라이브러리도 함께 설치합니다. 검증된 단위/브라우저/선택 외부 공개페이지 테스트는 서로 다른 실행입니다. Windows 사용자의 로그인·필터 변경을 포함한 실제 Record 확인은 [복사 가능한 최종 체크리스트](docs/WINDOWS_FINAL_CHECKLIST.md)를 참조하세요. 실제 유료 OpenAI API는 사전 승인 없이 호출하지 않습니다.

## 설치 및 실행

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scan.py https://example.com --out ./out/demo
python scan.py https://example.com --out ./out/demo --timeout 20
python -m pytest -q
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scan.py https://example.com --out ./out/demo
python scan.py https://example.com --out ./out/demo --timeout 20
python -m pytest -q
```

`--out` 생략 시 `out/YYYYMMDD-HHMMSS-마이크로초/`에 `result.json`, `report.md`를 생성합니다. 모든 실패는 부분 결과와 안전한 경고를 저장하고 exit code `2`를 반환하며, 성공/비치명적 경고는 `0`을 반환합니다. 옵션은 `python scan.py --help` 참조. 요청 시간 초과 기본 10초(연결/읽기 각각), 자동 리다이렉트 최대 5회, HTML 다운로드 최대 2,000,000바이트. HTTPS 인증서 검증 활성화.

## 수집·보안 범위

- URL 1개에 대한 **GET**만 전송 (최대 5회 리다이렉트만 추적).
- 최종 URL·HTTP 상태·리다이렉트 경로·허용 목록 응답 헤더·쿠키 이름·meta generator·script src·stylesheet href·구조적 HTML 마커·CSP 서비스 도메인을 수집.
- 출력에 `Authorization`, `Cookie`, `Set-Cookie` 값과 원본 HTML은 저장하지 않음. URL의 민감 쿼리값, userinfo, 근거 발췌 내 인증값은 마스킹/크기 제한.
- 403·429 및 봇 차단 의심 페이지는 경고. 네트워크 연결 실패 및 400 이상 응답에는 비정상 종료 코드를 반환.
- 로그인, 폼 제출, 임의 엔드포인트 프로빙, 관리자·백업·`.env` 경로 탐색, 링크 크롤링, JS 실행 **모두 없음**.
- 네트워크 접근이 사용자 입력 URL과 리다이렉트 목적지로 제한되므로 **신뢰할 수 없는 URL을 서버 내부에서 실행하지 마세요**. SSRF 차단용 보안 프록시는 포함하지 않습니다.

## 결과 스키마

최상위 키: `schema_version`, `target`, `scanned_at`, `scan_mode`, `frontend`, `backend_inferred`, `infra`, `api`, `charts`, `evidence`, `warnings`.

기술 항목은 `name`, `version`(명확할 때만), `confidence`, `evidence_ids`를 포함합니다. 근거는 `id`, `source`, `key`, `value`, `note`. 미탐지 카테고리는 `unknown`(confidence 0, 근거 없음)으로 남깁니다. `evidence_ids`는 실제 `evidence`에 존재하는 ID만 참조합니다. `scan_mode`는 `static`, `api`는 `{"endpoints":[], "candidates":[], "connections":[]}`, `charts`는 `[]`입니다.

## 규칙 파일 작성 방법

`rules/fingerprints.json`은 내부에 포함된 작은 자체 제작 규칙 파일입니다. 외부 Wappalyzer나 LLM/API 키는 불필요합니다.

```json
{
  "schema_version": "1.0",
  "technologies": [
    {
      "name": "Express",
      "category": "backend_inferred",
      "signals": [
        {
          "source": "response_header",
          "key": "x-powered-by",
          "pattern": "^Express$",
          "weight": 0.6,
          "note": "Express 헤더를 통한 추정",
          "group": "express-header"
        }
      ]
    }
  ]
}
```

- `source`: `html`(일반 본문 단어가 아닌 사전 정의된 구조적 특징), `response_header`, `cookie_name`, `script_src`, `stylesheet_href`, `meta_generator`, `csp_domain`.
- `key`: 헤더 등 딕셔너리형 자료에서는 선택적으로 필터.
- `pattern`: 대소문자 구분 없는 정규식. 구체적인 마커만 사용하고 일반 본문 키워드 탐지는 금지.
- `weight`: 0–1 단일 단서 휴리스틱 가중치. `group`의 동일 신호는 반복 횟수와 무관하게 최대 1회 계산.
- `version_pattern`: 선택 사항. 명확한 버전 문자열에서 캡처 그룹 1을 확인한 경우만 채움.
- `note`: 해당 근거의 한국어 설명. 모든 추정은 원본 관찰과 설명을 추적할 수 있음.

16개 기술 규칙: React, Next.js, Vue, Nuxt, Angular / PHP, ASP.NET, Express, Django, Laravel, Java Servlet / Cloudflare, Vercel, Netlify, nginx, Apache. nginx/Apache는 웹서버/인프라로만 처리하고, `JSESSIONID`는 Java Servlet로만 추정합니다. Next.js가 감지되어도 전체 백엔드가 Node.js라고 주장하지 않습니다.

## 오프라인 검증

`tests/fixture_server.py`는 **실제 서비스가 아닌 로컬 모의 HTTP 서버**입니다. Next.js, Java Servlet 쿠키, 일반 HTML, 403/429, 리다이렉트, 민감정보 응답 등을 제공합니다.

```bash
python -m pytest -q
```

인터넷의 특정 사이트가 특정 기술을 노출한다고 기대하지 않습니다. 성공 판정은 자체 모의 서버·스키마·마스킹·종료 코드 검증만을 기준으로 합니다.

## 자동 검증 (GitHub Actions)

`.github/workflows/windows-python311.yml`은 `main`의 소스·테스트·규칙·워크플로 변경 시와 `main` 대상 PR 또는 수동 실행 시 동작합니다. Windows Server 2022 / Python 3.11에서 새 `.venv-ci`를 만들고 `requirements.txt`를 설치한 뒤 오프라인 pytest를 실행합니다. 토큰 권한은 `contents: read`만 사용하고, 사이트 스캔·배포를 수행하지 않습니다. 한 작업의 제한 시간은 15분입니다.

2026-10-18 CI 검증: 최초 실행에서 리디렉션 stdout `cp1252`의 한글 인코딩 문제가 발견되어 수정했고, [다음 실행](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39111101377)에서 **23 passed**로 최종 검증했습니다. 한글을 표현할 수 없는 출력 스트림은 실행 중단 대신 이스케이프 문자열로 안전하게 출력합니다.

## Step 1 최종 완료 상태 (2026-10-18)

- 사용자 원문 `fable5.1_step1.txt`의 **완료 기준 7/7개 충족(100%)**. 상세 기준과 한계는 [최종 승인 체크리스트](docs/STEP1_FINAL_ACCEPTANCE.md)를 참고하세요.
- 신규 경계 회귀 테스트 3개 포함하여 **26 tests**. Windows, Ubuntu, macOS 각각 Python 3.11의 독립 새 가상환경에서 전체 통과. 기존 23 PASS 기록은 중간 검증 기록이며 최신 최종 결과는 26 PASS입니다.
- 실제 공개 홈페이지 `https://www.python.org/`와 `https://example.com/`에서 결과 파일과 schema/evidence 무결성을 확인했습니다. 특정 기술의 탐지를 성공 조건으로 요구하지 않았습니다.
- 실행: `python scan.py https://example.com --out ./out/demo` / 테스트: `python -m pytest -q`.
- 배포 및 Record·LLM·웹 UI는 여전히 범위 밖이며, Playwright 실행 기반은 Step 2 단위 1에 추가되었습니다. **Step 2 단위 1(격리 Chromium 실행 기반)은 완료했습니다. 아래 단위 1 설명 참조.**

## Step 2 확장 지점

정적 수집 `scanner/static_scan.py`, 규칙 판정 `scanner/fingerprints.py`, 공통 데이터 `scanner/models.py`, 보고서 `scanner/report.py`가 분리되어 있습니다. 향후 선택적 브라우저 분석 결과도 같은 스키마로 반환할 수 있으나, **현재 API·WebSocket·SSE·차트 DOM·보수적 차트↔API 후보·JS 번들 문자열 후보까지 Step 2 범위를 구현했습니다. Record/LLM/웹 UI는 범위 밖입니다.**

## Step 2 — 단위 1: 런타임 브라우저 실행 기반 (부분 구현)

정적 모드는 **변경 없이** `python scan.py URL --out ./out/static`으로 계속 사용합니다.
Playwright 기반 런타임 모드는 다음 명령으로 실행합니다.

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python scan.py https://example.com --runtime --out ./out/runtime
python scan.py https://example.com --runtime --headed --wait 10 --out ./out/runtime
```

`--wait`의 기본값은 10초이며 첫 DOMContentLoaded 뒤 이벤트를 처리하는 시간입니다.
격리된 Chromium context를 사용하고, 로딩 후 최대 두 번 스크롤합니다.
로그인·클릭·폼 제출·내부 링크 탐색은 수행하지 않습니다.
오류가 나면 부분 JSON/보고서를 남기고 종료 코드 2를 반환합니다.
Step 2 단위 1 당시의 `runtime.scope=navigation_only`는 실행 기반만 구현했다는 표시였습니다. 현재 값은 `network_and_connections_metadata`입니다.
추가된 `runtime.xhr_fetch_requests_seen`·`runtime.xhr_fetch_responses_seen`는 개수만 기록합니다.
단위 1 당시에는 API·차트 분석이 미구현이었습니다. 현재는 단위 1~6 및 Step 2 최종 인수검사를 완료했으며 아래 단위별 설명은 개발 이력입니다.
따라서 이번 단위 결과를 Step 2 완료라고 해석하지 마세요.

테스트는 두 종류로 구분합니다.

```bash
python -m pytest -q
python -m pytest -q tests/browser_runtime_check.py
```

두 번째 명령은 Chromium이 설치된 환경에서만 동작하는 **로컬 fixture의 실제 브라우저 통합 테스트**입니다.
전용 GitHub Actions `.github/workflows/runtime-python311.yml`에서도 별도로 실행합니다.
`--headed`는 화면 표시가 가능한 환경에서만 사용하세요.
Chromium 실행이 실패하면 `python -m playwright install chromium`을 확인하세요.
SSE/WebSocket/API는 단위 2~3, 차트 DOM 후보는 단위 4에서 구현했습니다. SSRF 격리는 아직 미구현입니다.


## Step 2 — 단위 2: 관찰된 XHR/fetch 메타데이터

`--runtime`은 이제 브라우저 탐색 전 요청/응답 이벤트 리스너를 설치하고,
페이지가 **실제로 요청한** fetch/XHR만 `api.endpoints`에 기록합니다.
요청별 `id`, 마스킹된 `url`, `method`, `resource_type`,
`request_started_at_ms`, `response_received_at_ms`, `status`,
`content_type`, `graphql_candidate`, `json_structure`, `response_body_analysis`을 저장합니다.
GraphQL은 관찰된 URL 경로나 콘텐츠 유형에 근거한 **후보**일 뿐 자동 introspection하지 않습니다.

JSON 본문은 값·원문을 저장하지 않고 필드 이름/자료형만 요약합니다.
**응답에 Content-Length가 명시되고 128 KiB 이하이면서 종료된 JSON** 중
최대 20개만 처리합니다. 응답 크기가 불명확하거나 초과하면 해당 endpoint는
보존하면서 본문 요약은 건너뜁니다. 전체 XHR/fetch 기록은 최대 150건,
JSON 중첩 5단계, 객체 키 24개, 배열 표본 3개로 제한합니다.
요청 body, 인증 헤더, Cookie, HAR, 원본 응답 body, storage state를 저장하지 않습니다.
브라우저 내부 디코딩 과정에서 순간적으로 128 KiB를 넘는 메모리 사용이
발생할 수 있으며 **완전한 메모리 상한은 보장되지 않습니다**.
브라우저에서 응답 완료 후 body를 읽기 때문에 끝나지 않는 스트림은 읽지 않습니다.

오프라인 단위 테스트: `python -m pytest -q tests/test_network.py`
(일반 전체: `python -m pytest -q`).
실제 Chromium fixture: `python -m pytest -q tests/browser_runtime_check.py`.
단위 5에서는 근거가 유일할 때만 api.chart_candidates와 charts[].data_sources에 연관 후보를 기록하며, 근거가 부족하거나 경쟁 응답이 있으면 빈 배열입니다.
WS/SSE 단위 3, 차트 DOM 단위 4, 차트↔API 연관 단위 5, JS 번들 문자열 단위 6까지 구현했습니다.

## Step 2 — 단위 3: WebSocket·SSE 연결 관찰

런타임 실행에서 실제 WebSocket과 text/event-stream SSE 응답을 api.connections에 기록합니다.
WebSocket의 마스킹 URL·관찰 시각·송수신 프레임 개수, SSE의 마스킹 URL·상태·MIME·시각을 저장합니다.
프레임 원문, SSE 데이터, 인증 헤더나 쿠키는 읽거나 저장하지 않습니다.
연결 60건, 프레임 카운트 방향별 1,000,000 상한이 있습니다.
SSE 요청 종료를 기다리지 않으며 networkidle도 사용하지 않습니다.
WebSocket/SSE는 로컬 fixture 및 실제 Chromium 테스트로 검증합니다.

```bash
python -m pytest -q tests/test_connections.py
python -m pytest -q tests/browser_runtime_check.py
```

차트 DOM은 단위 4, 연관 후보는 단위 5, 번들 문자열은 단위 6에서 구현했습니다.

## Step 2 — 단위 4: 런타임 기술·차트 DOM 후보

런타임 실행은 페이지 이동 이전에 DOM 관찰기를 설치하고 초기 SVG/canvas 및 추가 노드와 관련 속성 변경을 관찰합니다.
Next.js/Nuxt 및 Highcharts, Chart.js, ECharts, Plotly, ApexCharts, D3의 알려진 속성만 읽습니다.
로드된 라이브러리와 관찰된 인스턴스 개수는 다르게 기록하며, 버전은 검증 가능한 공개 속성에서만 수집합니다.
charts에는 구조적 selector, 최초 등장 시각, 속성 갱신 관찰 시각, confidence, 라이브러리 근거, data_sources 빈 목록을 보관합니다.
일반 canvas/svg는 confidence 0.2의 후보이지 실제 차트 확정이 아닙니다. D3 존재도 차트 존재를 증명하지 않습니다.
DOM 최초 등장 시각은 렌더 완료가 아니며 MutationObserver는 canvas 픽셀 변경을 감지할 수 없습니다.
후보 80개, mutation 이벤트 1200개 상한. 속성이나 DOM에서 사용자 데이터/비밀값은 저장하지 않습니다.
Unit tests: python -m pytest -q tests/test_runtime_detect.py
Chromium fixture: python -m pytest -q tests/browser_runtime_check.py
라이브러리 전역은 테스트용 stub으로 검증했습니다. 실제 배포 라이브러리 통합 테스트는 별도입니다.
차트↔API 후보 점수는 단위 5, JS 번들 문자열 탐지는 단위 6에서 구현했습니다.

## Step 2 — 단위 5: 차트↔API 연관 후보

차트 라이브러리 DOM 마커, 응답이 완료된 2xx JSON의 시간·수치형 시계열 구조, 응답 후 최대 1200ms 이내 DOM 속성 갱신을 함께 확인합니다. 단순 시간 일치나 일반 SVG/canvas는 연결하지 않으며 동등한 적격 API가 2개 이상이면 연결을 보류합니다.

api.chart_candidates에는 chart_id, endpoint_id, candidate_only 상태, 비확률적 confidence(0.55~0.65), 근거 및 한계를 보관합니다. charts[].data_sources는 후보 endpoint ID를 가리킵니다. 실제 데이터 연결의 증명이 아니며 반복 일관성도 검증하지 않았습니다. 추가 API 호출이나 원본 응답 저장은 없습니다.

테스트: `python -m pytest -q`와 `python -m pytest -q tests/browser_runtime_check.py tests/browser_mapping_check.py`. 번들 단서 및 전체 Step 2 검증은 이후 별도 단위입니다.

## Step 2 — 단위 6: 이미 로드된 JS 번들의 미검증 API 문자열 후보

브라우저가 실제로 로드한 **같은 출처**의 JavaScript 응답 중 MIME/상태/Content-Length와 requestfinished가 확인된 응답만 분석합니다. 새로운 요청·경로 탐색은 실행하지 않습니다. JS 파일당 128KiB, 최대 10개 파일/스크립트별 15개 및 전체 30개 후보로 제한합니다. 크기 불명·미완료·교차 출처 JS는 본문을 읽지 않습니다.

짧고 제한된 따옴표 문자열 중 API/GraphQL 경로만 추출해 query/민감 경로를 버리고 `api.candidates`에 source_script, discovered_by=bundle_string, `unverified_string_literal`/observed_request=false로 저장합니다. 실제 `api.endpoints`의 관찰 결과와 다르며, JS 문자열이 실제 사용된 API를 의미하지 않습니다. 원본 JS·코드 스니펫·쿼리 비밀값은 저장하지 않습니다. 압축 응답 처리의 메모리 절대 상한은 보장하지 못합니다.

테스트: `python -m pytest -q` 및 `python -m pytest -q tests/browser_runtime_check.py tests/browser_mapping_check.py tests/browser_bundle_check.py`. 최종 통합/보안 fixture 검증과 공개 홈페이지 구조 검사까지 통과했습니다. 개인 Windows PC/모든 실사이트 탐지 정확도는 별도 미검증 한계입니다.

## 최신 Step 2 결과 스키마 요약

- `api.endpoints`: 실제 관찰된 XHR/fetch 요청/응답의 마스킹 메타데이터 및 값 없는 JSON 구조
- `api.connections`: 실제 관찰 WebSocket/SSE 연결 메타데이터
- `api.candidates`: 이미 로드된 동일 출처 JS 문자열의 **미검증** API 경로 (`source_script`, `discovered_by=bundle_string`)
- `api.chart_candidates`: 차트와 API의 **연관 후보** (`chart_id`, `endpoint_id`, `confidence`, `reasons`, `limitations`)
- `charts[].data_sources`: 연관 후보의 endpoint ID, 실제 데이터 흐름 확정 아님

최종 검사 명령: `python -m pytest -q`; Chromium fixture는 `python -m pytest -q tests/browser_runtime_check.py tests/browser_mapping_check.py tests/browser_bundle_check.py tests/browser_final_check.py`. 별도 공개 URL smoke는 `python -m pytest -q -s tests/public_runtime_smoke.py`이며 네트워크 의존으로 CI에서는 비필수입니다.

## Step 2 실사이트 정확도 개선 사례 (2026-10-18)

대상: https://daily-dashboard-ldh-1013.clevertide128.chatgpt.site/#v-dash

- Chromium에서 처음 발견된 일반 SVG 후보 14~15건에는 작은 아이콘이 섞여 있었음. 보이는 크기와 도형 수를 추가 확인한 결과, 최종 차트 후보는 3건(큰 SVG 2, CSS 막대 그룹 1)으로 감소.
- CSS로 표현된 반복 퍼센트 높이 막대 그룹을 낮은 신뢰도의 시각화 후보로 탐지. 이 근거는 실제 차트 라이브러리나 데이터 소스를 확정하지 않음.
- SPA URL의 해시(#v-dash)는 --runtime 브라우저 탐색에 전달하되 결과 파일에는 기록하지 않음.
- 검증: Windows 57/57 PASS, 실제 Chromium 통합 12/12 PASS, 실사이트 분석 HTTP 200/경고 0.
- 상세 진단: docs/DASHBOARD_LIVE_ACCURACY_2026-10-18.md
- 사용자 Windows에서 새 코드를 내려받은 뒤 재실행하는 검증은 별도이며, 실사이트 전체 차트 탐지율을 수치화한 것은 아님.

실사이트 실행:
    python scan.py "https://daily-dashboard-ldh-1013.clevertide128.chatgpt.site/#v-dash" --runtime --wait 10 --out ./out/dashboard-test


## 2026-10-18 실제 대시보드 Record 재검수 (PR #2 반영)

수동 Record 보고서(47.344초)에서 화면 전환 후 동일 클릭이 여러 navigation ID에 다시 기록되고, 전체 브라우저 창을 닫으면 final_url이 unknown으로 표시되는 문제가 발견되었습니다. 현재 main에서는 SPA의 hash/history 변경을 같은 JS 문서로 구분하고, 클릭 중복·차트 후보 ID 충돌·종료 시 최종 URL 미기록을 수정했습니다. Windows 60/60, 실제 headed Chromium 19/19, 선택 사이트 4/4 테스트 PASS. 자세한 근거는 docs/STEP3_REAL_RECORD_FEEDBACK_2026-10-18.md.

원본 대시보드가 호출한 n8n 웹훅은 **다른 origin**입니다. 기본 정책에서는 응답 JSON을 분석하지 않습니다. 해당 서비스를 분석할 권한이 있을 때만 다음처럼 추가 허용하세요:

~~~powershell
python scan.py "https://daily-dashboard-ldh-1013.clevertide128.chatgpt.site/#v-dash" --record --allow-origin "https://practice02.61-107-199-22.sslip.io" --max-duration 900 --out ./out/record-after-fix
~~~

브라우저에서 직접 탭·필터를 변경한 뒤 터미널 Enter를 누르세요. 브라우저 종료 역시 정상 종료 조건입니다. 사용자 로컬 폴더가 Git 복제가 아닌 다운로드 ZIP이면 git pull은 실패하므로, 먼저 .git 여부를 확인하고 GitHub 최신 main ZIP을 별도 폴더에 압축 해제하세요. 리포트에 0건 차트↔API 후보가 나와도 곧바로 오류는 아닙니다. CSS bar/일반 SVG와 해당 JSON 사이의 자료 흐름은 확인된 근거 없이 연결하지 않습니다.

## Step 3 Record: 응답 크기 헤더가 없는 JSON 분석 (2026-10-18)

승인한 정확한 API origin에서 수집되는 JSON 응답이 `Content-Length`를 제공하지 않아 `size_unknown`으로 제외되던 경우, **Record 모드에 한해** 요청이 완료된 후 브라우저가 측정한 응답 본문 전송 크기를 확인합니다. 비압축 응답이고 크기가 128KiB 이하라면 JSON 자료형 구조만 분석하며, 값이나 원본 응답은 저장하지 않습니다. 크기 미확인·초과 및 미확인 길이의 압축 응답은 차단합니다. 본문을 읽은 뒤 실제 크기도 재검사합니다.

이 정책은 `--record`에서만 적용되고 기존 `--runtime`의 `size_unknown` 정책은 유지됩니다. 외부 API는 권한 있는 origin을 `--allow-origin`으로 명시해야 합니다. 실제 실사이트 분석 성공과 차트↔API 연결은 별도 확인이 필요합니다. Playwright 본문 디코딩 과정의 메모리를 절대 상한으로 제한한 기능은 아닙니다. 변경/보안/테스트 근거: `docs/STEP3_HEADERLESS_JSON_BOUND_2026-10-18.md`.

## Step 3 Record: 헤더 없는 압축 JSON의 안전한 크기 판정 (2026-10-18)

Playwright `--record`로 수동 탐색 시 승인한 정확한 `--allow-origin`의 JSON 응답에 `Content-Length`가 없고 `gzip`/`br` 압축돼 있으면, CDP에서 관찰한 압축 **해제 후 바이트 수**가 128KiB 이하인 경우에만 기존 값 없는 필드/타입 구조 분석을 수행합니다. 실제 body를 읽은 후에도 측정 길이·상한을 검증합니다. 128KiB 초과, 불완전한 CDP 데이터, 중복 요청 등은 본문을 읽지 않고 수집 제한 사유를 기록합니다.

이 기능은 Step 3에만 적용하며 Step 1/2 원래 정책은 유지됩니다. Chrome 자체에서 웹페이지의 모든 압축 응답을 메모리에 해제하는 현상을 막는 절대 메모리 제한 기능은 아닙니다. 특정 실제 데모사이트의 API는 디코딩 크기가 128KiB 초과하여 현재 `decoded_too_large`이고, 본문 구조 미수집이 정상입니다. 상세 근거 `docs/STEP3_COMPRESSED_JSON_DECODED_BOUND_2026-10-18.md`.

## Step 3: 128KiB 초과 JSON의 제한된 부분 구조 힌트

승인된 `--record` XHR/fetch JSON 응답의 디코딩 전체 크기가 128KiB를 초과하면 전체 본문을 분석하지 않는 기존 정책을 유지합니다. 대신 Chromium CDP로 수신 시점의 첫 **최대 32KiB**를 일시적으로 관찰하고 그 안에 **완전하게 닫힌 첫 JSON 객체**가 있으면 키 이름과 타입만 `json_prefix_structure`에 기록합니다. `completeness=partial_prefix_only`이므로 전체 JSON 스키마나 차트/API의 인과 관계를 증명하지 않습니다. 응답 본문 값은 저장하지 않고, 로그에 실제 필드명을 출력하지 않습니다. 최대 20개 스트림/10개 부분 힌트 상한이 적용됩니다. CDP의 브라우저 내부 메모리를 절대 제한하는 기능은 아닙니다.

관련 근거와 테스트: `docs/STEP3_PARTIAL_LARGE_JSON_PREFIX_2026-10-19.md`.

## Step 4 — 사용자가 명시적으로 켜는 OpenAI 보고서

Step 1~3 스캔은 **OPENAI_API_KEY 없이 종전처럼 동작**합니다. API 키가 환경변수에 존재해도 `--llm`을 쓰지 않으면 모델 API를 호출하지 않습니다. Step 4는 기존 스캔의 서버 내부 코드/DB/원본 페이지를 알아내는 기능이 아니라 **값 없는 관찰 근거만 재해석**하는 선택적 보고서입니다.

### 설치 및 설정 (PowerShell)

```powershell
python -m pip install -r requirements.txt
# Step 2/3 Chromium이 필요한 경우: python -m playwright install chromium
$env:OPENAI_API_KEY = "본인_API_키"   # 파일/저장소에 쓰지 말고 실제 실행 환경변수로만 지정
$env:OPENAI_MODEL = "본인_계정에서_사용_가능한_정확한_모델_ID"
```

모델을 코드에서 추측하거나 자동으로 기본 지정하지 않습니다. 실제 모델 ID는 계정의 API 사용 권한과 공식 지원 모델 목록을 확인하세요. OpenAI API는 ChatGPT 구독과 과금이 별도일 수 있습니다. 모델별 비용/토큰은 실행 환경과 가격 정책에 따라 달라지므로 고정 가격을 약속하지 않습니다.

### 먼저 dry-run으로 전송 자료 검토 (API 비용 0)

```powershell
python scan.py "https://본인이-검사할-사이트" --out ./out/demo
python scan.py --from-result ./out/demo/result.json --llm-dry-run
notepad ./out/demo/llm_payload.preview.json
```

`--llm-dry-run`은 로컬에서 동일한 payload builder를 이용해 `llm_payload.preview.json`을 생성하며 **OpenAI API/외부 서비스 호출 0회**입니다. 미리보기에서 호스트명·사람 이름·이메일·경로·JSON 키가 충분히 익명화됐는지 직접 확인하세요. 프로그램의 정규식·허용목록만으로 모든 개인/기업 비밀이 익명화됐다고 보장할 수는 없습니다.

### 명시적 호출

```powershell
python scan.py "https://본인이-검사할-사이트" --runtime --llm --model "실제_MODEL_ID" --out ./out/demo
python scan.py "https://본인이-권한을-보유한-사이트" --record --llm --model "실제_MODEL_ID" --out ./out/demo
python scan.py --from-result ./out/demo/result.json --llm --model "실제_MODEL_ID"
```

`--record`를 사용하면 사용자가 로컬 Chromium에서 직접 클릭·로그인·필터 변경하고 종료해야 합니다. 직접 로그인 입력이나 쿠키 원문은 모델에 보내지 않습니다.

### 외부 전송 범위 / 한계

- 허용하는 것: **로컬 규칙 엔진의 기술명/휴리스틱 점수**, 마스킹·제한된 evidence ID/구조적 단서, 호스트 대신 `origin_1` 등의 별칭으로 표현된 API 경로, HTTP method/status/content-type, 값 없는 JSON 필드 자료형 구조, 차트 타입 및 이미 관찰된 연관 후보, 생략/경고 개수, 시각 차이.
- 전송하지 않는 것: 원본 result.json, HTML/JS, 쿠키와 인증값, response.body, 폼값, 사용자 조작 원문, 로그인/세션, 원래 URL의 host/query/fragment, 임의 이름·전화번호·이메일·개인 식별 가능한 JSON key 및 비신뢰 경고 원문.
- 35개 기술에 대한 50개 독립 규칙 신호를 사용하며 헤더/쿠키/메타/자산 경로는 **구현 확증이 아닌 관찰 단서**입니다. 규칙 ID와 검증 메모, 양성/음성 테스트를 `rules/fingerprints.json`에서 확인할 수 있습니다. `JSESSIONID`는 Servlet 계열, `csrftoken`은 Django 후보, `connect.sid`은 Express 확정 아님. 서버/CDN 헤더는 앱 백엔드/DB를 증명하지 못합니다.
- 전송 데이터는 근거 최대 45, 탐지 결과 35, API 24, 차트 16, 차트↔API 후보 20, 총 28KiB 제한. 부족한 근거는 생략 건수로 표시하며 일부 자료로 판단했음을 명시합니다. 정확한 토큰 수는 SDK의 실제 usage가 반환된 경우에만 기록합니다.
- 웹페이지의 문자열은 비신뢰 입력으로만 제공하며 모델에 tools/file/network 기능을 연결하지 않습니다. 검증되지 않은 모델의 추측, 새 기술/버전/불확실한 참조는 로컬 검증에서 차단하도록 노력하지만 **모든 환각/프롬프트 주입을 탐지한다고 보장하지 않습니다**.
- 모델 응답은 JSON schema로 수신한 뒤 로컬에서 참조 ID·문자 길이·추가 필드를 검증합니다. 최종 Markdown은 로컬이 작성하며 원 사이트의 사용 기술과 새로운 재구현 추천을 분리합니다. **매핑은 끝까지 연관 후보이며 인과적 데이터 흐름 확정이 아닙니다.**

### 산출 파일과 실패 처리

기존 `result.json`, `report.md`는 절대 덮어쓰지 않습니다. Step 4가 성공하면 `llm_report.json`(생성 시각, 선택 모델, prompt/payload 버전, 원본 hash, SDK 실제 usage, warnings, 검증된 분석), `llm_report.md`(7개 한국어 섹션)를 별도로 생성합니다.

모델 미지정·API 키 없음·401/403 인증·400/404 모델·스키마 설정·429 한도·서버 5xx·타임아웃·모델 거절·잘린 응답·JSON/ID 검증 실패를 구별해 안내합니다. **429/5xx만 최대 1회 자체 재시도**하고 공식 SDK 자동 재시도를 사용하지 않습니다. 모델 오류나 인증 실패 때는 기존 `report.md`를 보세요. 종료 코드는 기존 스캔 성공 0 / 스캔 자체 오류 2 / LLM 후처리 오류 3입니다.

`pytest -q`는 실제 유료 API를 절대 호출하지 않는 **mock/fixture 테스트**입니다. **실제 OpenAI API smoke는 별도 opt-in**으로 사용자 본인 키·모델 지정과 `--llm` 호출 시에만 수행하며 사용량에 따른 비용이 발생할 수 있습니다. 자동 CI에서는 실제 API 키를 주입하지 않습니다.

**Step 4 기능은 프런트엔드 복제·웹 UI·자동 코드 생성이 아닙니다.** DB/서버를 실제 조사했다고 주장하지 않으며, 프리랜서 재구현 제안은 원사이트 기술과 엄격히 분리합니다.


## Step 5 — URL 배치 / 저장 결과 비교 / 관찰 기반 데이터 계약

Step 5는 기존 Step 1~4 스캔·규칙·보고서 구조를 재사용하는 **로컬 CLI 확장**입니다. 웹 UI, DB, Docker, 큐 서버, 병렬 실행, 자동 로그인/인증 우회는 포함하지 않습니다. **배치·비교·계약 생성은 LLM API를 호출하지 않습니다.** 본인 소유 또는 분석 권한이 있는 공개 URL만 사용하세요.

### 1) UTF-8 URL 목록 순차 배치

`urls.txt` 파일:
```text
# 분석 권한이 있는 사이트만
https://example.com
https://example.org/dashboard
https://example.net/docs
```

실행:
```powershell
python scan.py --batch urls.txt --out ./out/batch
python scan.py --batch urls.txt --runtime --wait 10 --out ./out/batch-runtime
python scan.py --batch urls.txt --delay 3 --max-urls 50 --out ./out/batch-other
```

- 한 번에 **1 URL**씩, 기본 URL 사이 2초 간격(최소 1초), 고유 URL 상한 기본 50·설정 최대 500. HTTP/HTTPS만 허용. fragment는 비교 키에서 제외하되 path/query의 원래 내용과 순서는 메모리에서만 유지합니다. 민감 쿼리/내부 host/path는 manifest·요약·개별 보고서에 일반화합니다. 상세 URL 식별이 필요한 경우 사용자가 원본 입력 파일에서 확인합니다.
- `--batch --record`, `--batch --llm`, `--batch --llm-dry-run`, `--batch --allow-origin`은 **명확한 오류**입니다. 각 runtime URL은 기존 `scan()`의 새로운 격리 Chromium 실행을 사용하며 쿠키/세션을 공유하지 않습니다.
- `batch_manifest.json`, `batch_summary.json`, `batch_report.md`, `targets/001-site/result.json`, `targets/001-site/report.md` 등을 만듭니다. 폴더명과 식별번호에 원본 사이트 이름·쿼리·식별자 값을 쓰지 않습니다. 정상/경고 포함 부분 성공/실패/중단/같은 origin 429 이후 skipped를 구별합니다.
- 각 대상 전후 상태를 임시 파일+atomic replace로 저장합니다. **기존 폴더를 덮어쓰지 않습니다.** Ctrl+C 시 현재 대상 interrupted/나머지 pending, 기존 성공 결과를 보존합니다. 자동 resume은 지원하지 않습니다. 실패/잘못된 입력이 하나라도 있으면 종료코드 2, 모두 성공(비치명적 경고 포함)이면 0, 사용자 중단은 130입니다.
- 403/429 우회나 공격적 재시도는 없습니다. **429 이후 같은 origin의 후속 URL은 건너뜁니다.** 서버별 Retry-After 값을 추가 네트워크 호출로 조사하지 않습니다.
- 보안 강화로 배치 폴더의 개별 결과는 원래 Step 1~4 `result.json`보다 더 많은 필드·원문을 숨깁니다. 폴더의 익명화한 `result.json`은 일반 보고·기초 비교용이며 정확한 서버 URL이나 원본 근거를 복원하기 위한 용도가 아닙니다. 원래 스캔의 권한 범위와 한도는 보존합니다.

### 2) 두 저장된 결과 비교 (네트워크/LLM 0회)

```powershell
python scan.py --compare old/result.json new/result.json --out ./out/diff
```

`diff.json`, `diff.md`에 기술(카테고리/버전/confidence/근거 소스), 요청 method+origin+일반화 path, JSON 타입/구조, 차트 라이브러리/개수/연관 후보 수와 수집 범위 경고를 기록합니다. 시간, evidence ID, 차트 selector/id와 배열 순서의 차이만으로 변경되었다고 판정하지 않습니다.

- 같은 대상이면 **'이번에 관찰되지 않음'**이고 실제 삭제가 아닙니다.
- 다른 대상이면 **'A에만/B에만 관찰'**로 표시하며 시간 변화 표현을 피합니다.
- 익명화된 원본/구버전 필드 누락 등으로 동일 대상 판정이 불확실하면 unknown 처리합니다.
- 같은 원래 origin 이외의 API를 경로가 비슷하다는 이유로 합치지 않습니다. 동적 id를 일반화하면서 경로가 충돌하면 ambiguous로 표시합니다. 관찰된 JSON 차이는 공식 서버 breaking change 확증이 아닙니다.

### 3) 이미 관찰한 JSON 구조 → 참고 데이터 계약

```powershell
python scan.py --from-result ./out/demo/result.json --export-contracts
python scan.py --from-result ./out/demo/result.json --export-contracts --out ./out/separate-contracts
```

기본 출력: `./out/demo/contracts/contracts.json`, `contracts.md`, `contracts/schemas/endpoint-001.schema.json` 등. **새 API 요청·원본 값 복원·LLM 호출 없음.** JSON Schema Draft 2020-12의 관찰 기반 참고 스키마를 만듭니다.

- status/content-type별로 다른 variant를 보존하고, 동일 variant의 기존 JSON 구조 표본만 값 없이 병합합니다. 타입 충돌은 `anyOf`, null 별도 타입, 빈 배열/요소 미관찰은 `items: {}`. 필드 존재 빈도를 확인할 수 없는 기존 결과는 `unknown`.
- `required`, `additionalProperties:false`, 실제 값 기반 `enum/default/examples`, 정당화되지 않은 숫자 범위·날짜 형식·단위를 생성하지 않습니다. 128KiB 크기 제한으로 미분석된 응답이나 부분 prefix는 전체 서버 스키마로 승격하지 않습니다.
- `contracts.md`는 후보 배열 데이터 경로/문자열·수치·시간 이름 후보만 표시하며, 실제 범주 의미나 x/y 축·단위·집계 방식을 확정하지 않습니다.
- 결과 파일 최대 6MB, `schema_version=1.0` 또는 버전 없는 구형 출력만 수용합니다. 지원하지 않는 버전과 이미 있는 출력 폴더는 명시적으로 오류 처리합니다.

### Step 5 로컬 검사 및 알려진 한계

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
python -m pytest -q tests/test_batch.py tests/test_compare.py tests/test_contracts.py
```

배치 기능은 각 사이트에 실제로 연결되므로 허가된 URL에서만 실행하세요. 비교/계약 기능은 디스크의 두 결과만 처리하며 외부 네트워크를 사용하지 않습니다. 기존 JSON 구조 요약 자체가 제한된 표본이므로 실제 API의 `required`/validation/호환성은 알 수 없습니다. 개인정보를 정규식만으로 완벽히 익명화한다고 보장하지 않으며, 민감 자료를 외부 공유하기 전 확인하세요. Step 3의 CDP 이벤트 수집 성공률 문제 및 Step 4의 실제 유료 OpenAI 호출 미검증은 별도로 유지됩니다.
