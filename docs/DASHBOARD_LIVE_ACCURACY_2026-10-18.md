# Step 2 실사이트 정확도 검증 1호 — 젤네일 인사이트 대시보드

검증일: 2026-10-18 KST.
대상: https://daily-dashboard-ldh-1013.clevertide128.chatgpt.site/#v-dash
범위: 공개 페이지의 읽기 전용 Chromium 구조 검사 및 Fable CLI 결과 비교.
최종 GitHub Actions 실사이트 진단: run 39123343463 (소스 b7c707386034a14c44820709b4a13388dfcf7e7e).
기존 Chromium 전체 회귀: run 39123322129 **12/12 PASS**, Windows: run 39123343492 **57/57 PASS**.

## 최초 문제 및 근거
- 실제 페이지 HTTP 200, XHR/fetch 2건, 알려진 차트 라이브러리 전역 0건.
- Fable 일반 SVG/canvas 차트 후보 14~15건(아이콘 다수 포함).
- 독립 Chromium DOM: SVG 11개, canvas 0개. 18~60px 작은 SVG 다수와 472×168 큰 SVG, 138×138 SVG.
- CSS 막대 그래프: 438×105 크기 bars 컨테이너에 bar 요소 13개, 가변 높이 퍼센트 스타일 사용. 기존 SVG/canvas 감지로는 미인식.
- 원래 URL의 해시 #v-dash가 Fable 브라우저 탐색 과정에서 제거돼 클라이언트 라우트가 달라질 가능성 확인.
- 해당 페이지는 표준 차트 전역 라이브러리를 노출하지 않았으며 수집된 근거로 데이터 소스 연결 확정 불가.

## 수정 사항
1. scan.py: --runtime 브라우저 탐색에서 해시 fragment(최대 512자)를 전달하고 JSON/MD에는 기존처럼 저장하지 않음.
2. scanner/runtime_detect.py: generic SVG/canvas는 실제 연결된 DOM, 최소 100×70px, SVG 도형 2개 이상 확인 후 후보로 수집. 명시적 차트 라이브러리 DOM 마커는 보존.
3. scanner/runtime_detect.py: 보이는 반복 CSS bar 그룹(4개 이상, 서로 다른 높이/너비 퍼센트, 충분한 컨테이너 크기)을 css_bar_pattern_candidate, library unknown, confidence 0.5로 별도 보수적 추출. 원본 텍스트·CSS 스타일값 미저장.
4. tests/fixture_server.py, tests/browser_runtime_check.py: 해시 라우트 CSS 막대 1개 + 장식 SVG를 검증. 테스트 결과 CSS 후보 1개, 장식 SVG 후보 0개. tests/test_runtime_detect.py와 tests/test_runtime_bootstrap.py에 회귀 추가.
5. tests/dashboard_accuracy_smoke.py: 사용자가 제공한 URL에서 실제 수집/DOM 구조를 숫자·형태로만 비교.

## 개선 전후 실제 결과

| 항목 | 개선 전 | 개선 후 |
|---|---:|---:|
| HTTP 상태 | 200 | 200 |
| XHR/fetch | 2 | 2 |
| Fable 차트 후보 | 14~15 | **3** |
| 차트 후보 유형 | 일반 SVG 후보만 | **큰 SVG 2 + CSS 막대 그룹 1** |
| 알려진 차트 라이브러리 | 0 | 0 |
| 차트↔API 연관 후보 | 0 | 0 |
| 해시 라우트 전달 | 누락 | **수정 및 Chromium fixture 검증** |
| 오류·경고 | 0 | 0 |

## 판정
이 실사이트의 핵심 오탐(작은 SVG 아이콘)과 미탐(CSS 막대 그룹)을 완화했다. 실사이트 진단과 회귀 테스트 성공. 단, 전체 차트가 얼마나 있는지에 대한 독립적인 ground truth가 없어 정량적인 정확도/재현율 100%는 주장하지 않는다.
CSS/HTML로 만든 다른 시각화 종류는 여전히 미탐일 수 있고, 차트↔API의 실제 데이터 흐름은 검증하지 못했다. Python.org와 달리 해당 대시보드에서는 같은 출처 JS 번들 후보 0건이었다.

## 사용자 Windows 재검증 명령
    git pull
    python scan.py "https://daily-dashboard-ldh-1013.clevertide128.chatgpt.site/#v-dash" --runtime --wait 10 --out ./out/dashboard-test

파일: out/dashboard-test/result.json, out/dashboard-test/report.md.
배포·서버용 SSRF 보호는 범위 밖. 사용자 Windows 환경에서 위 새 코드 실행은 아직 확인되지 않았다.
