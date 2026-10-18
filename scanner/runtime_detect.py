"""Bounded, read-only browser chart observation and known runtime globals.

The injected JS is installed before page navigation. No chart methods are called,
no arbitrary window keys enumerated, and no canvas pixels inspected. Observed
DOM timestamps use the same epoch-ms basis as the NetworkCollector.
"""
from __future__ import annotations

import re

MAX_CHARTS = 80
MAX_TECH = 9
_VERSION = re.compile(r"^[0-9]{1,4}(?:\.[0-9]{1,4}){0,3}(?:[-+][A-Za-z0-9.-]{1,24})?$")
_NAMES = {"Next.js", "Nuxt", "Highcharts", "Chart.js", "ECharts",
          "Plotly", "ApexCharts", "D3"}

# No raw document content, attribute values or user-defined selectors are
# returned. Selectors are generated from element tag names and sibling indexes.
CHART_OBSERVER_SCRIPT = r"""
(() => {
  'use strict';
  const MAX_CHARTS = 80, MAX_MUTATIONS = 1200, MAX_BATCH_NODES = 120;
  const GEOMETRY = new Set(['d','points','x','y','x1','x2','y1','y2','cx','cy','r','rx','ry','width','height','viewBox','transform']);
  const charts = new Map();
  let mutations = 0, capped = false, started = false;
  const clock = () => Math.round(performance.timeOrigin + performance.now());
  const ntype = (node) => node && node.nodeType === 1;
  function selector(el) {
    const parts = [];
    for (let n = el, depth = 0; ntype(n) && depth < 5; n = n.parentElement, depth++) {
      const tag = n.tagName.toLowerCase();
      if (!/^[a-z][a-z0-9-]*$/.test(tag)) break;
      let index = 1, sib = n;
      while ((sib = sib.previousElementSibling)) if (sib.tagName === n.tagName) index++;
      parts.unshift(tag + ':nth-of-type(' + Math.min(index, 999) + ')');
      if (n === document.body) break;
    }
    return parts.join(' > ').slice(0, 250);
  }
  function classify(el) {
    const cls = (el.getAttribute('class') || '').slice(0, 200);
    const parent = el.parentElement;
    const pcls = parent ? (parent.getAttribute('class') || '').slice(0, 200) : '';
    const combined = cls + ' ' + pcls;
    if (/highcharts-(root|container)/i.test(combined))
      return ['Highcharts', 'highcharts_dom_marker', 0.85];
    if (el.hasAttribute('_echarts_instance_') || (parent && parent.hasAttribute('_echarts_instance_')))
      return ['ECharts', 'echarts_instance_marker', 0.85];
    if (/js-plotly-plot|main-svg/i.test(combined) && /plotly/i.test(combined + ' ' + (parent && parent.parentElement ? parent.parentElement.className || '' : '')))
      return ['Plotly', 'plotly_dom_marker', 0.8];
    if (/apexcharts-(canvas|svg)/i.test(combined))
      return ['ApexCharts', 'apexcharts_dom_marker', 0.8];
    if (/chartjs-(render-monitor|chart)/i.test(combined))
      return ['Chart.js', 'chartjs_dom_marker', 0.7];
    return ['unknown', 'generic_' + el.tagName.toLowerCase(), 0.2];
  }
  function record(el, changed, reason) {
    if (!ntype(el) || !/^(svg|canvas)$/.test((el.localName || el.tagName).toLowerCase())) return;
    let item = charts.get(el);
    if (!item && charts.size >= MAX_CHARTS) { capped = true; return; }
    const type = classify(el), now = clock();
    if (!item) {
      item = {id: 'chart-' + String(charts.size + 1).padStart(3, '0'),
        library: type[0], library_evidence: [type[1]], selector: selector(el),
        first_seen_ms: now, last_observed_update_ms: null, change_evidence: null,
        detection_confidence: type[2], detection_level:
          type[0] === 'unknown' ? 'generic_markup_candidate' : 'library_dom_candidate',
        data_sources: []};
      charts.set(el, item);
    } else if (changed) {
      // Theme/hover class changes do not establish generic SVG data movement.
      if (item.library !== 'unknown' || reason === 'svg_geometry_changed' ||
          reason === 'svg_structure_changed') {
        item.last_observed_update_ms = now;
        if (reason === 'svg_geometry_changed' || reason === 'svg_structure_changed')
          item.change_evidence = reason;
      }
      if (item.library === 'unknown' && type[0] !== 'unknown') {
        item.library = type[0]; item.library_evidence = [type[1]];
        item.detection_confidence = type[2];
        item.detection_level = 'library_dom_candidate';
      }
    }
  }
  function visit(node, changed) {
    if (!ntype(node)) return;
    record(node, changed);
    if (node.querySelectorAll) {
      const found = node.querySelectorAll('svg,canvas');
      for (let i=0; i<Math.min(found.length, MAX_BATCH_NODES); i++)
        record(found[i], changed);
      if (found.length > MAX_BATCH_NODES) capped = true;
    }
  }
  function init() {
    if (started || !document.documentElement) return;
    started = true;
    visit(document.documentElement, false);
    const observer = new MutationObserver(events => {
      if (mutations >= MAX_MUTATIONS) { capped = true; observer.disconnect(); return; }
      for (const entry of events) {
        if (++mutations > MAX_MUTATIONS) { capped = true; observer.disconnect(); break; }
        if (entry.type === 'childList') {
          for (const added of entry.addedNodes) visit(added, false);
          const svg = entry.target.closest && entry.target.closest('svg');
          if (svg && (entry.addedNodes.length || entry.removedNodes.length))
            record(svg, true, 'svg_structure_changed');
        } else if (entry.type === 'attributes') {
          visit(entry.target, true);
          const svg = entry.target.closest && entry.target.closest('svg');
          if (svg && GEOMETRY.has(entry.attributeName))
            record(svg, true, 'svg_geometry_changed');
          if (entry.target.parentElement &&
              /^(svg|canvas)$/.test((entry.target.parentElement.localName || entry.target.parentElement.tagName).toLowerCase()))
            record(entry.target.parentElement, true);
        }
      }
    });
    observer.observe(document.documentElement, {childList:true, subtree:true,
      attributes:true, attributeFilter:['class','style','width','height','viewBox','_echarts_instance_',
        'd','points','x','y','x1','x2','y1','y2','cx','cy','r','rx','ry','transform']});
  }
  Object.defineProperty(window, '__fable51_chart_probe', {
    value: {snapshot: () => ({charts:Array.from(charts.entries()).filter(([el, item]) => {
      if (item.library !== 'unknown') return true;
      if (!el.isConnected) return false;
      const box = el.getBoundingClientRect();
      const tag = (el.localName || '').toLowerCase();
      if (tag === 'canvas') return box.width >= 100 && box.height >= 70;
      const marks = el.querySelectorAll('path,line,rect,circle,polyline,polygon').length;
      return box.width >= 100 && box.height >= 70 && marks >= 2;
    }).map(([el, item]) => item), capped,
      mutation_count: mutations, initialized: started})},
    configurable:false, enumerable:false
  });
  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', init, {once:true});
  else init();
})();
"""

# Post-wait read-only shape inspection. Detects CSS bar *groups*, not libraries.
# Neither data values nor literal class/style/label text is returned to Python.
CSS_BAR_GROUP_SCRIPT = r"""
() => {
  'use strict';
  // Store only in-document geometry signatures; never persist the numbers.
  let cache = window.__fable51_css_bar_geometry;
  if (!cache) {
    cache = new WeakMap();
    Object.defineProperty(window, '__fable51_css_bar_geometry', {
      value: cache, enumerable: false, configurable: false
    });
  }
  const groups = new Map();
  const candidates = document.querySelectorAll('[style*="height:"],[style*="width:"]');
  const cls = el => typeof el.className === 'string' ? el.className : '';
  const label = el => cls(el).split(/\s+/).some(t => /(?:^|[-_])bars?(?:$|[-_])/i.test(t));
  for (let i = 0; i < Math.min(candidates.length, 400); i++) {
    const el = candidates[i], parent = el.parentElement;
    if (!parent || !label(el)) continue;
    const style = el.getAttribute('style') || '';
    const match = style.match(/(?:^|;)\s*(?:height|width)\s*:\s*(\d+(?:\.\d+)?)%/i);
    if (!match) continue;
    const n = Number(match[1]);
    if (!Number.isFinite(n) || n < 0 || n > 100) continue;
    if (!groups.has(parent)) groups.set(parent, []);
    groups.get(parent).push(n);
    if (groups.size >= 40) break;
  }
  const selector = el => {
    const parts = [];
    for (let n=el, depth=0; n && n.nodeType===1 && depth<5; n=n.parentElement,depth++) {
      const tag=n.localName.toLowerCase();
      let index=1, prev=n;
      while ((prev=prev.previousElementSibling)) if(prev.localName===n.localName) index++;
      parts.unshift(tag+':nth-of-type('+Math.min(index,999)+')');
      if(n===document.body) break;
    }
    return parts.join(' > ').slice(0,250);
  };
  const found = [];
  for (const [parent, heights] of groups.entries()) {
    const box = parent.getBoundingClientRect();
    if (!parent.isConnected || heights.length < 4 ||
        heights.length / Math.max(parent.children.length,1) < 0.65 ||
        new Set(heights.map(n=>Math.round(n))).size < 3 ||
        box.width < 120 || box.height < 45) continue;
    const now = Math.round(performance.timeOrigin+performance.now());
    const signature = heights.map(n => n.toFixed(3)).join(',');
    const prev = cache.get(parent);
    const changed = !!prev && prev.signature !== signature;
    const last = changed ? now : (prev ? prev.last : null);
    cache.set(parent, {signature, last, first: prev ? prev.first : now});
    found.push({
      library: 'unknown', library_evidence: ['css_bar_group_pattern'],
      selector: selector(parent),
      first_seen_ms: prev ? prev.first : now,
      last_observed_update_ms: last,
      change_evidence: last !== null ? 'css_bar_geometry_changed' : null,
      detection_confidence: 0.5,
      detection_level: 'css_bar_pattern_candidate',
      data_sources: []
    });
    if (found.length >= 12) break;
  }
  return found;
}
"""

# Only explicit, documented window properties; no arbitrary object traversal.
# A loaded library is not equivalent to a rendered chart.
RUNTIME_GLOBALS_SCRIPT = r"""
() => {
  'use strict';
  const out = [];
  const push = (name, present, version, instanceCount, evidence) => {
    if (!present) return;
    out.push({name, version: typeof version === 'string' ? version.slice(0, 50) : null,
      instances_observed: Number.isSafeInteger(instanceCount) && instanceCount > 0
        ? Math.min(instanceCount, 10000) : 0,
      evidence});
  };
  try {
    push('Next.js', !!(window.__NEXT_DATA__ || document.getElementById('__NEXT_DATA__')), null, 0,
         'next_data_marker');
  } catch (_) {}
  try {
    push('Nuxt', !!(window.__NUXT__ || document.getElementById('__nuxt')), null, 0,
         'nuxt_marker');
  } catch (_) {}
  try {
    const h = window.Highcharts;
    push('Highcharts', !!(h && typeof h === 'object'), h && h.version,
         h && Array.isArray(h.charts) ? h.charts.filter(Boolean).length : 0, 'global_Highcharts');
  } catch (_) {}
  try {
    const c = window.Chart;
    const items = c && c.instances;
    const count = items && typeof items === 'object'
      ? Object.values(items).filter(Boolean).length : 0;
    push('Chart.js', !!(c && (typeof c === 'function' || typeof c === 'object')),
         c && c.version, count, 'global_Chart');
  } catch (_) {}
  try {
    const e = window.echarts;
    push('ECharts', !!(e && typeof e === 'object'), e && e.version, 0, 'global_echarts');
  } catch (_) {}
  try {
    const p = window.Plotly;
    push('Plotly', !!(p && typeof p === 'object'), p && p.version, 0, 'global_Plotly');
  } catch (_) {}
  try {
    const a = window.ApexCharts;
    push('ApexCharts', !!(a && typeof a === 'function'), a && a.version, 0, 'global_ApexCharts');
  } catch (_) {}
  try {
    const d = window.d3;
    push('D3', !!(d && typeof d === 'object'), d && d.version, 0, 'global_d3');
  } catch (_) {}
  return out.slice(0, 9);
}
"""


def normalize_probe(snapshot: object, technologies: object) -> tuple[list[dict], list[dict], dict]:
    """Accept only fixed, bounded fields from injected script (zero raw page values)."""
    if not isinstance(snapshot, dict):
        snapshot = {}
    charts = []
    for chart in (snapshot.get("charts") if isinstance(snapshot.get("charts"), list) else [])[:MAX_CHARTS]:
        if not isinstance(chart, dict):
            continue
        name = chart.get("library")
        if name not in _NAMES:
            name = "unknown"
        evidence = chart.get("library_evidence")
        allowed_evidence = {
            "highcharts_dom_marker", "echarts_instance_marker", "plotly_dom_marker",
            "apexcharts_dom_marker", "chartjs_dom_marker", "generic_svg", "generic_canvas",
            "css_bar_group_pattern"
        }
        evidence = [e for e in evidence if e in allowed_evidence][:2] if isinstance(evidence, list) else []
        selector = chart.get("selector") if isinstance(chart.get("selector"), str) else ""
        # Generated structural path only (no ids, attributes, or actual page text).
        if not re.fullmatch(r"[a-z0-9> ():nth-of-type.\-]{1,250}", selector):
            selector = "unknown"
        first = chart.get("first_seen_ms")
        last = chart.get("last_observed_update_ms")
        conf = chart.get("detection_confidence")
        reason = chart.get("change_evidence")
        if reason not in ("svg_geometry_changed", "svg_structure_changed", "css_bar_geometry_changed"):
            reason = None
        charts.append({
            "id": f"chart-{len(charts)+1:03d}", "library": name,
            "library_evidence": evidence,
            "selector": selector,
            "first_seen_ms": first if type(first) is int and first > 0 else None,
            "last_observed_update_ms": last if type(last) is int and last > 0 else None,
            "change_evidence": reason if type(last) is int and last > 0 else None,
            "detection_confidence": float(conf) if type(conf) in (float, int) and 0 <= conf <= 1 else 0.2,
            "detection_level": ("css_bar_pattern_candidate" if "css_bar_group_pattern" in evidence else
                                "generic_markup_candidate" if name == "unknown" else "library_dom_candidate"),
            "data_sources": [],
        })
    tech = []
    for row in (technologies if isinstance(technologies, list) else [])[:MAX_TECH]:
        if not isinstance(row, dict) or row.get("name") not in _NAMES:
            continue
        name = row["name"]
        if any(item["name"] == name for item in tech):
            continue
        version = row.get("version")
        if not isinstance(version, str) or not _VERSION.fullmatch(version):
            version = None
        count = row.get("instances_observed")
        count = min(10000, count) if type(count) is int and count > 0 else 0
        evidence = row.get("evidence")
        allowed = {
            "Next.js": "next_data_marker", "Nuxt": "nuxt_marker",
            "Highcharts": "global_Highcharts", "Chart.js": "global_Chart",
            "ECharts": "global_echarts", "Plotly": "global_Plotly",
            "ApexCharts": "global_ApexCharts", "D3": "global_d3"
        }
        if evidence != allowed.get(name):
            continue
        tech.append({"name": name, "version": version, "library_loaded": True,
                     "instances_observed": count, "evidence": evidence})
    meta = {"observer_initialized": snapshot.get("initialized") is True,
            "mutation_count": min(1200, snapshot["mutation_count"])
            if type(snapshot.get("mutation_count")) is int and snapshot["mutation_count"] >= 0 else 0,
            "observation_capped": snapshot.get("capped") is True}
    return charts, tech, meta


def collect_runtime_charts(page, result: dict) -> None:
    """Merge runtime evidence into existing result, retaining partial records."""
    snapshot = page.evaluate("""() => {
      const p = window.__fable51_chart_probe;
      return p && typeof p.snapshot === 'function' ? p.snapshot() : {};
    }""")
    globals_seen = page.evaluate(RUNTIME_GLOBALS_SCRIPT)
    css_groups = page.evaluate(CSS_BAR_GROUP_SCRIPT)
    if not isinstance(css_groups, list):
        css_groups = []
    original = snapshot.get("charts", []) if isinstance(snapshot, dict) else []
    if not isinstance(original, list):
        original = []
    charts, tech, metadata = normalize_probe({"charts": original + css_groups,
                                              **({k: v for k, v in snapshot.items() if k != "charts"}
                                                 if isinstance(snapshot, dict) else {})}, globals_seen)
    result["charts"] = charts
    result["runtime"]["chart_observer"] = metadata
    result["runtime"]["technologies"] = tech
    for item in tech:
        # Existing static fingerprint schema remains valid.
        name = item["name"]
        category = result["frontend"]
        # No fabricated version, no "chart instance" assertion for library load alone.
        evidence_id = f"runtime-{len(result['evidence']) + 1:04d}"
        result["evidence"].append({
            "id": evidence_id, "source": "runtime_global", "key": name,
            "value": item["evidence"], "note": "알려진 런타임 전역/마커 관찰(실제 차트 사용과 별개)"
        })
        existing = next((v for v in category if v["name"] == name), None)
        if existing:
            existing["evidence_ids"] = list(dict.fromkeys(existing["evidence_ids"] + [evidence_id]))
            existing["confidence"] = max(existing["confidence"], 0.8)
            if existing.get("version") is None:
                existing["version"] = item["version"]
        else:
            category.append({"name": name, "version": item["version"],
                             "confidence": 0.8, "evidence_ids": [evidence_id]})
