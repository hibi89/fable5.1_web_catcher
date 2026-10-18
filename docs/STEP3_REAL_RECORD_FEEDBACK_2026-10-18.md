# Step 3 실제 사용자 대시보드 Record 피드백 및 수정 (2026-10-18)

## 현장 보고서 (사용자 직접 실행; 수정 전 코드)

사용자 제공: 2026-10-18 12:29:14~12:30:01 UTC의 수동 Record report.md. 대시보드 URL과 서비스 API 주소 외 내용은 본 문서에서 비식별화한다.

- 성공: HTTPS 200, DOMContentLoaded, 기록 종료 browser_closed, 수집시간 **47.344초**.
- 관찰: 2개 XHR/fetch 이벤트(상세 1건·생략 1건), SVG/CSS bar 차트 후보 **4건**, 조작 마커 **228건**, nav 목록 **5건**.
- 관찰한 API 응답은 외부 origin n8n webhook의 200 JSON이었으며 본문은 scope_or_auth_body_excluded. 기본 허용 origin이 대시보드이므로 정상적인 범위 제한이다.
- 차트는 generic SVG와 CSS bar 패턴; 특정 라이브러리 마커·속성 갱신이 없어 **엄격한 기존 chart↔API 매핑 후보 0건**. allow-origin만으로 매핑을 보장할 수 없다.
- 동일 클릭 시각이 여러 nav 문서 ID에 재등장했다. Playwright framenavigated가 SPA hash/history 변경도 알리므로 JS 문서를 바꾸지 않았는데 문서 ID가 증가하고 이전 클릭 배열이 재수집된 버그를 **재현 fixture로 확인**했다.
- browser_closed로 종료 시 final_url이 unknown인 문제 및 같은 문서 CSS bar와 SVG가 동일 chart-001 ID를 부여받을 가능성을 수정했다.

## 수정과 검증

- PR #2: https://github.com/hibi89/fable5.1_web_catcher/pull/2 (main 병합).
- 검증 기능 SHA: **173d42d3a33d29bf80c2dc5a137daccf0992216d**.
- 병합 SHA: **b5496a61bd82d56204bdab24c984288230a95713**.
- Windows 2022 Python 3.11: run **39128145838**, 60 passed.
- Ubuntu 실제 headed Chromium + Xvfb: run **39128145939**, 19 passed (기존 16 + SPA 문서 구분/클릭 중복 방지 + final_url 보존 + 명시적 외부 origin 분석 보안 테스트 3개). 선택 공개 홈페이지 smoke 4 passed.
- 문서 ID 판정에 performance.timeOrigin을 사용하여 동일 JS 문서의 hash/history URL 변경은 하나의 문서로 취급하고 실제 새 문서만 분리한다.
- chart 후보는 구조 key에 따라 안정적·고유 ID를 부여한다. 마지막 안전 URL을 browser_closed 이후에도 보존한다.
- 프레임·응답 본문 보호 및 값 저장 금지 유지. 별도 허용 없는 외부 origin JSON은 분석하지 않는다.
- 모르는 기술/차트 연결을 강제 추측하지 않는다.

## 사용자 Windows 재시험 (아직 수행되지 않음)

로컬 폴더가 기존 Step 2 ZIP 압축 해제본일 수 있으므로 git pull 이전에 .git 존재를 확인한다. Git 복제 저장소의 최신 main을 받거나 최신 ZIP에서 수정된 파일을 사용한다.

~~~powershell
python scan.py "https://daily-dashboard-ldh-1013.clevertide128.chatgpt.site/#v-dash" --record --allow-origin "https://practice02.61-107-199-22.sslip.io" --max-duration 900 --out ./out/record-after-fix
~~~

**분석 권한이 있는 사이트에 한해서만** API origin을 추가한다. 필터/탭을 직접 조작 후 터미널 Enter를 누르거나 전체 브라우저를 종료한다. output의 report.md와 result.json에서 조작 마커·nav 구분·마스킹·API response_body_analysis·chart_candidates를 확인한다. 외부 API 구조가 허용 후에도 size_unknown/too_large 등의 조건으로 생략될 수 있다. 일반 SVG/CSS 차트는 현재 엄격한 근거 조건 때문에 매핑 0건을 유지할 수 있다.

## 검증 한계

Windows 사용자의 실제 사이트에서 수정 후 재시험은 아직 관찰되지 않았다. Chromium fixture에서는 문제를 재현해 수정 검증했지만 모든 SPA 구현·상용 인증·차트 구성에 대한 보장은 없다. 시간적 연관성만으로 인과적 데이터 연결을 확정하지 않는다.
