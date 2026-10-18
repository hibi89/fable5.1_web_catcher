"""CLI for bounded static or isolated browser technology observations."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from scanner.fingerprints import apply_fingerprints
from scanner.models import blank_result, ensure_unknown
from scanner.report import write_reports
from scanner.sanitize import request_url, safe_url
from scanner.static_scan import scan_page


def scan(url: str, out: Path, timeout: float = 10.0, *, runtime: bool = False,
         headed: bool = False, wait: float = 10.0) -> int:
    result = blank_result(safe_url(url))
    fatal = False
    if runtime:
        result['scan_mode'] = 'runtime'
    try:
        sanitized_request = request_url(url)
        if runtime:
            from scanner.runtime_scan import scan_runtime_page
            fatal = scan_runtime_page(sanitized_request, result, timeout=timeout, wait=wait, headed=headed)
        else:
            observations, fatal = scan_page(url, result['target'], result['warnings'], timeout=timeout)
            try:
                apply_fingerprints(result, observations)
            except (ValueError, KeyError, OSError) as exc:
                result['warnings'].append('핑거프린트 규칙 처리 오류: ' + type(exc).__name__)
    except ValueError:
        result['warnings'].append('잘못된 URL: HTTP/HTTPS 주소만 허용됩니다.')
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
    args = p.parse_args()
    if not (0 < args.timeout <= 120):
        p.error('--timeout은 0보다 크고 120 이하이어야 합니다.')
    if not (0 <= args.wait <= 120):
        p.error('--wait는 0 이상 120 이하이어야 합니다.')
    if args.headed and not args.runtime:
        p.error('--headed는 --runtime과 함께 사용해야 합니다.')
    if not args.runtime and args.wait != 10:
        p.error('--wait는 --runtime과 함께 사용해야 합니다.')
    destination = args.out or Path('out') / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    return scan(args.url, destination, args.timeout, runtime=args.runtime,
                headed=args.headed, wait=args.wait)


if __name__ == '__main__':
    raise SystemExit(main())
