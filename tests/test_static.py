"""Offline end-to-end CLI tests against emulated HTTP responses."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from scan import scan
from scanner.models import CATEGORIES
from scanner.static_scan import scan_page
from tests.fixture_server import fixture_server

ROOT = Path(__file__).resolve().parents[1]


def read_result(path):
    return json.loads((path / "result.json").read_text(encoding="utf-8"))


def all_names(result, group):
    return [x["name"] for x in result[group]]


def test_next_and_schema_and_references(tmp_path):
    with fixture_server() as url:
        assert scan(url + "/next", tmp_path) == 0
    result = read_result(tmp_path)
    assert {"schema_version", "target", "scanned_at", "scan_mode", "frontend",
            "backend_inferred", "infra", "api", "charts", "evidence", "warnings"} <= set(result)
    assert result["scan_mode"] == "static"
    assert result["api"] == {"endpoints": [], "candidates": [], "connections": []}
    assert result["charts"] == []
    assert "Next.js" in all_names(result, "frontend")
    assert "Vercel" in all_names(result, "infra")
    assert "Node.js" not in all_names(result, "backend_inferred")
    evidence_ids = {ev["id"] for ev in result["evidence"]}
    for category in CATEGORIES:
        for item in result[category]:
            assert set(item) == {"name", "version", "confidence", "evidence_ids"}
            assert 0 <= item["confidence"] <= 1
            assert set(item["evidence_ids"]) <= evidence_ids
    assert (tmp_path / "report.md").exists()
    assert result["target"]["meta_generator"] == ["Test Fixture"]


def test_plain_body_does_not_trigger_framework(tmp_path):
    with fixture_server() as url:
        assert scan(url + "/plain", tmp_path) == 0
    result = read_result(tmp_path)
    assert all_names(result, "frontend") == ["unknown"]
    assert all_names(result, "backend_inferred") == ["unknown"]


def test_servlet_cookie_not_spring_boot(tmp_path):
    with fixture_server() as url:
        assert scan(url + "/servlet", tmp_path) == 0
    result = read_result(tmp_path)
    assert "Java Servlet" in all_names(result, "backend_inferred")
    assert "Spring Boot" not in all_names(result, "backend_inferred")
    assert "Apache" in all_names(result, "infra")
    assert result["target"]["cookie_names"] == ["JSESSIONID"]


def test_redirect_and_sensitive_data_not_saved(tmp_path, capsys):
    with fixture_server() as url:
        status = scan(url + "/redirect?token=INPUT_PRIVATE", tmp_path)
    assert status == 0
    result = read_result(tmp_path)
    assert result["target"]["status_code"] == 200
    assert len(result["target"]["redirect_chain"]) == 1
    all_output = (tmp_path / "result.json").read_text(encoding="utf-8") + (tmp_path / "report.md").read_text(encoding="utf-8") + capsys.readouterr().out
    for secret in ["INPUT_PRIVATE", "REDIRECT_PRIVATE", "SCRIPT_PRIVATE", "STYLE_PRIVATE"]:
        assert secret not in all_output
    assert "[REDACTED]" in all_output


def test_sensitive_cookie_and_csp_and_header(tmp_path, capsys):
    with fixture_server() as url:
        assert scan(url + "/secret?api_key=KEY_PRIVATE&safe=okay", tmp_path) == 0
    result = read_result(tmp_path)
    assert result["target"]["cookie_names"] == ["csrftoken", "sessionid"]
    assert result["target"]["csp_domains"] == ["cdn.example.net"]
    assert "Express" in all_names(result, "backend_inferred")
    saved = (tmp_path / "result.json").read_text(encoding="utf-8") + (tmp_path / "report.md").read_text(encoding="utf-8") + capsys.readouterr().out
    for secret in ("KEY_PRIVATE", "SCRIPT_PRIVATE", "STYLE_PRIVATE", "COOKIE_PRIVATE", "CSRF_PRIVATE"):
        assert secret not in saved
    assert "okay" in saved


def test_403_and_429_warnings_and_error_code(tmp_path):
    with fixture_server() as url:
        for endpoint in ("blocked", "rate"):
            out = tmp_path / endpoint
            assert scan(url + "/" + endpoint, out) == 2
            result = read_result(out)
            assert any(str(result["target"]["status_code"]) in w for w in result["warnings"])
            assert (out / "report.md").exists()


def test_bounded_html_partial_and_non_html(tmp_path):
    with fixture_server() as url:
        result = {"response_headers": {}, "cookie_names": [], "csp_domains": [], "redirect_chain": [],
                  "final_url": None, "status_code": None}
        warnings = []
        _, fatal = scan_page(url + "/huge", result, warnings, max_html_bytes=100)
        assert not fatal
        assert any("상한" in w for w in warnings)
        assert scan(url + "/not-html", tmp_path) == 0
    out = read_result(tmp_path)
    assert "Express" in all_names(out, "backend_inferred")
    assert any("HTML이 아닙니다" in w for w in out["warnings"])


def test_network_fail_and_bad_scheme(tmp_path, capsys):
    assert scan("file:///etc/passwd", tmp_path / "scheme") == 2
    assert read_result(tmp_path / "scheme")["target"]["status_code"] is None
    # Pick an impossible HTTP port on loopback and require bounded failure.
    assert scan("http://127.0.0.1:0/private?token=FAIL_PRIVATE", tmp_path / "network", timeout=1) == 2
    recorded = (tmp_path / "network" / "result.json").read_text(encoding="utf-8") + capsys.readouterr().out
    assert "FAIL_PRIVATE" not in recorded


def test_subprocess_cli(tmp_path):
    with fixture_server() as url:
        done = subprocess.run([sys.executable, str(ROOT / "scan.py"), url + "/next", "--out", str(tmp_path),
                               "--timeout", "5"], cwd=ROOT, capture_output=True, text=True, timeout=10)
    assert done.returncode == 0, done.stdout + done.stderr
    assert (tmp_path / "result.json").exists() and (tmp_path / "report.md").exists()


def test_subprocess_cli_when_stdout_cannot_encode_korean(tmp_path):
    # Reproduce Windows redirected stdout with a Western legacy console code page.
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252:strict"
    with fixture_server() as url:
        done = subprocess.run(
            [sys.executable, str(ROOT / "scan.py"), url + "/next", "--out", str(tmp_path)],
            cwd=ROOT, env=env, capture_output=True, text=True, encoding="cp1252", timeout=10,
        )
    assert done.returncode == 0, done.stdout + done.stderr
    assert (tmp_path / "result.json").exists()
    assert (tmp_path / "report.md").exists()
