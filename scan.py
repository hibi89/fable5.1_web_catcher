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
    p.add_argument('url', help='HTTP/HTTPS 사이트 URL')
    p.add_argument('--out', type=Path, help='결과 폴더 (기본: out/날짜-시간)')
    p.add_argument('--timeout', type=float, default=10, help='탐색 타임아웃 초 (기본: 10)')
    p.add_argument('--runtime', action='store_true', help='Step 2: 격리 Chromium 브라우저 관찰')
    p.add_argument('--headed', action='store_true', help='Chromium 화면 표시 (--runtime 전용)')
    p.add_argument('--wait', type=float, default=10, help='DOMContentLoaded 이후 추가 관찰 시간 초 (기본: 10)')
    p.add_argument('--record', action='store_true', help='Step 3: 사용자가 직접 조작하는 headed Record')
    p.add_argument('--max-duration', type=float, default=900, help='Record 최대 초 (기본: 900)')
    p.add_argument('--allow-origin', action='append', default=[], help='추가 허용 origin (반복 지정 가능)')
    args = p.parse_args()
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
    destination = args.out or Path('out') / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    return scan(args.url, destination, args.timeout, runtime=args.runtime,
                headed=args.headed, wait=args.wait,
                record=args.record, max_duration=args.max_duration, allow_origin=args.allow_origin)


if __name__ == '__main__':
    raise SystemExit(main())
