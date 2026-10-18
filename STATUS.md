# STATUS.md — Fable 5.1 Web Catcher / Step 2 단위 5

## 2026-10-18 KST 현재 상태
- Step 1 원본 완료 기준 **7/7 PASS**, 정적 CLI 및 이전 26개 검증 유지.
- Step 2 **단위 1~5 완료, 전체 미완료**. 단위 1 Chromium 기초, 2 XHR/fetch·JSON 형태, 3 WebSocket/SSE, 4 런타임 차트 DOM 후보, 5 차트↔API 연관 후보.
- 비공개 GitHub hibi89/fable5.1_web_catcher / main. 검증 소스 SHA **60469e4b8c58a6f188656639a433c22a65675466**. 배포/Vercel 미적용.

## 단위 5 구현
- scanner/chart_mapping.py: 명시적인 차트 DOM 마커, 2xx JSON 수치형 시계열 구조, 응답 후 1200ms 이내 DOM 속성 갱신을 모두 확인. 일반 SVG/canvas 또는 단순 시각 근접 API는 연결하지 않음.
- 적격 API가 2건 이상이면 모호성으로 연결 보류. 단일 후보는 api.candidates에 chart_id·endpoint_id·candidate_only·근거·한계·비확률적 휴리스틱 confidence(0.55~0.65)·시각 차이, charts[].data_sources에는 endpoint ID만 기록. 실제 데이터 흐름 입증이 아니며 반복 일관성 검증도 없음.
- 기존 정적/동적 기능 보존. 테스트용 로컬 브라우저 서버에서 유일 후보와 무관 로그, 동등한 API 2건 경합을 확인. scanner/report.py에 후보·보류·한계 표시.

## 최종 테스트
- Windows Python 3.11 전체 **49/49 PASS**, GitHub Actions run **39118292918**.
- Ubuntu Python 3.11 실제 Chromium **7/7 PASS**, run **39118292894**. 양쪽 모두 기능 커밋 **60469e4b8c58a6f188656639a433c22a65675466**.
- 실사이트 정확도, 사용자 PC/Windows headed, 실제 데이터 연결은 **미검증**. 외부 URL 서버 서비스용 SSRF 보호 미구현.

## 다음 ㄱ
Step 2 **단위 6**: 현재 로드된 동일 origin JS 번들에서 제한된 문자열 기반 미검증 API 후보를 분리 추출. 임의 경로 탐색·원본 JS/비밀값 저장 금지. 이후 별도 최종 통합 검증. 상세 인수인계 HANDOFF.md.
