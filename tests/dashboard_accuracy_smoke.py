"""One-shot, opt-in diagnostic of user's public dashboard (not accuracy PASS)."""
from __future__ import annotations

import json
from pathlib import Path

from scan import scan
from playwright.sync_api import sync_playwright

URL = "https://daily-dashboard-ldh-1013.clevertide128.chatgpt.site/#v-dash"


def test_dashboard_structural_diagnostic(tmp_path: Path):
    # Do not save page HTML, actual API values, cookies, or authorization.
    code = scan(URL, tmp_path / "fable", runtime=True, timeout=18, wait=2)
    data = json.loads((tmp_path / "fable" / "result.json").read_text(encoding="utf-8"))
    summary = {
        "fable_exit": code,
        "fable_http": data["target"]["status_code"],
        "final_url_hash_preserved": "#v-dash" in str(data["target"]["final_url"]),
        "runtime_dom_ready": data.get("runtime", {}).get("domcontentloaded_observed"),
        "runtime_technology_names": [r["name"] for r in data.get("runtime", {}).get("technologies", [])],
        "xhr_fetch_observed": len(data["api"]["endpoints"]),
        "chart_candidates": len(data["charts"]),
        "chart_libraries": [r["library"] for r in data["charts"]][:10],
        "chart_to_api_hypotheses": len(data["api"].get("chart_candidates", [])),
        "bundle_string_candidates": len(data["api"].get("candidates", [])),
        "bundle_scripts_examined": data.get("runtime", {}).get("bundle_scan", {}).get("scanned_scripts", 0),
        "warning_count": len(data["warnings"]),
    }
    print("FABLE_DASHBOARD_DIAGNOSTIC", json.dumps(summary, ensure_ascii=False))
    # A separate read-only DOM inventory: never read text or business data.
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(ignore_https_errors=False)
            try:
                page = context.new_page()
                response = page.goto(URL, wait_until="domcontentloaded", timeout=18000)
                page.wait_for_timeout(1000)
                inventory = page.evaluate("""() => ({
                    hash: location.hash,
                    totalSvg: document.querySelectorAll('svg').length,
                    totalCanvas: document.querySelectorAll('canvas').length,
                    svgPaths: document.querySelectorAll('svg path').length,
                    svgRects: document.querySelectorAll('svg rect').length,
                    chartishCssClasses: document.querySelectorAll(
                        '[class*="chart"],[class*="Chart"],[class*="bar"],[class*="Bar"],[class*="graph"],[class*="Graph"]'
                    ).length,
                    tables: document.querySelectorAll('table').length,
                    buttons: document.querySelectorAll('button').length,
                    bodyExists: !!document.body
                })""")
                print("BROWSER_DOM_INVENTORY", json.dumps({
                    "status": response.status if response else None,
                    **inventory
                }, ensure_ascii=False))
            finally:
                context.close()
        finally:
            browser.close()
    assert code == 0 and data["target"]["status_code"] == 200, data["warnings"]
