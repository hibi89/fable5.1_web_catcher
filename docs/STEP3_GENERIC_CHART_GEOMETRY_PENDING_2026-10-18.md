# 후속 검증 확정 — PR #4 병합 완료 (2026-10-18 KST)

**이 문서의 과거 'CI 차단/병합 대기' 설명은 해결 전 기록이다. 최신 최종 판정은 아래와 같다.**

- GitHub 저장소를 Public으로 전환한 뒤 이전 사용량 제한으로 작업 단계 0개에서 실패했던 workflow를 재실행하여 정상 실행됨.
- 최초 재실행 결과 Windows 65/65 PASS, Chromium 20 PASS/1 FAIL. 실패는 새 fixture의 `chart_candidates` 키 필수 존재 가정(해당 API 연결 후보가 없으면 이 필드는 생략될 수 있음)이었으며, 실제 SVG/CSS 감지는 통과.
- `tests/browser_record_check.py`에서 키 생략을 허용하도록 기대값을 `result['api'].get('chart_candidates', []) == []`로 수정. 기능 로직에는 추가 변경 없음.
- **최종 검증 소스 SHA `30a59be00d473a1040d67aa0d3166f41b70f5e70`에서 성공**:
  - Windows Python 3.11 workflow [39136596883](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39136596883) — **65/65 PASS**
  - Ubuntu 실제 headed Chromium workflow [39136596876](https://github.com/hibi89/fable5.1_web_catcher/actions/runs/39136596876) — **21/21 PASS**, 보조 공개 사이트 smoke **4/4 PASS**
- [PR #4](https://github.com/hibi89/fable5.1_web_catcher/pull/4) **main 병합 완료**, merge SHA `67e72529be4d5e6a190d7c63fc0c840878301965`. 사용자 로컬 PC 및 실제 대상 사이트에서 이 신규 코드의 그래프 변화 탐지는 아직 재확인되지 않았다.
- SVG/CSS DOM 기하 변화는 '업데이트 관찰 증거'이며, 어떤 외부 API가 차트를 움직였는지 증명하지 않는다. 기존 보수적 `chart_mapping` 정책은 유지한다.

---

# Step 3 generic SVG/CSS 상태 변화 감지 보강 — PR #4 검증 대기

## 목적
2026-10-18 Windows 사용자 실사이트 Record는 CSS bar 1건과 SVG 후보 2건을 확인했지만 `last_observed_update_ms=null`이고 차트↔API 후보는 0건이었다. 임의 API 인과관계 추정 없이 *차트 모양 변화가 관찰됐다는 사실*만 추가하고자 한다.

## 구현 중인 기능 (main 미적용)
- PR #4: https://github.com/hibi89/fable5.1_web_catcher/pull/4
- 브랜치: `fix/step3-generic-chart-change-evidence-20261018`.
- 관찰 중 SVG `path d`, `points`, `x/y/cx/cy/r`, `viewBox`, 변형·좌표 관련 속성 변경 및 내부 자식 삽입/제거 이벤트를 감지한다. 알려지지 않은 일반 SVG는 클래스/호버만 변경됐을 때 갱신으로 기록하지 않는다.
- CSS bar 그룹의 별도 스냅샷 간 퍼센트 기하벡터 변화를 동일 DOM 부모의 WeakMap 캐시로 비교한다. **크기·너비 퍼센트/도형 내용은 JS 문서 내부 임시 저장만 하며 Python 결과에는 저장하지 않는다**. 첫 발견은 baseline이며 변화 아님. 완전히 새 부모로 재생성되는 경우 변경을 확정하지 않는다.
- `change_evidence`는 `svg_geometry_changed`, `svg_structure_changed`, `css_bar_geometry_changed` 세 타입의 허용 목록만 저장. 결과는 `last_observed_update_ms`와 구조적 selector만 사용.
- 같은 selector의 이전 관찰 시각 보존, 보고서에서는 '관찰된 변화 UTC ms'와 '변화 단서'로 표기.
- 차트↔API 연결 함수는 미변경. 기존 라이브러리 DOM 마커·시계열 JSON·시간 조건 없는 generic SVG/CSS에 대해서는 **연결을 강제하지 않는다**.

## 검증 실적과 블로커
- 브랜치의 JavaScript 원문 2개를 V8 파서에서 문법 검사 통과.
- 순수 JS 모의 DOM 검증: CSS bar baseline/미변경은 시각 null; 백분율 변화 후 `css_bar_geometry_changed` 발생하고 이후 유지; 출력에 비율 원문 미포함. Generic SVG class-only hover는 시각 null, 중첩 path geometry attribute mutation 시 `svg_geometry_changed` 발생.
- Python 단위 테스트(원문 비밀값 차단 및 generic chart mapping 보류)와 실제 headed Chromium fixture 테스트가 PR에 추가되었으나 **GitHub CI 실행 실패로 미검증**.
- GitHub workflow runs `39132765417`(Windows) / `39132765458`(Chromium) 둘 다 failure 상태. 각 job은 **단계 목록 0개**, 로그 다운로드는 `BlobNotFound` 오류. 재실행한 Windows job도 단계 목록 0개로 실패. 따라서 pytest 실패로 단정하거나 PASS로 주장할 수 없다.
- 본 PR은 **main에 병합하지 않는다**. 검증 가능한 GitHub runner 또는 로컬 Playwright 환경에서 실제 Python/Chromium 전체 회귀가 실행될 때까지 보류.
- 이 모듈의 관찰은 DOM 기하 변경의 단서일 뿐 데이터 값 갱신·실제 API 인과 관계·모든 사이트 감지율을 보증하지 않는다.

## 다음 단계
- GitHub Actions 실행 환경/계정 제한을 확인한 뒤 정상적인 Windows Python 테스트 및 headed Chromium fixture 테스트를 실행한다.
- 테스트 실패가 실제 발생하면 원인만 수정, 기존 Step 1/2/3 회귀 동작을 유지한다.
- 성공 근거 확보 뒤에만 PR 병합 및 STATUS/HANDOFF/BOOK의 완료 판정 갱신. 사용자 Windows 반복 테스트는 그 후 필요할 경우 한 번만 진행.
