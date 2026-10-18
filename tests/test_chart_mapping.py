"""Step 2 unit-five conservative chart-to-API association tests."""
from __future__ import annotations

import json

from scanner.chart_mapping import map_chart_api_candidates, _timeseries_shape
from scanner.models import blank_result


def _result():
    result = blank_result("https://example.test/")
    result["scan_mode"] = "runtime"
    result["runtime"] = {}
    result["charts"] = [{
        "id": "chart-001", "library": "Highcharts",
        "library_evidence": ["highcharts_dom_marker"],
        "detection_level": "library_dom_candidate",
        "last_observed_update_ms": 2000, "first_seen_ms": 1600,
        "data_sources": [],
    }]
    return result


def _endpoint(id="api-0001", ms=1900, shape=None):
    if shape is None:
        shape = {"data": [{"date": "string", "value": "number"}]}
    return {"id": id, "response_received_at_ms": ms, "status": 200,
            "response_body_analysis": "structure_only", "json_structure": shape,
            "url": "https://example.test/api/observed?token=SECRET_PRIVATE"}


def test_unique_numeric_timeseries_structure_after_response_candidate_only():
    result = _result()
    result["api"]["endpoints"] = [_endpoint()]
    map_chart_api_candidates(result)
    link = result["api"]["chart_candidates"][0]
    assert link["chart_id"] == "chart-001"
    assert link["endpoint_id"] == "api-0001"
    assert link["status"] == "candidate_only"
    assert "numeric_timeseries_structure" in link["reasons"]
    assert link["time_delta_ms"] == 100
    assert 0.55 <= link["confidence"] <= 0.65
    assert "single_observation_no_repeated_consistency" in link["limitations"]
    assert result["charts"][0]["data_sources"] == ["api-0001"]
    assert result["runtime"]["mapping_analysis"]["repeated_consistency_checked"] is False
    assert "SECRET_PRIVATE" not in json.dumps(result["api"]["chart_candidates"])


def test_nearby_unrelated_text_logs_not_linked():
    result = _result()
    logs = _endpoint("api-0002", 1999, {"logs": [{"message": "string"}]})
    result["api"]["endpoints"] = [logs, _endpoint(ms=1860)]
    map_chart_api_candidates(result)
    assert [x["endpoint_id"] for x in result["api"]["chart_candidates"]] == ["api-0001"]
    assert result["charts"][0]["data_sources"] == ["api-0001"]


def test_two_plausible_simultaneous_apis_create_no_guessed_link():
    result = _result()
    result["api"]["endpoints"] = [_endpoint(), _endpoint("api-0002", 1990)]
    map_chart_api_candidates(result)
    assert result["api"]["chart_candidates"] == []
    assert result["charts"][0]["data_sources"] == []
    assert result["runtime"]["mapping_analysis"]["ambiguous_charts_unlinked"] == 1


def test_generic_dom_marker_or_library_load_is_not_enough():
    result = _result()
    result["charts"][0]["library"] = "unknown"
    result["charts"][0]["detection_level"] = "generic_markup_candidate"
    result["api"]["endpoints"] = [_endpoint()]
    map_chart_api_candidates(result)
    assert result["api"]["chart_candidates"] == []
    assert result["runtime"]["mapping_analysis"]["marked_charts_assessed"] == 0


def test_no_response_or_missing_dom_update_does_not_link():
    result = _result()
    result["api"]["endpoints"] = [_endpoint(ms=2050)]
    map_chart_api_candidates(result)
    assert result["api"]["chart_candidates"] == []
    result["charts"][0]["last_observed_update_ms"] = None
    result["api"]["endpoints"] = [_endpoint(ms=1900)]
    map_chart_api_candidates(result)
    assert result["api"]["chart_candidates"] == []


def test_non_json_or_non_2xx_or_missing_number_does_not_link():
    result = _result()
    api = _endpoint()
    api["response_body_analysis"] = "size_unknown"
    result["api"]["endpoints"] = [api]
    map_chart_api_candidates(result)
    assert result["api"]["chart_candidates"] == []
    api["response_body_analysis"] = "structure_only"
    api["status"] = 500
    map_chart_api_candidates(result)
    assert result["api"]["chart_candidates"] == []
    api["status"] = 200
    api["json_structure"] = {"series": [{"label": "string", "value": "number"}]}
    map_chart_api_candidates(result)
    assert result["api"]["chart_candidates"] == []
    assert not _timeseries_shape(api["json_structure"])


def test_mapping_reexecution_does_not_duplicate_and_static_untouched():
    result = _result()
    result["api"]["endpoints"] = [_endpoint()]
    map_chart_api_candidates(result)
    previous = json.dumps(result["api"]["chart_candidates"], sort_keys=True)
    map_chart_api_candidates(result)
    assert json.dumps(result["api"]["chart_candidates"], sort_keys=True) == previous
    assert result["charts"][0]["data_sources"] == ["api-0001"]
    static = blank_result("https://example.test")
    map_chart_api_candidates(static)
    assert static["api"]["candidates"] == []
    assert "mapping_analysis" not in static
