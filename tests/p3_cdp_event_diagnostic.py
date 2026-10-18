"""Temporary privacy-preserving CDP event timing diagnostic; do not merge.

Runs only localhost two-server gzip fixture. Logs aggregate status counts,
decoded-event presence, CDP completion and request association, not URLs,
headers, body bytes, credentials, field names or other user information.
"""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
from threading import Event
from unittest.mock import patch

from scanner.cdp_decoded_size import DecodedLengthTracker
from scanner.models import blank_result
from scanner.record_scan import run_record
from tests.browser_record_check import serve_record


def snapshot_category(tracker, request):
    try:
        page = request.frame.page
        matches = tracker._by_page.get(page, {}).get((request.url, request.method), ())
        if len(matches) == 0:
            return "no_cdp_match"
        if len(matches) > 1:
            return "ambiguous_cdp_match"
        s = matches[0]
        if s["failed"]:
            return "loading_failed"
        if s["invalid"]:
            return "invalid_data_event"
        if s["events"] == 0:
            return "zero_data_events_done" if s["done"] else "zero_data_events_pending"
        if not s["done"]:
            return "data_present_pending_finish"
        if s["over"]:
            return "complete_over_cap"
        return "complete_within_cap"
    except Exception:
        return "diagnostic_unavailable"


def main():
    before = Counter()
    at_clear = Counter()
    after = Counter()
    real_decide = DecodedLengthTracker.decide
    real_clear = DecodedLengthTracker.clear

    def decide(self, req):
        before[snapshot_category(self, req)] += 1
        return real_decide(self, req)

    def clear(self):
        for page, by_key in self._by_page.items():
            for states in by_key.values():
                for s in states:
                    if s.get("failed"):
                        at_clear["loading_failed"] += 1
                    elif s.get("invalid"):
                        at_clear["invalid"] += 1
                    elif not s.get("done"):
                        at_clear["not_done"] += 1
                    elif s.get("events", 0) == 0:
                        at_clear["finished_without_data_event"] += 1
                    elif s.get("over"):
                        at_clear["complete_over_cap"] += 1
                    else:
                        at_clear["complete_within_cap"] += 1
        return real_clear(self)

    with patch.object(DecodedLengthTracker, "decide", decide), patch.object(
            DecodedLengthTracker, "clear", clear):
        for delay_ms in (0, 500):
            for endpoint in ("/gz-small", "/gz-large"):
                for repeat in range(2):
                    with ExitStack() as stack:
                        dashboard = stack.enter_context(serve_record())
                        external = stack.enter_context(serve_record())
                        result = blank_result(dashboard)
                        fired = set()

                        def hook(context, pages, elapsed, stop):
                            if fired:
                                return
                            fired.add(1)
                            pg = context.pages[0]
                            pg.evaluate("u => fetch(u).then(r => r.json()).then(x => !!x)",
                                        external + endpoint)
                            pg.wait_for_timeout(delay_ms)
                            stop.set()

                        error = run_record(
                            dashboard + "/record", result, timeout=8,
                            max_duration=12, allow_origin=[external],
                            stop_event=Event(), test_hook=hook)
                        rows = result["api"].get("endpoints", [])
                        chosen = [row for row in rows
                                  if row.get("url", "").endswith(endpoint)]
                        if error:
                            after["browser_error"] += 1
                        elif len(chosen) != 1:
                            after["endpoint_count_mismatch"] += 1
                        else:
                            status = chosen[0].get("response_body_analysis", "unknown")
                            after[(delay_ms, "small" if endpoint.endswith("small") else "large", status)] += 1
                            # Assert existing security policy is never violated.
                            if status in ("compressed_decoded_unavailable", "decoded_too_large"):
                                assert chosen[0].get("json_structure") is None
    # Print only categories and integer counts, never actual request data.
    print("P3_CDP_DIAGNOSTIC_BEFORE", repr(dict(sorted(before.items()))), flush=True)
    print("P3_CDP_DIAGNOSTIC_FINAL", repr(dict(sorted(at_clear.items()))), flush=True)
    print("P3_CDP_DIAGNOSTIC_OUTCOME", repr({
        str(k): v for k, v in sorted(after.items(), key=lambda kv: str(kv[0]))
    }), flush=True)
    assert sum(after.values()) == 8
    assert after["browser_error"] == 0
    assert after["endpoint_count_mismatch"] == 0
    print("P3_CDP_DIAGNOSTIC_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
