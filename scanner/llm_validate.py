"""Strict local validation of model JSON. The model never supplies scores."""
from __future__ import annotations

import json
import re

from .fingerprints import RULES_PATH

PROMPT_VERSION = "step4-structured-1"

TEXT_FIELDS = {
    "summary": 900, "explanation": 700, "caveats": 500,
    "title": 150, "description": 700,
}
ITEM_LIMITS = {"backend_assessments": 25, "chart_api_assessments": 20,
               "limitations": 16, "implementation_suggestions": 12}


class LLMValidationError(ValueError):
    pass


def _object_schema(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def _str():
    return {"type": "string"}


def _strings():
    return {"type": "array", "items": _str()}


def response_json_schema():
    return _object_schema({
        "summary": _str(),
        "backend_assessments": {"type": "array", "items": _object_schema({
            "finding_id": _str(), "evidence_ids": _strings(),
            "explanation": _str(), "caveats": _str(),
        })},
        "chart_api_assessments": {"type": "array", "items": _object_schema({
            "chart_id": _str(), "endpoint_id": _str(), "evidence_ids": _strings(),
            "explanation": _str(), "caveats": _str(),
        })},
        "limitations": _strings(),
        "implementation_suggestions": {"type": "array", "items": _object_schema({
            "title": _str(), "description": _str(), "caveats": _str(),
        })},
    })


def _no_duplicates(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise LLMValidationError("duplicate JSON key")
        obj[key] = value
    return obj


def _text(value, name, limit):
    if type(value) is not str or len(value) > limit or any(
        ord(c) < 32 and c not in "\n\t" for c in value
    ):
        raise LLMValidationError(name + ": invalid text")
    return value.strip()


def _shape(obj, keys, name):
    if type(obj) is not dict or set(obj) != set(keys):
        raise LLMValidationError(name + ": missing or additional field")


def validate_llm_output(raw, payload):
    if type(raw) is str:
        if len(raw) > 100_000:
            raise LLMValidationError("response too long")
        try:
            raw = json.loads(raw, object_pairs_hook=_no_duplicates)
        except (ValueError, TypeError) as exc:
            raise LLMValidationError("invalid JSON") from exc
    schema = response_json_schema()
    _shape(raw, schema["properties"], "report")
    allowed_f = {f["id"]: f for f in payload["findings"]}
    allowed_e = {e["id"] for e in payload["evidence"]}
    allowed_pairs = {(c["chart_id"], c["endpoint_id"])
                     for c in payload["chart_api_candidates"]}
    for key, maxitems in ITEM_LIMITS.items():
        items = raw[key]
        if type(items) is not list or len(items) > maxitems:
            raise LLMValidationError(key + ": invalid list or length")
    _text(raw["summary"], "summary", TEXT_FIELDS["summary"])
    for item in raw["backend_assessments"]:
        _shape(item, ["finding_id", "evidence_ids", "explanation", "caveats"],
               "backend_assessment")
        finding = allowed_f.get(item["finding_id"])
        if not finding or finding["category"] != "backend_inferred":
            raise LLMValidationError("unknown or non-backend finding")
        _check_refs(item["evidence_ids"], set(finding["evidence_ids"]), "backend")
        _text(item["explanation"], "explanation", 700)
        _text(item["caveats"], "caveats", 500)
    for item in raw["chart_api_assessments"]:
        _shape(item, ["chart_id", "endpoint_id", "evidence_ids",
                      "explanation", "caveats"], "chart_api_assessment")
        if (item["chart_id"], item["endpoint_id"]) not in allowed_pairs:
            raise LLMValidationError("unobserved chart API pair")
        _check_refs(item["evidence_ids"], allowed_e, "chart_api")
        _text(item["explanation"], "explanation", 700)
        _text(item["caveats"], "caveats", 500)
    for item in raw["implementation_suggestions"]:
        _shape(item, ["title", "description", "caveats"], "suggestion")
        for key in ("title", "description", "caveats"):
            _text(item[key], key, TEXT_FIELDS[key])
    for lim in raw["limitations"]:
        _text(lim, "limitation", 450)

    # Detect recognizable unsupported technologies from our *known* catalog.
    # This is a bounded useful guard, not a proof against all hallucinations.
    permitted = {f["name"].lower() for f in payload["findings"]}
    from .llm_payload import _catalog
    narratives = [
        raw["summary"],
        *(s for e in raw["backend_assessments"] for s in
          (e["explanation"], e["caveats"])),
        *(s for e in raw["chart_api_assessments"] for s in
          (e["explanation"], e["caveats"])),
    ]
    sensitive_technology_names = _catalog() | {
        "Spring Boot", "Node.js", "FastAPI", "Flask", "PostgreSQL",
        "MySQL", "MongoDB", "Redis", "Kubernetes", "Docker",
    }
    for name in sensitive_technology_names:
        if name.lower() in permitted or len(name) <= 3:
            continue
        # Only explicit product-like names with token boundaries; false positives
        # result in safe rejection, not attribution.
        pat = r"(?<![a-zA-Z0-9])" + re.escape(name) + r"(?![a-zA-Z0-9])"
        if any(re.search(pat, text, re.I) for text in narratives):
            raise LLMValidationError("unobserved technology name in narrative")
    return raw


def _check_refs(refs, allowed, name):
    if type(refs) is not list or len(refs) > 15 or any(
        type(ref) is not str or ref not in allowed for ref in refs
    ):
        raise LLMValidationError(name + ": invalid evidence reference")
    if len(refs) != len(set(refs)):
        raise LLMValidationError(name + ": duplicate evidence reference")
