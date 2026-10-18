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
