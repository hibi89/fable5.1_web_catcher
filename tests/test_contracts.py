"""Observed-only reference contracts: no invented required, dates, values."""
import json
from pathlib import Path

import pytest

from scanner.contracts import (shape_schema, merge_schema, collect_contracts,
                               as_json_schema, run_contracts)
from scanner.models import blank_result


def record(endpoint, shape, *, status=200, content_type="application/json", i=1):
    return {"id":f"api-{i:04d}", "url":endpoint, "method":"GET",
            "status":status, "content_type":content_type,
            "json_structure":shape,
            "response_body_analysis":"structure_only" if shape is not None
            else "decoded_too_large"}


def test_nested_arrays_and_no_required_or_forbid_unknown():
    x=shape_schema({"items":[{"name":"string","value":"number",
                              "meta":{"enabled":"boolean"}}]})
    assert x["type"]=="object"
    items=x["properties"]["items"]
    assert items["type"]=="array"
    assert items["items"]["properties"]["value"]=={"type":"number"}
    txt=json.dumps(x)
    assert "required" not in txt
    assert "additionalProperties" not in txt
    assert "enum" not in txt
    assert "examples" not in txt


def test_empty_array_null_union_and_unknown_no_fake_type():
    assert shape_schema([])["items"]=={}
    assert shape_schema("null")=={"type":"null"}
    assert merge_schema([shape_schema("null"),shape_schema("number")])=={
        "anyOf":[{"type":"null"},{"type":"number"}]}
    assert merge_schema([shape_schema(["string"]),shape_schema([])])["items"]=={}
    assert shape_schema("truncated")=={}
    assert shape_schema("unknown")=={}


def test_status_variants_are_separate_and_samples_merged():
    r=blank_result("https://owned.example.com/")
    p="https://api.example.com/api/items/123"
    r["api"]["endpoints"]=[
        record(p,{"items":[{"value":"number","name":"string"}]},i=1),
        record(p,{"items":[{"value":"string","name":"null"}]},i=2),
        record(p,{"error":"string"},status=404,i=3),
    ]
    doc=collect_contracts(r)
    assert doc["endpoint_count"]==2
    ok=next(x for x in doc["endpoints"] if x["status"]==200)
    err=next(x for x in doc["endpoints"] if x["status"]==404)
    assert ok["sample_count"]==2
    assert ok["structure_samples"]==2
    assert ok["presence_frequencies"]=="unknown_in_legacy_results"
    schema=as_json_schema(ok)
    assert schema["$schema"]=="https://json-schema.org/draft/2020-12/schema"
    assert "required" not in schema and "required" not in schema["properties"]["items"]["items"]
    assert err["schema_available"]
    union=schema["properties"]["items"]["items"]["properties"]["value"]
    assert "anyOf" in union


def test_partial_prefix_never_promoted_to_complete_schema():
    r=blank_result("https://owned.example.com")
    e=record("https://api.example.com/api/items",None)
    e["json_prefix_structure"]={
        "completeness":"partial_prefix_only",
        "fields":{"name":"string","value":"number"},
    }
    r["api"]["endpoints"]=[e]
    d=collect_contracts(r)
    assert d["endpoints"][0]["schema"] is None
    assert d["endpoints"][0]["omitted_samples"]==1
    assert as_json_schema(d["endpoints"][0]) is None


def test_unsafe_json_key_and_hostname_never_exported(tmp_path):
    r=blank_result("https://internal.private.example/abc?secret=BAD_QUERY_VALUE")
    r["api"]["endpoints"]=[
        record("https://internal.private.example/api/joe@example.com?token=BAD_QUERY_VALUE",
               {"joe@example.com":"string","date":"string"},i=1)]
    src=tmp_path/"result.json";src.write_text(json.dumps(r),encoding="utf-8")
    out=tmp_path/"contracts"
    assert run_contracts(src,out)==0
    assert (out/"contracts.json").exists()
    assert (out/"contracts.md").exists()
    schema_files=list((out/"schemas").glob("*.schema.json"))
    assert len(schema_files)==1
    import jsonschema
    jsonschema.Draft202012Validator.check_schema(json.loads(schema_files[0].read_text(encoding="utf-8")))
    everything="\n".join(f.read_text(encoding="utf-8") for f in out.rglob("*") if f.is_file())
    for secret in ("internal.private.example","joe@example.com","BAD_QUERY_VALUE","?token"):
        assert secret not in everything
    assert "field_unknown" in everything or "field_1" in everything
    with pytest.raises(ValueError):
        run_contracts(src,out)


def test_cli_export_contracts_from_result(tmp_path):
    import subprocess,sys
    root=Path(__file__).resolve().parents[1]
    r=blank_result("https://owned.example")
    r["api"]["endpoints"]=[record("https://api.example.com/api/items",
                                   {"items":[{"name":"string","count":"integer"}]})]
    source=tmp_path/"result.json"
    source.write_text(json.dumps(r),encoding="utf-8")
    proc=subprocess.run([sys.executable,str(root/"scan.py"),"--from-result",
                         str(source),"--export-contracts"],
                        capture_output=True,text=True,cwd=root,timeout=12)
    assert proc.returncode==0,proc.stderr
    assert (tmp_path/"contracts"/"contracts.md").exists()


def test_depth_limit_and_absent_legacy_presence_are_unknown():
    r=blank_result("https://owned.example")
    r["api"]["endpoints"]=[record("https://api.example.com/api/data",
                                   {"deep":{"layer":{"nested":"truncated"}},
                                    "empty":[]},i=1)]
    d=collect_contracts(r)
    entry=d["endpoints"][0]
    assert entry["presence_frequencies"]=="unknown_in_legacy_results"
    assert entry["schema"]["type"]=="object"
    assert entry["schema"]["properties"]["empty"]["items"]=={}
