"""Conservative chart-to-observed-API hypotheses (Step 2 unit 5).

Never imply data lineage: browser DOM and HTTP events alone cannot establish that
the response populated the chart. No network requests, payload values, or hidden
chart state are accessed. Only existing sanitized result objects are inspected.
"""
from __future__ import annotations

from typing import Any

MAX_WINDOW_MS = 1200
MAX_MAPPINGS = 40
TIME_KEYS = frozenset({"date", "day", "month", "year", "time", "timestamp", "datetime", "x"})
REASONS = ("library_dom_marker", "numeric_timeseries_structure", "response_precedes_dom_update")
LIMITATIONS = (
    "temporal_and_structural_hypothesis_not_data_lineage",
    "single_observation_no_repeated_consistency",
    "dom_attribute_update_not_render_completion",
)


def _timeseries_shape(node: Any, depth: int = 0) -> bool:
    """Find a *single* array of objects with temporal and numeric fields."""
    if depth > 5:
        return False
    if isinstance(node, list):
        for item in node[:3]:
            if isinstance(item, dict):
                fields = {str(k).lower(): v for k, v in item.items()}
                has_time = any(k in TIME_KEYS and v in ("string", "number") for k, v in fields.items())
                has_number = any(
                    v == "number" and k not in TIME_KEYS and not k.startswith("[")
                    for k, v in fields.items()
                )
                if has_time and has_number:
                    return True
                if _timeseries_shape(item, depth + 1):
                    return True
        return False
    if isinstance(node, dict):
        return any(_timeseries_shape(v, depth + 1) for v in list(node.values())[:24])
    return False


def _qualified_chart(chart: dict) -> bool:
    return (
        chart.get("library") in {"Chart.js", "Highcharts", "ECharts", "Plotly", "ApexCharts"}
        and chart.get("detection_level") == "library_dom_candidate"
        and isinstance(chart.get("library_evidence"), list)
        and any(e in {
            "highcharts_dom_marker", "echarts_instance_marker", "plotly_dom_marker",
            "apexcharts_dom_marker", "chartjs_dom_marker"
        } for e in chart["library_evidence"])
        and type(chart.get("last_observed_update_ms")) is int
        and chart["last_observed_update_ms"] > 0
    )


def _qualified_api(row: dict, chart_at: int) -> tuple[bool, int | None]:
    stamp = row.get("response_received_at_ms")
    if (
        type(stamp) is not int
        or row.get("response_body_analysis") != "structure_only"
        or type(row.get("status")) is not int
        or not 200 <= row["status"] < 300
        or not _timeseries_shape(row.get("json_structure"))
    ):
        return False, None
    delta = chart_at - stamp
    return 0 <= delta <= MAX_WINDOW_MS, delta


def map_chart_api_candidates(result: dict) -> None:
    """Link at most one uniquely eligible observed response per marked chart.

    Cases with multiple plausible chart-shaped responses are *not* ranked by
    timing. Mark them as ambiguous and emit no guessed link.
    """
    if result.get("scan_mode") not in ("runtime", "record"):
        return
    api = result.setdefault("api", {})
    charts = result.get("charts", [])
    endpoints = api.get("endpoints", [])
    api["chart_candidates"] = []
    for chart in charts:
        chart["data_sources"] = []

    assessed = 0
    ambiguous = 0
    missing = 0
    for chart in charts:
        if len(api["chart_candidates"]) >= MAX_MAPPINGS:
            break
        if not _qualified_chart(chart):
            continue
        assessed += 1
        stamp = chart["last_observed_update_ms"]
        eligible = []
        for row in endpoints:
            ok, delta = _qualified_api(row, stamp)
            if (ok and type(row.get("id")) is str and row["id"].startswith("api-")
                    and (result.get("scan_mode") != "record" or (
                        row.get("page_id") == chart.get("page_id")
                        and row.get("navigation_id") == chart.get("navigation_id")))):
                eligible.append((row, delta))
        if len(eligible) > 1:
            ambiguous += 1
            continue
        if not eligible:
            missing += 1
            continue
        endpoint, delta = eligible[0]
        # Heuristic score is NOT a calibrated probability or verified lineage.
        confidence = round(0.55 + 0.10 * (1 - delta / MAX_WINDOW_MS), 3)
        link = {
            "chart_id": chart["id"],
            "endpoint_id": endpoint["id"],
            "confidence": confidence,
            "status": "candidate_only",
            "evidence": list(REASONS),
            "reasons": list(REASONS),
            "time_delta_ms": delta,
            "limitations": list(LIMITATIONS),
        }
        if result.get("scan_mode") == "record":
            markers = result.get("record", {}).get("interactions", [])
            matched = any(
                marker.get("page_id") == chart.get("page_id")
                and marker.get("navigation_id") == chart.get("navigation_id")
                and isinstance(marker.get("at_ms"), int)
                and 0 <= endpoint["request_started_at_ms"] - marker["at_ms"] <= 2000
                for marker in markers
            )
            if matched:
                link["confidence"] = min(0.7, round(link["confidence"] + 0.03, 3))
                link["reasons"].append("preceding_manual_interaction_marker")
                link["evidence"].append("preceding_manual_interaction_marker")
                link["limitations"].append("interaction_does_not_prove_causality")
        api["chart_candidates"].append(link)
        chart["data_sources"] = [endpoint["id"]]

    result.setdefault("runtime", {})["mapping_analysis"] = {
        "policy": "conservative_unique_candidate",
        "window_ms": MAX_WINDOW_MS,
        "marked_charts_assessed": assessed,
        "ambiguous_charts_unlinked": ambiguous,
        "no_matching_response": missing,
        "hypotheses_created": len(api["chart_candidates"]),
        "repeated_consistency_checked": False,
        "calibrated_probability": False,
    }
