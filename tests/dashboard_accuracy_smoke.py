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
        "fragment_hidden_in_persisted_url": "#v-dash" not in str(data["target"]["final_url"]),
        "runtime_dom_ready": data.get("runtime", {}).get("domcontentloaded_observed"),
        "runtime_technology_names": [r["name"] for r in data.get("runtime", {}).get("technologies", [])],
        "xhr_fetch_observed": len(data["api"]["endpoints"]),
        "chart_candidates": len(data["charts"]),
        "chart_libraries": [r["library"] for r in data["charts"]][:10],
        "css_bar_groups": sum(c["detection_level"] == "css_bar_pattern_candidate" for c in data["charts"]),
        "generic_svg_canvas_candidates": sum(c["detection_level"] == "generic_markup_candidate" for c in data["charts"]),
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
                page.wait_for_timeout(2000)
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
                    svgDetails: Array.from(document.querySelectorAll('svg')).slice(0, 12).map(e => ({
                       width: Math.round(e.getBoundingClientRect().width),
                       height: Math.round(e.getBoundingClientRect().height),
                       children: e.children.length,
                       paths: e.querySelectorAll('path').length,
                       lines: e.querySelectorAll('line').length,
                       rects: e.querySelectorAll('rect').length
                    })),
                    inlineSizedDivs: Array.from(document.querySelectorAll('div[style]')).filter(e => {
                       const st = e.getAttribute('style') || '';
                       return /(?:height|width):/.test(st);
                    }).length,
                    namedCharts: ['주별 게시물 수','게시 시간대별 반응 중앙값','브랜드별 반응 중앙값'].map(title => {
                       const e = Array.from(document.querySelectorAll('h1,h2,h3,h4,div,span,p'))
                           .find(n => n.children.length < 2 && (n.textContent || '').trim() === title);
                       if (!e) return {found:false};
                       const host = e.parentElement && e.parentElement.parentElement;
                       const lower = host && host.parentElement;
                       return {
                         found: true, tag:host?.tagName?.toLowerCase(),
                         childCount:host?.children?.length,
                         svgCount:lower?.querySelectorAll('svg')?.length,
                         canvasCount:lower?.querySelectorAll('canvas')?.length,
                         inlineSizedCount:lower?.querySelectorAll('div[style]')?.length,
                         tagHistogram:lower? Array.from(lower.querySelectorAll('*')).slice(0,150).reduce((acc,node)=>{
                             const tag=node.tagName.toLowerCase();acc[tag]=(acc[tag]||0)+1;return acc;
                           },{}) : {}
                       };
                    }),
                    cssStructure: Array.from(document.querySelectorAll(
                       '[class*="chart"],[class*="Chart"],[class*="bar"],[class*="Bar"],[class*="plot"],[class*="Plot"]'
                    )).slice(0,30).map(e => ({
                       tag: e.tagName.toLowerCase(),
                       classes: String(e.getAttribute('class')||'').slice(0,100),
                       width: Math.round(e.getBoundingClientRect().width),
                       height: Math.round(e.getBoundingClientRect().height),
                       children: e.children.length,
                       inlineSizedDesc: e.querySelectorAll('div[style]').length,
                       svgDesc: e.querySelectorAll('svg').length
                    })),
                    sizeStyles: Array.from(document.querySelectorAll('div[style]'))
                     .filter(e=> /(?:width|height):/.test(e.getAttribute('style')||''))
                     .slice(0,20).map(e=> ({
                        styles:String(e.getAttribute('style')).slice(0,90),
                        classes:String(e.getAttribute('class')||'').slice(0,80),
                        parentClasses:String(e.parentElement?.getAttribute('class')||'').slice(0,80),
                        siblings:e.parentElement?.children.length
                     })),
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
