"""Offline fail-closed checks for Step 3 CDP decoded-length metadata."""
from scanner.cdp_decoded_size import DecodedLengthTracker
from scanner.network import MAX_JSON_BYTES


class Request:
    def __init__(self, page):
        self.url = "https://approved.test/data"
        self.method = "GET"
        self.frame = type("Frame", (), {"page": page})()


def test_unknown_missing_ambiguous_and_oversize_are_never_approved():
    page = object()
    req = Request(page)
    tracker = DecodedLengthTracker(lambda url: True)
    assert tracker.decide(req) == ("ambiguous_or_missing", None)
    tracker._by_page[page] = {
        (req.url, req.method): [
            {"decoded": 30, "over": False, "invalid": False,
             "events": 1, "done": False, "failed": False},
        ]
    }
    assert tracker.decide(req) == ("pending", None)
    tracker._by_page[page][(req.url, req.method)][0]["done"] = True
    assert tracker.decide(req) == ("ready", 30)
    tracker._by_page[page][(req.url, req.method)].append({
        "decoded": 30, "over": False, "invalid": False,
        "events": 1, "done": True, "failed": False,
    })
    assert tracker.decide(req) == ("ambiguous_or_missing", None)
    tracker._by_page[page][(req.url, req.method)] = [{
        "decoded": MAX_JSON_BYTES + 1, "over": True, "invalid": False,
        "events": 2, "done": True, "failed": False,
    }]
    assert tracker.decide(req) == ("decoded_too_large", None)
    tracker.clear()
    assert tracker.decide(req) == ("ambiguous_or_missing", None)


def test_missing_data_or_failed_request_abstains():
    page = object()
    req = Request(page)
    tracker = DecodedLengthTracker(lambda url: True)
    row = {"decoded": 0, "over": False, "invalid": False,
           "events": 0, "done": True, "failed": False}
    tracker._by_page[page] = {(req.url, req.method): [row]}
    assert tracker.decide(req) == ("invalid_or_missing", None)
    row["events"] = 1
    row["decoded"] = 20
    row["failed"] = True
    assert tracker.decide(req) == ("invalid_or_missing", None)
    row["failed"] = False
    row["invalid"] = True
    assert tracker.decide(req) == ("invalid_or_missing", None)
