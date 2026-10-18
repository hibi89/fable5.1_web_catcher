# Step 3 자동 인수검사 — 권한 있는 로컬 수동 Record

확인일: 2026-10-18 KST. 사용자 첨부 원본: 5 .1_step3.txt.
소스: hibi89/fable5.1_web_catcher, main.
PR #1의 검증 기능 SHA: 80f71d2b7de0f7a803872e76a616fe70f974e192.
main 병합 SHA: e28ea7f1f5a91d2f7a69160377558c6bc72e836d.
원본 Step 1·2의 기능과 테스트는 보존한다.

## 완료 기준과 확인 범위

| # | 원본 기준 | 확인 결과 |
|---|---|---|
| 1 | --record 실행 시 headed 브라우저 | PASS — Ubuntu xvfb-run의 실제 Chromium 창/격리 context 통합 테스트 |
| 2 | 직접 조작 중 지속 관찰 | PASS(모의 조작) — fixture 로그인 버튼, 필터 변경, 페이지 이동, 팝업에서 이벤트 펌프 유지. 사람의 실제 서비스 로그인은 미검증 |
| 3 | Enter 종료 후 JSON 및 MD | PASS — stdin에 Enter 입력한 subprocess CLI에서 두 파일과 stop_reason=enter 확인 |
| 4 | Ctrl+C/시간 만료/창 종료 | PASS — KeyboardInterrupt 주입, max-duration, 모든 창 종료의 종료 사유/정리 확인 |
| 5 | Step 2 수집기 재사용 | PASS — NetworkCollector, ConnectionCollector, BundleCollector, collect_runtime_charts와 chart_mapping 직접 재사용. 종료 전 점진적인 완료 응답 JSON 구조 처리 추가 |
| 6 | 개인정보 및 수집 범위 | PASS(오프라인 fixture 범위) — 다른 origin 페이지, 인증 경로 본문, 로그인·API 테스트 비밀값, URL 쿼리/fragment, 상한 생략 검사 |
| 7 | 기존 및 신규 테스트 | PASS — Windows 60/60, 실제 Chromium 16/16, 선택 공개사이트 점검 4/4 |
| 8 | README 사용/미지원 안내 | PASS — 설치, 직접 조작, allow-origin, 종료, 한계·보안 안내 |

**판정: Step 3 원본의 자동 검증 가능한 CLI MVP 기준 8/8 PASS. 실제 사용자의 Windows 표시 브라우저·실계정 로그인·실사이트 차트 매핑은 미검증이며 별도로 확인해야 한다.** 인과적 차트↔API 데이터 흐름 확정 도구가 아니다.

## 검증된 GitHub Actions

- Windows 2022 / Python 3.11: run **39126644441**, **60 passed**.
- Ubuntu 24.04 / Playwright 실제 Chromium with Xvfb: run **39126644405**, **16 passed** (이전 Step 2 browser fixture 및 신규 Record 시나리오 포함).
- 선택적 공개 홈페이지 example.com/python.org 정적/런타임: 같은 Ubuntu run에서 **4 passed** (외부 네트워크 의존·비필수).
- 검증 SHA는 PR branch **80f71d2b...**이며 동일 트리가 main에 **e28ea7f1...**로 병합되었다. 병합 이후 상태/문서만 변경하는 경우 해당 최종 문서 HEAD는 테스트 소스 SHA와 구별한다.
- user Windows 로컬에서 --record 실행한 증거는 아직 없다. CLI 명령의 수동 사용 흐름은 fixture에서만 자동화하여 검증했다.

## 구현 주안점

1. 입력 감시 스레드는 stop 신호만 설정하며 모든 Playwright 명령은 생성 스레드에서 실행. 루프는 wait_for_timeout으로 Playwright 이벤트를 계속 펌핑한다.
2. 새 비영구 context, 사용자 상호작용은 실제 모드에서 자동 실행하지 않는다. context의 신규 page와 main frame navigation에 page_id/frame_id/navigation_id 부여.
3. 정확한 origin allowlist 및 JS 실행 범위 guard. 범위 밖 페이지의 DOM·click/change·응답 구조를 제외하고, 외부 API는 시작 페이지가 허용된 경우에도 값 없는 메타데이터만 기록. 인증/토큰 경로는 JSON 구조 분석하지 않는다.
4. 클릭/변경 이벤트는 시각, tag, 구조적 selector만 보관. 페이지 이동을 일으킨 클릭을 위한 제한된 callback과 문서 snapshot fallback을 중복 제거하여 사용한다.
5. 각 차트 ID를 페이지·문서별로 구분. API/차트 연관 후보는 같은 page_id/navigation_id에 한정한다. 반복 일관성과 실제 데이터 연결은 증명하지 않는다.
6. 장시간 제한: XHR/fetch 10,000 이벤트 카운트, 최대 1,000 상세 행, JSON 본문 20개·개당 128KiB, 상호작용 2,000, 문서 100, 차트 결과 80, JS 번들은 기존 상한. 누락/상한은 경고로 명시한다.
7. 완료된 small JSON은 페이지 이동 전에도 점진적으로 구조 요약. 원본 본문을 결과에 저장하지 않는다. SSE/WS 완전 종료를 기다리지 않는다.
8. 종료 이유 enter / ctrl_c / max_duration / browser_closed / stdin_eof / stop_signal 및 초기 탐색/브라우저 오류, 마무리 및 브라우저 정리. 비대화형 EOF는 오류로 표기한다.

## 실행

~~~powershell
git pull origin main
python -m pip install -r requirements.txt
python -m playwright install chromium
python scan.py "https://내가-권한있는-사이트" --record --max-duration 900 --out ./out/record
~~~

로그인과 조작 후 터미널 Enter. 출력: out/record/result.json, out/record/report.md. 선택적으로 --allow-origin https://api.example.com 을 여러 번 추가할 수 있다. 이 도구는 URL을 받는 공개 서버에 올리지 않는다.

## 남은 한계 및 검증 대기

- 사람의 Windows 실제 계정 로그인/차트 필터 변경→API와 chart 후보 확인은 미검증.
- 페이지 이동 시 아주 짧게 나타났다 사라지는 시각화는 폴링 사이에 누락될 수 있음. iframe 내부 DOM/행동은 분석하지 않으며 경고 처리.
- 실제 사이트의 인증 제공자/WAF/SPA/차트 라이브러리별 호환성·정밀도는 보장되지 않음.
- Playwright response.body의 압축 해제 순간 절대 메모리 상한은 보장되지 않음.
- 외부 사용자 URL 서비스의 SSRF·리소스 격리 미구현. 로컬 승인 사이트 전용.
- Record의 cross-document JS 문자열 단서는 관찰한 script 후보만 수집하며 일부 이전 문서 정보가 읽히지 않을 수 있음.
