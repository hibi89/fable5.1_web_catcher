"""Small transparent rule engine. Confidence is a heuristic, NOT a probability."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import CATEGORIES, ensure_unknown
from .sanitize import safe_text

RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "fingerprints.json"


def _observation_matches(observations: dict, signal: dict) -> list[tuple[str, str]]:
    source = signal["source"]
    data = observations.get(source, {})
    if isinstance(data, dict):
        items = [(str(key), str(val)) for key, val in data.items()]
    else:
        items = [(source, str(val)) for val in data]
    wanted_key = signal.get("key")
    rx = re.compile(signal["pattern"], re.I)
    matches = []
    for key, value in items:
        if wanted_key and key.lower() != wanted_key.lower():
            continue
        if rx.search(value):
            matches.append((key, value))
    return matches


def apply_fingerprints(result: dict, observations: dict, rules_path: Path = RULES_PATH) -> None:
    rules = json.loads(rules_path.read_text(encoding="utf-8"))["technologies"]
    evidence_index: dict[tuple[str, str, str, str], str] = {}
    evidences: list[dict] = []
    found: dict[str, list[dict]] = {c: [] for c in CATEGORIES}
    for tech in rules:
        cat = tech["category"]
        if cat not in found:
            raise ValueError("Unknown technology category")
        used_groups: dict[str, float] = {}
        evidence_ids: set[str] = set()
        version = None
        for signal in tech["signals"]:
            for key, value in _observation_matches(observations, signal):
                safe_val = safe_text(value, 160)
                note = signal["note"]
                signature = (signal["source"], key, safe_val, note)
                if signature not in evidence_index:
                    eid = f"ev_{len(evidences) + 1:03d}"
                    evidence_index[signature] = eid
                    evidences.append({"id": eid, "source": signal["source"],
                                      "key": safe_text(key, 80), "value": safe_val, "note": note})
                evidence_ids.add(evidence_index[signature])
                # One vote for each independent signal group, irrespective of repeats.
                group = signal.get("group", f"{signal['source']}:{key}:{signal['pattern']}")
                used_groups[group] = max(used_groups.get(group, 0), float(signal["weight"]))
                if signal.get("version_pattern") and version is None:
                    vm = re.search(signal["version_pattern"], value, re.I)
                    if vm:
                        version = vm.group(1)[:40]
        if evidence_ids:
            confidence_remaining = 1.0
            for weight in used_groups.values():
                confidence_remaining *= 1 - min(0.99, max(0, weight))
            score = round(min(0.99, 1 - confidence_remaining), 3)
            found[cat].append({"name": tech["name"], "version": version,
                               "confidence": score, "evidence_ids": sorted(evidence_ids)})
    # Canonical evidence order independent of the declaration/processing path.
    ordered = sorted(evidences, key=lambda ev: (ev["source"], ev["key"], ev["value"], ev["note"]))
    mapping = {ev["id"]: f"ev_{i:03d}" for i, ev in enumerate(ordered, 1)}
    for i, ev in enumerate(ordered, 1):
        ev["id"] = f"ev_{i:03d}"
    for category in CATEGORIES:
        for item in found[category]:
            item["evidence_ids"] = sorted(mapping[eid] for eid in item["evidence_ids"])
        result[category] = sorted(found[category], key=lambda x: x["name"].lower())
    result["evidence"] = ordered
    ensure_unknown(result)
