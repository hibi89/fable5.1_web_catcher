"""CLI for bounded static or isolated browser technology observations."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from scanner.fingerprints import apply_fingerprints
from scanner.models import blank_result, ensure_unknown
from scanner.report import write_reports
from scanner.sanitize import request_url, safe_url
from scanner.static_scan import scan_page


def scan(url: str, out: Path, timeout: float = 10.0, *, runtime: bool = False,
         headed: bool = False, wait: float = 10.0, record: bool = False,
         max_duration: float = 900.0, allow_origin: list[str] | None = None) -> int:
    if record:
        from scanner.record_scan import record_safe_url
        result = blank_result(record_safe_url(url))
    else:
        result = blank_result(safe_url(url))
    fatal = False
    if record:
        result['scan_mode'] = 'record'
    elif runtime:
        result['scan_mode'] = 'runtime'
    try:
        sanitized_request = request_url(url)
        if record:
            from scanner.record_scan import run_record
            fragment = urlsplit(url).fragment
            if fragment and len(fragment) <= 512:
                sanitized_request += '#' + fragment
            elif fragment:
                result['warnings'].append('브라우저 해시 길이 상한 초과: fragment 생략')
            fatal = run_record(sanitized_request, result, timeout=timeout,
                               max_duration=max_duration, allow_origin=allow_origin)
        elif runtime:
            # Hash fragments drive client-side dashboard routing. Browsers do not
            # send fragments over HTTP; output safe_url() still omits them.
            fragment = urlsplit(url).fragment
            if fragment and len(fragment) <= 512:
                sanitized_request += '#' + fragment
            elif fragment:
                result['warnings'].append('브라우저 화면 해시 길이 상한 초과: fragment 생략')
            from scanner.runtime_scan import scan_runtime_page
            fatal = scan_runtime_page(sanitized_request, result, timeout=timeout, wait=wait, headed=headed)
        else:
            observations, fatal = scan_page(url, result['target'], result['warnings'], timeout=timeout)
            try:
                apply_fingerprints(result, observations)
            except (ValueError, KeyError, OSError) as exc:
                result['warnings'].append('핑거프린트 규칙 처리 오류: ' + type(exc).__name__)
    except ValueError:
        result['warnings'].append('잘못된 URL 또는 allow-origin: HTTP/HTTPS 주소·정확한 origin만 허용됩니다.')
        fatal = True
    except Exception as exc:
        result['warnings'].append('분석 처리 오류: ' + type(exc).__name__)
        fatal = True
    ensure_unknown(result)
    write_reports(result, out)
    if fatal:
        print('분석 실패: ' + '; '.join(result['warnings']))
        print('부분 결과: ' + str(out / 'result.json'))
        return 2
    print('분석 완료: ' + str(out / 'result.json'))
    print('보고서: ' + str(out / 'report.md'))
    if result['warnings']:
        print('경고: ' + '; '.join(result['warnings']))
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is not None:
            reconfigure(errors='backslashreplace')
    p = argparse.ArgumentParser(description='공개 URL의 기술 단서 정적/브라우저 관찰')
    p.add_argument('url', nargs='?', help='HTTP/HTTPS 사이트 URL (또는 --from-result 사용)')
    p.add_argument('--from-result', type=Path, help='저장된 result.json 로컬 처리 (스캔 생략)')
    p.add_argument('--batch', type=Path, help='Step 5: UTF-8 URL 목록 순차 분석')
    p.add_argument('--compare', type=Path, nargs=2, metavar=('OLD', 'NEW'),
                   help='Step 5: 두 저장된 result.json 로컬 비교')
    p.add_argument('--export-contracts', action='store_true',
                   help='Step 5: --from-result의 관찰 JSON 구조 참고 계약 생성')
    p.add_argument('--delay', type=float, default=2.0,
                   help='Step 5: 배치 대상 간 대기(초), 최소 1')
    p.add_argument('--max-urls', type=int, default=50,
                   help='Step 5: 배치 고유 URL 상한, 기본 50')
    p.add_argument('--llm', action='store_true', help='명시적으로 OpenAI API 보고서 요청 (비용 가능)')
    p.add_argument('--llm-dry-run', action='store_true', help='네트워크 0회, 외부 전송 예정 자료 파일만 출력')
    p.add_argument('--model', help='OpenAI 모델 ID (기본 OPENAI_MODEL 환경변수, 하드코딩 없음)')
    p.add_argument('--out', type=Path, help='결과 폴더 (기본: out/날짜-시간)')
    p.add_argument('--timeout', type=float, default=10, help='탐색 타임아웃 초 (기본: 10)')
    p.add_argument('--runtime', action='store_true', help='Step 2: 격리 Chromium 브라우저 관찰')
    p.add_argument('--headed', action='store_true', help='Chromium 화면 표시 (--runtime 전용)')
    p.add_argument('--wait', type=float, default=10, help='DOMContentLoaded 이후 추가 관찰 시간 초 (기본: 10)')
    p.add_argument('--record', action='store_true', help='Step 3: 사용자가 직접 조작하는 headed Record')
    p.add_argument('--max-duration', type=float, default=900, help='Record 최대 초 (기본: 900)')
    p.add_argument('--allow-origin', action='append', default=[], help='추가 허용 origin (반복 지정 가능)')
    args = p.parse_args()
    modes = sum(bool(x) for x in (args.url, args.from_result, args.batch, args.compare))
    if modes != 1:
        p.error('URL, --from-result, --batch, --compare 중 하나만 지정하세요.')
    if args.export_contracts and not args.from_result:
        p.error('--export-contracts는 --from-result와 함께 사용하세요.')
    if args.export_contracts and (args.llm or args.llm_dry_run):
        p.error('--export-contracts와 --llm/--llm-dry-run 동시 사용 불가')
    if args.batch or args.compare or args.export_contracts:
        if args.llm or args.llm_dry_run or args.model:
            p.error('Step 5 배치/비교/계약은 LLM을 호출하지 않습니다.')
        if args.record or args.allow_origin:
            p.error('Step 5에서는 --record/--allow-origin 사용할 수 없습니다.')
    if args.compare or args.export_contracts:
        if args.runtime or args.headed or args.wait != 10:
            p.error('로컬 비교/계약 내보내기에는 브라우저 옵션을 사용하지 않습니다.')
    if args.batch and args.headed and not args.runtime:
        p.error('--headed는 --batch --runtime과 함께 사용하세요.')
    if not args.batch and (args.delay != 2 or args.max_urls != 50):
        p.error('--delay 및 --max-urls는 --batch 전용입니다.')
    if args.batch and (args.delay < 1 or args.max_urls < 1 or args.max_urls > 500):
        p.error('배치 --delay >=1, --max-urls 1~500 이내이어야 합니다.')
    if args.llm and args.llm_dry_run:
        p.error('--llm과 --llm-dry-run은 동시에 사용할 수 없습니다.')
    if args.from_result and (args.runtime or args.record or args.headed or
                             args.allow_origin or args.wait != 10):
        p.error('--from-result는 브라우저/Record 옵션과 같이 사용할 수 없습니다.')
    if args.llm_dry_run and not args.from_result:
        p.error('--llm-dry-run은 --from-result가 필요합니다.')
    if args.from_result and not (args.llm or args.llm_dry_run or args.export_contracts):
        p.error('--from-result는 --llm/--llm-dry-run/--export-contracts 중 하나 필요')
    if not (0 < args.timeout <= 120):
        p.error('--timeout은 0보다 크고 120 이하이어야 합니다.')
    if not (0 <= args.wait <= 120):
        p.error('--wait는 0 이상 120 이하이어야 합니다.')
    if args.headed and not (args.runtime or args.record):
        p.error('--headed는 --runtime과 함께 사용해야 합니다.')
    if not args.runtime and not args.record and args.wait != 10:
        p.error('--wait는 --runtime과 함께 사용해야 합니다.')
    if args.record and args.wait != 10:
        p.error('Record 종료는 Enter·Ctrl+C·max-duration·브라우저 종료로만 결정됩니다. --wait 사용 불가')
    if not (0 < args.max_duration <= 86400):
        p.error('--max-duration은 0보다 크고 86400 이하이어야 합니다.')
    if args.allow_origin and not args.record:
        p.error('--allow-origin은 --record 전용입니다.')
    # Step 5 operations are strictly local unless explicitly scanning a
    # user-specified batch URL. The LLM SDK is never invoked by these modes.
    if args.compare:
        from scanner.compare import run_compare
        out = args.out or Path('out') / datetime.now().strftime('diff-%Y%m%d-%H%M%S-%f')
        try:
            return run_compare(args.compare[0], args.compare[1], out)
        except (ValueError, OSError) as exc:
            p.error('결과 비교 실패: ' + str(exc))
    if args.export_contracts:
        from scanner.contracts import run_contracts
        out = args.out or args.from_result.parent / 'contracts'
        try:
            return run_contracts(args.from_result, out)
        except (ValueError, OSError) as exc:
            p.error('계약 내보내기 실패: ' + str(exc))
    if args.batch:
        from scanner.batch import run_batch
        out = args.out or Path('out') / datetime.now().strftime('batch-%Y%m%d-%H%M%S-%f')
        try:
            return run_batch(args.batch, out, scan_fn=scan, runtime=args.runtime,
                             headed=args.headed, wait=args.wait,
                             timeout=args.timeout, delay=args.delay, max_urls=args.max_urls)
        except (ValueError, OSError) as exc:
            p.error('배치 입력/출력 오류: ' + str(exc))
    import os
    from scanner.llm_flow import run_llm_from_result
    model = args.model or os.getenv('OPENAI_MODEL')
    if args.from_result:
        destination = args.out or args.from_result.parent
        return run_llm_from_result(args.from_result, destination,
                                   model=model, dry_run=args.llm_dry_run)
    destination = args.out or Path('out') / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    status = scan(args.url, destination, args.timeout, runtime=args.runtime,
                  headed=args.headed, wait=args.wait,
                  record=args.record, max_duration=args.max_duration, allow_origin=args.allow_origin)
    if status != 0 or not args.llm:
        return status
    return run_llm_from_result(destination / 'result.json', destination, model=model)


if __name__ == '__main__':
    raise SystemExit(main())
