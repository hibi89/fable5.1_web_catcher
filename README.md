# Fable 5.1 Web Catcher — Step 1

**Python 3.11+에서 동작하는 공개 웹페이지 기술 단서 정적 분석 CLI**입니다. 읽기 전용 GET 요청으로 URL 한 페이지의 HTML과 응답 메타데이터를 조사한 뒤, 근거 기반으로 프론트엔드 / 백엔드 **추정** / 인프라·CDN 정보를 JSON과 한국어 Markdown으로 기록합니다.

백엔드 소스코드, DB, 비공개 API를 복원하는 도구가 아닙니다. 근거가 없다면 `unknown`입니다. `confidence`는 휴리스틱 점수(0–1)이며 통계적 확률이 아닙니다. 헤더와 쿠키는 변경·위조가 가능하므로 기술 확정 증거가 아닙니다.

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

정적 수집 `scanner/static_scan.py`, 규칙 판정 `scanner/fingerprints.py`, 공통 데이터 `scanner/models.py`, 보고서 `scanner/report.py`가 분리되어 있습니다. 향후 선택적 브라우저 분석 결과도 같은 스키마로 반환할 수 있으나, **현재 Playwright 실행 기반만 구현했으며, Record·LLM·웹 UI 및 API·차트 분석은 미구현입니다.**

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
`runtime.scope=navigation_only`는 **동작 기반만 구현**했다는 의미입니다.
추가된 `runtime.xhr_fetch_requests_seen`·`runtime.xhr_fetch_responses_seen`는 개수만 기록합니다.
**아직 API endpoint, JSON 구조, 차트 후보, 차트↔API 연결, 런타임 라이브러리, 번들 후보를 분석하지 않습니다.**
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
SSE, WebSocket, API/차트 수집 및 서버 측 SSRF 격리는 향후 단위의 작업입니다.


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
`api.candidates`, `api.connections`, `charts`는 아직 비어 있습니다.
WebSocket·SSE, 차트 라이브러리, 차트↔API 연관 후보, JS 번들 분석은 미구현입니다.
