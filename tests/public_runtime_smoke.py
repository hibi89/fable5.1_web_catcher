"""Optional live-site smoke for Step 2 final acceptance, never a fixture test.

Only visits the public homepage URLs below, once in static and once in
runtime mode. The checks validate output structure, not claimed technologies.
"""
from __future__ import annotations

import json

import pytest

from scan import scan

SITES = ("https://example.com/", "https://www.python.org/")


@pytest.mark.parametrize("site", SITES)
@pytest.mark.parametrize("runtime", (False, True))
def test_public_homepage_generates_evidence_backed_reports(site, runtime, tmp_path):
    destination = tmp_path / ("runtime" if runtime else "static")
    code = scan(site, destination, timeout=18, wait=0.35, runtime=runtime)
    data = json.loads((destination / "result.json").read_text(encoding="utf-8"))
    report = (destination / "report.md").read_text(encoding="utf-8")
    print(
        "PUBLIC_SITE_RESULT",
        "site=", site,
        "mode=", data["scan_mode"],
        "code=", code,
        "http=", data["target"]["status_code"],
        "endpoints=", len(data["api"]["endpoints"]),
        "charts=", len(data["charts"]),
        "warnings=", len(data["warnings"]),
    )
    assert code == 0, data["warnings"]
    assert data["target"]["status_code"] == 200
    assert data["scan_mode"] == ("runtime" if runtime else "static")
    assert "## 한계 및 주의" in report
    evidence = {e["id"] for e in data["evidence"]}
    for category in ("frontend", "backend_inferred", "infra"):
        assert data[category]
        for item in data[category]:
            assert all(ref in evidence for ref in item["evidence_ids"])
    if runtime:
        assert data["runtime"]["domcontentloaded_observed"] is True
        assert isinstance(data["api"]["candidates"], list)
        assert all(row["status"] == "unverified_string_literal"
                   for row in data["api"]["candidates"])
    else:
        assert set(data["api"]) == {"endpoints", "candidates", "connections"}
