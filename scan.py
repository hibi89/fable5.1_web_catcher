"""CLI for read-only, bounded static technology fingerprinting."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from scanner.fingerprints import apply_fingerprints
from scanner.models import blank_result, ensure_unknown
from scanner.report import write_reports
from scanner.sanitize import request_url, safe_url
from scanner.static_scan import scan_page


def scan(url: str, out: Path, timeout: float = 10.0) -> int:
    result = blank_result(safe_url(url))
    fatal = False
    try:
        request_url(url)
        observations, fatal = scan_page(url, result["target"], result["warnings"], timeout=timeout)
        try:
            apply_fingerprints(result, observations)
        except (ValueError, KeyError, OSError) as exc:
            result["warnings"].append("핑거프린트 규칙 처리 오류: " + type(exc).__name__)
    except ValueError:
        result["warnings"].append("잘못된 URL: HTTP/HTTPS 주소만 허용됩니다.")
        fatal = True
    except Exception as exc:
        result["warnings"].append("분석 처리 오류: " + type(exc).__name__)
        fatal = True
    ensure_unknown(result)
    write_reports(result, out)
    if fatal:
        print("분석 실패: " + "; ".join(result["warnings"]))
        print("부분 결과: " + str(out / "result.json"))
        return 2
    print("분석 완료: " + str(out / "result.json"))
    print("보고서: " + str(out / "report.md"))
    if result["warnings"]:
        print("경고: " + "; ".join(result["warnings"]))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="공개 URL의 정적 기술 근거 분석 (Step 1)")
    p.add_argument("url", help="HTTP/HTTPS 사이트 URL")
    p.add_argument("--out", type=Path, help="결과 폴더 (기본: out/날짜-시간)")
    p.add_argument("--timeout", type=float, default=10, help="연결 및 읽기 타임아웃 초 (기본: 10)")
    args = p.parse_args()
    if not (0 < args.timeout <= 120):
        p.error("--timeout은 0보다 크고 120 이하이어야 합니다.")
    destination = args.out or Path("out") / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return scan(args.url, destination, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
