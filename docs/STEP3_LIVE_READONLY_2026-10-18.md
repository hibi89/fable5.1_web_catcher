# Step 3 사용자 대시보드 실제 접속 검증 — 읽기 전용 (2026-10-18)

## 범위 / 검증 설정
- 사용자 제공 공개 대시보드: `https://daily-dashboard-ldh-1013.clevertide128.chatgpt.site/#v-dash`.
- 외부 API 허용 origin: `https://practice02.61-107-199-22.sslip.io` (이전에 사용자가 명시적으로 허용하고 Windows Record 테스트에 사용한 origin).
- 검증 소스: `main` (PR #4 SVG/CSS 변화 감지와 PR #3 헤더 없는 비압축 JSON 구조 수집 반영). 테스트용 코드는 임시 `probe/p3-live-readonly-20261018` 브랜치만 사용.
- Ubuntu 24.04 GitHub-hosted runner, Python 3.11 Playwright **headed Chromium/Xvfb**, `run_record` 실행; 12초 정도 이벤트 관찰 후 test_hook으로 stop_event 종료.
- **사용자 입력·클릭·필터 변경·로그인·임의 URL probing 전혀 실행하지 않았다.** 임시 격리 브라우저에서 수집한 기초 메타데이터만 집계.
- 실제 웹페이지 텍스트·응답 값·JSON 전체·쿠키·세션·스크린샷·동영상·전체 result.json/report.md를 GitHub 로그 또는 저장소에 게시하지 않았다.
- [GitHub Actions run 39137433372](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39137433372) **success**.
- 임시 검증용 PR [#5](https://github.com/hibi89/fable5.1_web_catcher/pull/5)는 테스트 후 **병합하지 않고 closed** 처리. 프로덕션 `main`에는 해당 공개 URL 특화 테스트와 신규 의존성이 들어가지 않음.

## 실제 실행 로그 집계

```json
{
  "navigation_http": 200,
  "scan_mode": "record",
  "duration_seconds": 12.397,
  "stop_reason": "stop_signal",
  "document_count": 1,
  "interaction_count": 0,
  "api_count": 1,
  "api_analysis_statuses": {"compressed_size_unknown": 1},
  "json_shape_count": 0,
  "chart_count": 3,
  "chart_kinds": {"css_bar_pattern_candidate": 1, "generic_markup_candidate": 2},
  "changed_chart_count": 0,
  "chart_api_candidate_count": 0,
  "warning_count": 2,
  "fatal": false
}
```

**결론**: 실제 공개 사이트 연결(HTTP 200), Record 브라우저 초기화/12초 이벤트 관찰/정상 종료, 차트 3개 후보 발견, 1개 외부 API 응답 메타데이터 관찰은 **성공**. 실제 데이터 근거 없는 그래프↔API 인과 연관을 생성하지 않았다.

## 검증으로 발견한 남은 한계
1. 새 API 응답은 `compressed_size_unknown`: `Content-Length`가 없고 인코딩된 압축 JSON이다. PR #3의 허용 범위는 **완료한 비압축·크기 확인 응답**이므로 해당 웹훅 JSON은 안전 제한에 의해 분석 제외됐다. `--allow-origin` 추가만으로 해결되지 않는다. 전송 바이트와 디코딩 메모리는 다르므로 압축 본문을 무턱대고 읽으면 메모리 상한 안전을 보장할 수 없다. 이 제한을 우회하지 않는다.
2. 12초 **읽기 전용** 시험이라 실제 그래프 데이터 변화가 없었다. `change_evidence=0`는 새 SVG/CSS 변화 감지 코드의 실패를 뜻하지 않는다. 버튼 클릭/필터 값 변경이 필요하면 사용자 승인 범위 내에서 **별도 수동 Windows Record**가 필요하다.
3. 시계열 필드 구조 미수집 및 일반 SVG/CSS 차트 갱신 데이터의 인과 증거 없음: `chart_api_candidate_count=0` 유지. 임의 연결 생성 금지.
4. 실제 브라우저는 Ubuntu GitHub-hosted Chromium이다. **사용자 Windows PC의 최신 PR #3/#4 코드 적용 후 실사이트 검증은 아직 실시되지 않았다.** 이 실행을 Windows 실사용 성공이라고 주장하지 않는다.
5. 경고 2건은 집계치만 남겼다. 요청 상세/경고 원문을 기록하지 않았으므로 두 건의 원인을 단정할 수 없다.

## 다음 작업 1단위 제안
- 사용자 개입 없이 구현 가능한 **안전한 압축·크기 미확인 JSON 구조 분석 방법의 타당성 평가** (브라우저 메모리와 제약을 정직하게 기술하고 기존 범위 보호): 실제 구현할 때 악성 압축 응답의 메모리 위험을 보수적으로 다룬다.
- 사용자의 수동 Windows 검증은 이후 최종 인수 검사 1회에 한해 진행: GitHub 최신 `main`을 업데이트하고 정확한 외부 API origin을 허용한 `--record`에서 실제 필터를 직접 바꾼 뒤 결과를 비교.
