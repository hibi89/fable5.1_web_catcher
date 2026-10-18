# Windows 최종 수동 검증 체크리스트 (사용자 로컬, Step 3 Record)

**목표**: 실제 수동 로그인/탭·날짜 조작으로 API 요청과 차트 DOM 변화가 관찰 가능한지 확인합니다. 이 과정은 GitHub CI에서 재현할 수 없으므로 사용자가 직접 실행해야 합니다. 자동 로그인, 클릭 우회, 고객 계정 정보 전달은 필요하지 않습니다.

## 0. 설치 및 기본 확인

PowerShell에서 **프로젝트 복제 폴더**로 이동한 상태에서 아래를 실행합니다.

```powershell
git pull origin main
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m pytest -q
```

기대 결과: Python 의존성과 Chromium 설치 성공, 기본 오프라인/fixture 테스트 통과. 실패하면 새 가상환경 사용 여부, Python 버전(3.11 이상)과 오류 종류를 확인합니다. 원본 오류 로그에 로컬 경로나 토큰이 있으면 그대로 공유하지 마세요.

## 1. 수동 Record 시작

다음 **본인에게 분석 권한이 있는 사이트 URL**로 교체합니다. 아래 예시 사이트는 사용자가 직접 바꿀 표시 자리이며 실제 사이트에 대한 접근을 요청하지 않습니다.

```powershell
.\.venv\Scripts\python.exe scan.py "https://YOUR-AUTHORIZED-SITE.example/" --record --out .\out\final-record --max-duration 900
```

기대 결과: 로그인 상태를 저장하지 않는 별도 headed Chromium 창이 열립니다. 프로그램이 조작 이벤트/허용 origin의 API 응답 구조/차트 구조를 메모리에서 수집합니다.

대시보드 데이터 API의 **별도 origin을 사용하고 분석 허가가 있는 경우에만**, 실행 전에 실제 origin을 정확히 확인하고 아래와 같이 추가할 수 있습니다. 허용하지 않은 origin의 응답 본문은 분석하지 않습니다.

```powershell
.\.venv\Scripts\python.exe scan.py "https://YOUR-AUTHORIZED-SITE.example/" --record --allow-origin "https://YOUR-AUTHORIZED-API.example" --out .\out\final-record-api --max-duration 900
```

> 기존 `out\final-record` 폴더가 있으면 이전 산출물을 먼저 본인이 별도 보관한 후 **새 이름으로 실행**하세요. 인증·쿠키·사용자 입력은 전달하지 마세요.

## 2. 직접 브라우저 조작

1. 로그인 과정이 필요한 사이트라면 **본인 브라우저 창 안에서 직접** 로그인합니다. 비밀번호/OTP/세션값을 ChatGPT에 제공하지 않습니다.
2. 데이터가 표시되는 대시보드 탭을 선택합니다.
3. 탭 또는 기간/날짜 필터를 적어도 한 번 변경하고 차트가 바뀌는지 눈으로 확인합니다.
4. 조작 후 2~3초 정도 데이터 로딩이 완료되는지 확인합니다.
5. 원래 **PowerShell 터미널에서 Enter**를 눌러 Record를 정상 종료합니다.

기대 결과: `out\final-record\result.json` 및 `out\final-record\report.md` 생성. `record.interactions`는 실제 클릭/변경 이벤트를 관찰한 경우에만 기록됩니다. API와 차트가 모두 보이더라도 **API→차트 인과관계의 자동 확증은 아닙니다**.

## 3. 저장 결과 개수·상태 확인

민감 URL/JSON 필드명을 콘솔에 출력하지 않고 **건수만** 확인합니다.

```powershell
.\.venv\Scripts\python.exe -c "import json; p=json.load(open(r'out\final-record\result.json', encoding='utf-8')); api=p.get('api',{}); rec=p.get('record',{}); print('API',len(api.get('endpoints',[])),'CHART',len(p.get('charts',[])),'CANDIDATE',len(api.get('chart_candidates',[])),'INTERACTION',len(rec.get('interactions',[])),'WARNINGS',len(p.get('warnings',[])))"
```

기대 결과: API/CHART/INTERACTION 값이 관찰된 작업에 따라 0보다 클 수 있습니다. `CANDIDATE=0`도 **유효한 미검증 결과**입니다. 시간 근접 또는 구조 미검증 시 잘못된 API↔차트 매핑을 억지로 만들지 않습니다. 필터 조작이 네트워크를 실제 발생시키지 않거나 로그인이 다른 origin에서 수행되면 관찰 수가 적을 수 있습니다.

## 4. 실패 시 확인할 위치와 전달 가능 정보

- CLI 시작 오류/브라우저 미설치: **PowerShell의 오류 유형**, Python/Playwright 버전, 종료 코드. 키·호스트·로컬 개인 경로는 지운 뒤 공유.
- 브라우저 닫힘/조작 수 미관찰: `out\final-record\result.json`의 `record.stop_reason`, `record.omitted_events`, `warnings` **오류 종류만** 확인.
- API 수집 미확인: `result.json`의 `api.endpoints[*].response_body_analysis` 종류와 개수, `cdp_decoded_diagnostic` 종류와 개수만 확인. 본문이나 endpoint URL·JSON 필드명 공유 금지.
- 차트 후보 미확인: `result.json`의 `charts` 수와 각 후보의 `detection_level`·`change_evidence` **분류 값만** 확인.
- 후보가 있더라도 실제 필터 변경이 원인이라고 단정하지 말고, 사용자가 눈으로 확인한 UI 결과와 비교해 수용 여부를 결정합니다.

**공유 금지:** 로그인 ID/비밀번호, API 키, 쿠키, 인증 헤더, 접근 토큰, OTP, 실제 고객사 원본 데이터, 민감 URL/JSON 필드명, 개인 사용자 폴더 경로. `result.json`/ `report.md` 원본을 그대로 외부에 공유하지 마세요.

## 5. Step 4 API 없는 dry-run

이미 생성된 `result.json`만 사용하여 외부 전송 예정 형식을 로컬 미리보기로 확인할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe scan.py --from-result .\out\final-record\result.json --llm-dry-run --out .\out\final-llm-preview
```

기대 결과: `out\final-llm-preview\llm_payload.preview.json` 생성. **실제 OpenAI API 호출 0회**, 계정/API 키 필요 없음. 형식/마스킹 검토 전 `--llm` 호출은 하지 않습니다. 실제 유료 API 연동은 별도 승인을 받아야 합니다.
