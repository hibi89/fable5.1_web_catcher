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
    real_attach = DecodedLengthTracker.attach_page
    request_event_classes = Counter()

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

    def attach_page(self, context, page):
        result = real_attach(self, context, page)
        if not result:
            request_event_classes["attach_failed"] += 1
            return result
        session = self._sessions[-1]
        try:
            frame = session.send("Page.getFrameTree")["frameTree"]["frame"]["id"]
        except Exception:
            request_event_classes["frame_tree_error"] += 1
            return result
        tracked_ids = set()

        def received_request(evt):
            # Count all CDP requests before filtering; do not persist URLs.
            request_event_classes["any_cdp_request_event"] += 1
            info = evt.get("request") or {}
            url = info.get("url")
            method = info.get("method")
            if not isinstance(url, str):
                request_event_classes["no_string_url"] += 1
                return
            from urllib.parse import urlsplit
            path = urlsplit(url).path
            if path not in ("/gz-small", "/gz-large"):
                request_event_classes["non_fixture_request"] += 1
                return
            request_event_classes["fixture_path_request"] += 1
            if not self.allow_url(url):
                request_event_classes["fixture_url_not_approved"] += 1
                return
            request_event_classes["allowed_target_request_event"] += 1
            if evt.get("frameId") == frame:
                request_event_classes["main_frame_id_match"] += 1
            else:
                request_event_classes["main_frame_id_mismatch"] += 1
            if evt.get("type") in ("Fetch", "XHR"):
                request_event_classes["resource_type_fetch_or_xhr"] += 1
            key = (url, method)
            if self._by_page.get(page, {}).get(key):
                request_event_classes["registered_in_tracker"] += 1
            else:
                request_event_classes["not_registered_by_tracker"] += 1
            if evt.get("requestId"):
                tracked_ids.add(evt["requestId"])

        def received_data(evt):
            if evt.get("requestId") in tracked_ids:
                request_event_classes["data_event_for_allowed_target"] += 1

        def received_finish(evt):
            if evt.get("requestId") in tracked_ids:
                request_event_classes["finish_event_for_allowed_target"] += 1

        session.on("Network.requestWillBeSent", received_request)
        session.on("Network.dataReceived", received_data)
        session.on("Network.loadingFinished", received_finish)
        return result

    with patch.object(DecodedLengthTracker, "decide", decide), patch.object(
            DecodedLengthTracker, "clear", clear), patch.object(
            DecodedLengthTracker, "attach_page", attach_page):
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
    print("P3_CDP_DIAGNOSTIC_REQUEST_EVENTS", repr(dict(sorted(request_event_classes.items()))), flush=True)
    assert sum(after.values()) == 8
    assert after["browser_error"] == 0
    assert after["endpoint_count_mismatch"] == 0
    print("P3_CDP_DIAGNOSTIC_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
