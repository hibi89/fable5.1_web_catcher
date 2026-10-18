"""Unit-four security, caps and distinction tests without Chromium."""
from __future__ import annotations

import json

from scanner.models import blank_result
from scanner.runtime_detect import MAX_CHARTS, collect_runtime_charts, normalize_probe


def _candidate(library="unknown", confidence=0.2, selector="body:nth-of-type(1) > canvas:nth-of-type(1)"):
    return {
        "library": library, "library_evidence": ["generic_canvas"],
        "selector": selector, "first_seen_ms": 1234567890000,
        "last_observed_update_ms": None, "detection_confidence": confidence
    }


def test_bounded_normalization_never_leaks_arbitrary_identifiers():
    raw = _candidate(selector="body#PRIVATE_TOKEN")
    raw["library_evidence"] = ["generic_canvas", "cookie_PRIVATE"]
    raw["data_sources"] = ["SECRET_PRIVATE"]
    raw["first_seen_ms"] = 123
    charts, tech, meta = normalize_probe(
        {"charts": [raw], "mutation_count": 999999, "initialized": True, "capped": True},
        [{"name": "D3", "version": "7.9.0", "instances_observed": 0, "evidence": "global_d3"}]
    )
    assert len(charts) == 1
    assert charts[0]["selector"] == "unknown"
    assert charts[0]["library_evidence"] == ["generic_canvas"]
    assert charts[0]["data_sources"] == []
    assert charts[0]["library"] == "unknown"
    assert charts[0]["detection_level"] == "generic_markup_candidate"
    assert meta["mutation_count"] == 1200
    assert meta["observer_initialized"] and meta["observation_capped"]
    assert tech[0]["name"] == "D3" and tech[0]["instances_observed"] == 0
    assert "SECRET_PRIVATE" not in json.dumps([charts, tech, meta])


def test_runtime_global_versions_only_if_explicit_and_reliable():
    chart, tech, meta = normalize_probe({"charts": []}, [
        {"name": "Highcharts", "version": "11.3.0", "instances_observed": 2,
         "evidence": "global_Highcharts"},
        {"name": "Chart.js", "version": "SECRET_VERSION_PRIVATE", "instances_observed": 0,
         "evidence": "global_Chart"},
        {"name": "ECharts", "version": "5.5.0", "instances_observed": 0,
         "evidence": "unknown_source"},
        {"name": "UnknownLibrary", "version": "1.0.0", "instances_observed": 10,
         "evidence": "unknown"}
    ])
    assert chart == []
    assert len(tech) == 2
    assert tech[0]["instances_observed"] == 2
    assert tech[1]["version"] is None
    assert all(t["name"] != "ECharts" for t in tech)
    assert not meta["observer_initialized"]


def test_chart_count_and_confidence_boundaries():
    records = [_candidate(library="Highcharts", confidence=0.85) for _ in range(MAX_CHARTS + 10)]
    records[0]["library_evidence"] = ["highcharts_dom_marker"]
    records[0]["last_observed_update_ms"] = 1234567890090
    records[1]["detection_confidence"] = 999
    charts, _, meta = normalize_probe({"charts": records, "initialized": True}, [])
    assert len(charts) == MAX_CHARTS
    assert charts[0]["last_observed_update_ms"] == 1234567890090
    assert charts[0]["detection_confidence"] == 0.85
    assert charts[0]["data_sources"] == []
    assert charts[1]["detection_confidence"] == 0.2
    assert len(set(row["id"] for row in charts)) == MAX_CHARTS


def test_evidence_merged_with_existing_frontend_schema():
    result = blank_result("https://example.test/")
    result["frontend"] = [{
        "name": "Next.js", "version": None, "confidence": 0.75, "evidence_ids": ["ev-0001"]
    }]
    result["evidence"] = [{"id": "ev-0001", "source": "html", "key": "marker",
                           "value": "present", "note": "fixture"}]
    class FakePage:
        def __init__(self):
            self.calls = 0
        def evaluate(self, script):
            self.calls += 1
            if self.calls == 1:
                return {"charts": [_candidate()], "initialized": True,
                        "mutation_count": 2, "capped": False}
            if self.calls == 3:
                return []  # new read-only CSS group observation
            return [{"name": "Next.js", "version": None, "instances_observed": 0,
                     "evidence": "next_data_marker"},
                    {"name": "D3", "version": "7.9.0", "instances_observed": 0,
                     "evidence": "global_d3"}]

    result["runtime"] = {}
    collect_runtime_charts(FakePage(), result)
    assert len(result["charts"]) == 1
    assert result["charts"][0]["library"] == "unknown"
    assert [t["name"] for t in result["runtime"]["technologies"]] == ["Next.js", "D3"]
    assert result["frontend"][0]["name"] == "Next.js"
    assert len(result["frontend"][0]["evidence_ids"]) == 2
    assert result["frontend"][1]["name"] == "D3"
    assert result["frontend"][1]["version"] == "7.9.0"
    assert result["runtime"]["chart_observer"]["mutation_count"] == 2
    assert all(ref in {ev["id"] for ev in result["evidence"]}
               for row in result["frontend"] for ref in row["evidence_ids"])



def test_css_bar_candidate_normalization_low_confidence_and_no_private_style_values():
    candidate = _candidate(selector="body:nth-of-type(1) > div:nth-of-type(4)")
    candidate["library_evidence"] = ["css_bar_group_pattern"]
    candidate["detection_confidence"] = 0.5
    chart, _, _ = normalize_probe({"charts": [candidate]}, [])
    assert len(chart) == 1
    assert chart[0]["detection_level"] == "css_bar_pattern_candidate"
    assert chart[0]["library_evidence"] == ["css_bar_group_pattern"]
    assert chart[0]["library"] == "unknown"
    assert chart[0]["data_sources"] == []
