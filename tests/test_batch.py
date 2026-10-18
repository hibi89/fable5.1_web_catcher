"""Step 5 three-local-URL acceptance and batch safety/failure semantics."""
import json
from pathlib import Path

import pytest

from scan import scan
from scanner.batch import parse_urls, run_batch
from scanner.models import blank_result
from scanner.report import write_reports
from tests.fixture_server import fixture_server


def test_real_three_url_localhost_batch_and_report(tmp_path):
    with fixture_server() as base:
        urls = tmp_path / "urls.txt"
        urls.write_text("# localhost authorized fixture\n" +
                        base + "/next\n" +
                        base + "/servlet\n" +
                        base + "/plain\n", encoding="utf-8")
        output = tmp_path / "batch"
        status = run_batch(urls, output, scan_fn=scan, sleep=lambda s: None)
    assert status == 0
    manifest = json.loads((output / "batch_manifest.json").read_text(encoding="utf-8"))
    assert [t["status"] for t in manifest["targets"]] == ["success"] * 3
    assert len(list((output / "targets").glob("*/result.json"))) == 3
    assert len(list((output / "targets").glob("*/report.md"))) == 3
    report = (output / "batch_report.md").read_text(encoding="utf-8")
    assert "기술" in report and "API" in report and "차트" in report
    for t in manifest["targets"]:
        assert t["report_path"].startswith("targets/")
        assert t["result_path"].startswith("targets/")
        assert not any(s in json.dumps(t) for s in ["127.0.0.1", "localhost"])
    assert (output / "batch_summary.json").exists()
    with pytest.raises(ValueError, match="이미"):
        run_batch(urls, output, scan_fn=scan, sleep=lambda s: None)


def test_parse_dedup_preserves_meaningful_path_query_order(tmp_path):
    text = tmp_path / "urls.txt"
    text.write_text("""
# comment
https://EXAMPLE.com/path?a=1&b=2#part
https://example.com/path?a=1&b=2
https://example.com/path?b=2&a=1
http://
not a url
https://example.com/other
""", encoding="utf-8")
    urls, errors = parse_urls(text)
    assert len(urls) == 3
    assert len(errors) == 2
    assert errors[0]["line"] == 6
    assert not any("not a url" in str(e) for e in errors)
    with pytest.raises(ValueError):
        parse_urls(text, max_urls=2)


def test_sensitive_batch_url_never_appears_in_output(tmp_path, capsys):
    urls = tmp_path / "urls.txt"
    urls.write_text("https://internal.example.local/custom/USER_PRIVATE?access_token=TOP_PRIVATE\n")
    def fake(url, out, timeout, **kwargs):
        r = blank_result(url)
        r["warnings"] = ["DO_NOT_PRINT_EMAIL jane@example.com"]
        r["target"]["final_url"] = url
        r["evidence"] = [{"id": "ev_001", "source": "html",
                           "key": "mail", "value": "jane@example.com",
                           "note": "secret PRIVATE_TOKEN"}]
        r["frontend"] = [{"name": "React", "version": None,
                          "confidence": 0.7, "evidence_ids": ["ev_001"]}]
        write_reports(r, out)
        print("LEAK_ASSERTION_SIMULATED_RAW_SECRET")
        return 0
    output = tmp_path / "batch"
    assert run_batch(urls, output, scan_fn=fake, sleep=lambda s: None) == 0
    all_text = "".join(p.read_text(encoding="utf-8")
                       for p in output.rglob("*") if p.is_file()) + capsys.readouterr().out
    for x in ("internal.example.local", "USER_PRIVATE", "TOP_PRIVATE", "jane@example.com",
              "PRIVATE_TOKEN", "LEAK_ASSERTION_SIMULATED_RAW_SECRET"):
        assert x not in all_text


def test_continue_on_fail_and_skip_same_origin_after_429(tmp_path):
    listfile = tmp_path / "urls.txt"
    listfile.write_text("https://a.test/first\nhttps://a.test/second\nhttps://b.test/third\n")
    calls = []
    def fake(url, out, timeout, **kwargs):
        calls.append(url)
        r = blank_result(url)
        if "first" in url:
            r["target"]["status_code"] = 429
            r["warnings"].append("429 Retry-After (not usable)")
        write_reports(r, out)
        return 2 if "first" in url else 0
    out = tmp_path / "batch"
    assert run_batch(listfile, out, scan_fn=fake, sleep=lambda s: None) == 2
    m = json.loads((out/"batch_manifest.json").read_text(encoding="utf-8"))
    assert [t["status"] for t in m["targets"]] == ["failed", "skipped", "success"]
    assert len(calls) == 2
    assert m["targets"][1]["error"] == "origin_rate_limited"


def test_interrupted_keeps_previous_results_pending(tmp_path):
    listfile = tmp_path / "urls.txt"
    listfile.write_text("https://a.test/one\nhttps://b.test/two\nhttps://c.test/three\n")
    counter = [0]
    def fake(url, out, timeout, **kwargs):
        counter[0] += 1
        if counter[0] == 2:
            raise KeyboardInterrupt()
        write_reports(blank_result(url), out)
        return 0
    out = tmp_path / "batch"
    assert run_batch(listfile, out, scan_fn=fake, sleep=lambda s: None) == 130
    m = json.loads((out/"batch_manifest.json").read_text(encoding="utf-8"))
    assert [t["status"] for t in m["targets"]] == [
        "success", "interrupted", "pending"]
    assert (out/"targets"/"001-site"/"result.json").exists()
    assert not (out/"targets"/"002-site"/"result.json").exists()


def test_cli_rejects_batch_record_and_llm(tmp_path):
    import subprocess
    import sys
    root = Path(__file__).resolve().parents[1]
    f = tmp_path/"urls.txt"
    f.write_text("https://example.com\n")
    for opts in (["--record"], ["--llm"], ["--allow-origin","https://api.example.com"],
                 ["--delay","0.2"]):
        proc = subprocess.run([sys.executable, str(root/"scan.py"), "--batch", str(f)] +
                              opts, cwd=root, capture_output=True, text=True, timeout=10)
        assert proc.returncode != 0
        assert not (tmp_path/"targets").exists()



def test_step5_acceptance_three_urls_then_compare_and_export_contracts(tmp_path):
    """The exact Step 5 final 3-operation acceptance, fully local/offline."""
    from scanner.compare import run_compare
    from scanner.contracts import run_contracts
    with fixture_server() as base:
        urls = tmp_path/"three_urls.txt"
        urls.write_text("\n".join([base+"/next",base+"/servlet",
                                    base+"/plain"])+"\n",encoding="utf-8")
        batch=tmp_path/"batch"
        assert run_batch(urls,batch,scan_fn=scan,sleep=lambda _:None)==0
    results=sorted((batch/"targets").glob("*/result.json"))
    assert len(results)==3
    assert run_compare(results[0],results[1],tmp_path/"diff")==0
    assert (tmp_path/"diff"/"diff.json").is_file()
    assert (tmp_path/"diff"/"diff.md").is_file()
    assert run_contracts(results[0],tmp_path/"contracts")==0
    assert (tmp_path/"contracts"/"contracts.md").is_file()
    assert (tmp_path/"contracts"/"contracts.json").is_file()
    document=json.loads((tmp_path/"contracts"/"contracts.json").read_text(encoding="utf-8"))
    assert document["endpoint_count"]==0
    assert "공식" in document["notice"]


def test_batch_runtime_sequential_and_no_automatic_llm(tmp_path):
    listed=tmp_path/"urls.txt"
    listed.write_text("https://one.test\nhttps://two.test\n")
    calls=[]
    def spy(url,out,timeout,*,runtime=False,wait=10,headed=False):
        calls.append((url,runtime,wait,headed))
        write_reports(blank_result(url),out)
        return 0
    assert run_batch(listed,tmp_path/"batch",scan_fn=spy,runtime=True,
                     wait=3,sleep=lambda _:None)==0
    assert len(calls)==2
    assert all(runtime and wait==3 for url,runtime,wait,headed in calls)
    assert (tmp_path/"batch"/"targets"/"002-site"/"report.md").exists()


def test_batch_redacted_api_urls_remain_usable_for_contracts(tmp_path):
    """Batch must anonymize sites without destroying observed API structure."""
    from scanner.contracts import run_contracts
    import jsonschema
    listing=tmp_path/"urls.txt"
    listing.write_text("https://example.private/one\nhttps://example.private/two\n",encoding="utf-8")
    def fake(url,out,timeout,**kwargs):
        r=blank_result(url)
        r["api"]["endpoints"]=[{
            "id":"api-0001", "method":"GET",
            "url":"https://api.internal.example/api/v1/items/123?api_key=SECRET_LEAK",
            "status":200,"content_type":"application/json",
            "response_body_analysis":"structure_only",
            "json_structure":{"items":[{"name":"string","count":"number"}]}
        }]
        write_reports(r,out)
        return 0
    output=tmp_path/"batch"
    assert run_batch(listing,output,scan_fn=fake,sleep=lambda _:None)==0
    one=output/"targets"/"001-site"/"result.json"
    clean=json.loads(one.read_text(encoding="utf-8"))
    u=clean["api"]["endpoints"][0]["url"]
    assert u.startswith("https://batch-") and u.endswith("/api/v1/items/:id")
    assert "api.internal.example" not in json.dumps(clean)
    assert "SECRET_LEAK" not in json.dumps(clean)
    assert run_contracts(one,tmp_path/"contracts")==0
    schema_path=tmp_path/"contracts"/"schemas"/"endpoint-001.schema.json"
    assert schema_path.is_file()
    jsonschema.Draft202012Validator.check_schema(
        json.loads(schema_path.read_text(encoding="utf-8")))


def test_batch_redacted_report_preserves_valid_evidence_references(tmp_path):
    """Privacy redaction must keep structural evidence IDs for rendering."""
    from scanner.batch import safe_batch_result
    from scanner.report import to_markdown
    from scanner.models import blank_result
    original = blank_result("https://customer.example/private?token=SECRET")
    original["frontend"] = [{
        "name": "React", "version": None,
        "confidence": 0.8, "evidence_ids": ["ev_001"],
    }]
    original["evidence"] = [{
        "id": "ev_001", "source": "html", "key": "test",
        "value": "PERSON_PRIVATE", "note": "SECRET_NOTE",
    }]
    cleaned = safe_batch_result(
        original, "https://batch-fixture-origin-001.batch.invalid")
    refs = cleaned["frontend"][0]["evidence_ids"]
    assert refs == ["ev_001"]
    assert set(refs) <= {e["id"] for e in cleaned["evidence"]}
    report = to_markdown(cleaned)
    assert "ev_001" in report
    for private in ("customer.example", "PERSON_PRIVATE", "SECRET_NOTE", "SECRET"):
        assert private not in report
