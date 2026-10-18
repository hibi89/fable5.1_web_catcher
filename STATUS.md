# STATUS.md — Fable 5.1 Web Catcher / Step 2 단위 4

## 현재 상태 (2026-10-18 KST)
Step 1 **완료 100%, 원본 7/7 PASS**. 기존 26개 정적 회귀 및 3 OS, 두 실사이트 정적 smoke 완료 기록 유지(docs/STEP1_FINAL_ACCEPTANCE.md).
Step 2 **단위 1~4 완료/해당 fixture 검증 성공, 전체 미완료**. 격리 Chromium, XHR/fetch·JSON 구조, WS/SSE, 런타임 기술/차트 DOM 후보 구현. 차트↔API 연결 점수·JS 번들 후보는 미구현.

## 구현 및 검증
새 scanner/runtime_detect.py는 페이지 이동 전 DOM MutationObserver(초기 SVG/canvas+추가/속성 갱신)를 붙이고 알려진 Next/Nuxt/Highcharts/Chart.js/ECharts/Plotly/ApexCharts/D3만 검사. 라이브러리 로드≠차트 인스턴스, 일반 SVG/canvas·D3로 차트 확정 안 함. 후보 최대 80개, mutation 1200건, 구조적 selector·동일 epoch ms 기록. canvas 픽셀 변화 감지 못하며 DOM 시각은 렌더 완료 시각이 아님. chart별 data_sources는 빈 배열.

GitHub **Windows 42/42 PASS** (run 39117164191), 실제 **Chromium 5/5 PASS** (run 39117164160); 기능 SHA **a1a7ae57675c36e2b7673e2156e405ccb70d9ecd**. 앞선 browser run 39117073731 4 PASS/1 FAIL(SVG tagName 대문자 비교 오류)을 소문자 정규화로 수정 후 재검증 성공.
실제 라이브러리 배포 파일이 아닌 명시적 JS stub을 사용한 fixture. 실사이트 정확도, 사용자 PC, Windows headed는 미검증.

## 저장소·배포
비공개 hibi89/fable5.1_web_catcher, main. 배포·Vercel/Production **미적용**. 코드 GitHub HEAD는 문서 갱신 후 재확인. 자세한 HANDOFF.md 10항.

## 다음 ㄱ
**Step 2 단위 5 — 차트↔API 연관 후보 근거 기반 점수화**: 시간+JSON 구조+반복+경합·불확실성 표시. 타이밍만으로 연결 확정 금지. JS 번들·최종 통합 검증은 이후.
