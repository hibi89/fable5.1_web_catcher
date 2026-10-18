"""One-off external dashboard Record smoke. No clicks, secrets or saved bodies.

Only run against the user-authorized public demonstration dashboard.
Never persist result.json, report.md, screenshots, cookies or page text.
Only report aggregate outcomes for real-site acceptance.
"""
from __future__ import annotations

import json
import threading
from collections import Counter

from scanner.models import blank_result
from scanner.record_scan import run_record

URL = "https://daily-dashboard-ldh-1013.clevertide128.chatgpt.site/#v-dash"
ALLOWED_API_ORIGIN = "https://practice02.61-107-199-22.sslip.io"


def main() -> int:
    result = blank_result(URL)
    result["scan_mode"] = "record"
    stop = threading.Event()

    def stop_after_observation(context, pages, elapsed, stop_event):
        # No action, login, input, click, inspection of text, or active probing.
        # Keep the browser event loop alive long enough for initial API traffic.
        if elapsed >= 12:
            stop_event.set()

    failed = run_record(
        URL, result, timeout=22, max_duration=19,
        allow_origin=[ALLOWED_API_ORIGIN],
        stop_event=stop, test_hook=stop_after_observation,
    )
    api = result["api"]["endpoints"]
    charts = result["charts"]
    summary = {
        "scan_mode": result.get("scan_mode"),
        "navigation_http": result["target"].get("status_code"),
        "stop_reason": result.get("record", {}).get("stop_reason"),
        "duration_seconds": result.get("record", {}).get("duration_seconds"),
        "document_count": len(result.get("record", {}).get("pages", [])),
        "interaction_count": len(result.get("record", {}).get("interactions", [])),
        "api_count": len(api),
        "api_analysis_statuses": dict(sorted(Counter(
            str(e.get("response_body_analysis")) for e in api).items())),
        "json_shape_count": sum(e.get("json_structure") is not None for e in api),
        "partial_prefix_hint_count": sum(e.get("json_prefix_structure") is not None for e in api),
        "chart_count": len(charts),
        "chart_kinds": dict(sorted(Counter(
            str(c.get("detection_level")) for c in charts).items())),
        "changed_chart_count": sum(c.get("change_evidence") is not None for c in charts),
        "changed_chart_kinds": dict(sorted(Counter(
            str(c.get("change_evidence")) for c in charts
            if c.get("change_evidence") is not None).items())),
        "chart_api_candidate_count": len(result["api"].get("chart_candidates", [])),
        "warning_count": len(result.get("warnings", [])),
        "fatal": bool(failed),
        "limitations": "Read-only baseline; no manual UI interaction. Missing change evidence does not mean feature failure.",
    }
    print("P3_REAL_SITE_RECORD_SUMMARY " + json.dumps(summary, sort_keys=True, ensure_ascii=True), flush=True)
    # Do not assert changes without user interaction. Enforce basic real-site reachability.
    if failed or result["target"].get("status_code") != 200:
        print("P3_REAL_SITE_READONLY_INCONCLUSIVE: navigation/browser did not return HTTP 200")
        return 1
    print("P3_REAL_SITE_READONLY_PASS: actual public URL visited; metadata collected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
