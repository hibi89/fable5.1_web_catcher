"""Stable result schema shared by static and future browser-based scanners."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "1.0"
CATEGORIES = ("frontend", "backend_inferred", "infra")


def blank_result(url: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "target": {
            "input_url": url,
            "final_url": None,
            "status_code": None,
            "redirect_chain": [],
            "response_headers": {},
            "cookie_names": [],
            "meta_generator": [],
            "scripts": [],
            "stylesheets": [],
            "csp_domains": [],
        },
        "scanned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scan_mode": "static",
        "frontend": [],
        "backend_inferred": [],
        "infra": [],
        "api": {"endpoints": [], "candidates": [], "connections": []},
        "charts": [],
        "evidence": [],
        "warnings": [],
    }


def unknown_item() -> dict[str, Any]:
    return {"name": "unknown", "version": None, "confidence": 0.0, "evidence_ids": []}


def ensure_unknown(result: dict[str, Any]) -> None:
    for category in CATEGORIES:
        if not result[category]:
            result[category] = [unknown_item()]
