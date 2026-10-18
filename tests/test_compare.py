"""Step 5 comparisons never infer removal or network traffic."""
import json
from pathlib import Path

import pytest
from scanner.compare import compare_results, run_compare
from scanner.models import blank_result


def sample(url="https://service.example.com/dashboard"):
    r=blank_result(url)
    r["scan_mode"]="runtime"
    r["target"]["final_url"]=url
    r["frontend"]=[{"name":"React","version":"17.0","confidence":0.7,
                    "evidence_ids":["ev_001"]}]
    r["evidence"]=[{"id":"ev_001","source":"script_src","key":"script_src",
                    "value":"some script","note":"untrusted"}]
    r["api"]["endpoints"]=[
        {"id":"api-0001","url":"https://api.example.com/api/v1/items/123?token=SECRET",
         "method":"GET","status":200,"content_type":"application/json",
         "json_structure":{"items":[{"value":"number","name":"string"}]},
         "response_body_analysis":"structure_only"}]
    r["charts"]=[{"id":"chart-1","library":"ECharts","selector":"user-PERSON"}]
    return r


def test_order_evidence_id_timestamp_not_real_change():
    a=sample()
    b=sample()
    b["scanned_at"]="2040-03-01T00:00:00Z"
    b["evidence"][0]["id"]="ev_999"
    b["frontend"][0]["evidence_ids"]=["ev_999"]
    b["api"]["endpoints"][0]["json_structure"]["items"][0] = {
        "name":"string", "value":"number"}
    b["charts"][0]["id"]="different-id"
    result=compare_results(a,b)
    assert result["comparison_mode"]=="same_target"
    assert all(not x["changes"] for x in result["technologies"])
    assert all(not x["changes"] for x in result["api_endpoints"])
    assert result["charts"]["individual_matching"]=="unsupported"


def test_version_and_confidence_and_schema_type_change():
    a=sample();b=sample()
    b["frontend"][0]["version"]="18.2"
    b["frontend"][0]["confidence"]=0.9
    b["api"]["endpoints"][0]["json_structure"]["items"][0]["value"]="string"
    diff=compare_results(a,b)
    assert set(diff["technologies"][0]["changes"]) >= {"version","confidence"}
    assert any("observed" in c["change"] for ep in diff["api_endpoints"]
               for c in ep["changes"])
    assert "이번 실행에서 미관찰" in " ".join(diff["warnings"])


def test_same_site_not_observed_not_deleted():
    a=sample();b=sample()
    b["frontend"]=[]
    b["api"]["endpoints"]=[]
    diff=compare_results(a,b)
    assert diff["technologies"][0]["state"]=="not_observed_this_run"
    assert diff["api_endpoints"][0]["state"]=="not_observed_this_run"
    assert "삭제됨" not in json.dumps(diff,ensure_ascii=False)


def test_different_sites_compare_without_merging_origins():
    a=sample();b=sample("https://other.example.net")
    b["api"]["endpoints"][0]["url"]="https://other-api.example.net/api/v1/items/987"
    diff=compare_results(a,b)
    assert diff["comparison_mode"]=="different_targets"
    assert len(diff["api_endpoints"])==2
    assert all("deleted" not in x["state"] for x in diff["api_endpoints"])
    assert not any(s in json.dumps(diff) for s in
                   ("example.com","example.net","?token=SECRET","user-PERSON"))


def test_mixed_modes_warn_and_masked_target_identity_unknown():
    a=sample();b=sample()
    b["scan_mode"]="record"
    assert any("스캔 모드" in x for x in compare_results(a,b)["warnings"])
    a["target"]["input_url"]="https://service.example.com/?access_token=[REDACTED]"
    assert compare_results(a,b)["comparison_mode"]=="unknown_identity"


def test_collision_is_ambiguous_and_does_not_force_lineage():
    a=sample();b=sample()
    a["api"]["endpoints"].append({
        **a["api"]["endpoints"][0],
        "id":"api-0002",
        "url":"https://api.example.com/api/v1/items/456?token=SECRET"})
    diff=compare_results(a,b)
    assert diff["api_endpoints"][0]["state"]=="ambiguous_normalized_endpoint"


def test_old_missing_fields_and_unsupported_schema(tmp_path):
    old=sample();old.pop("schema_version")
    new=sample()
    p=tmp_path/"old.json";q=tmp_path/"new.json";out=tmp_path/"diff"
    p.write_text(json.dumps(old),encoding="utf-8")
    q.write_text(json.dumps(new),encoding="utf-8")
    assert run_compare(p,q,out)==0
    assert (out/"diff.json").is_file()
    assert (out/"diff.md").is_file()
    with pytest.raises(ValueError):
        run_compare(p,q,out)
    old["schema_version"]="unknown_future_999"
    p.write_text(json.dumps(old),encoding="utf-8")
    with pytest.raises(ValueError,match="schema_version"):
        run_compare(p,q,tmp_path/"new_diff")


def test_cli_compare_no_internet_and_output(tmp_path):
    import subprocess,sys
    root=Path(__file__).resolve().parents[1]
    for name in ("a","b"):
        (tmp_path/(name+".json")).write_text(json.dumps(sample()),encoding="utf-8")
    proc=subprocess.run([sys.executable,str(root/"scan.py"),"--compare",
                         str(tmp_path/"a.json"),str(tmp_path/"b.json"),
                         "--out",str(tmp_path/"diff")],
                        capture_output=True,text=True,timeout=15,cwd=root)
    assert proc.returncode==0,proc.stderr
    assert (tmp_path/"diff"/"diff.md").exists()
