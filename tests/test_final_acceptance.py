"""Final offline Step 1 edge cases: URL boundaries and safe partial outputs."""
from __future__ import annotations

import json
from pathlib import Path

from scan import scan
from tests.fixture_server import fixture_server


def artifact_text(out: Path) -> str:
    return ((out / "result.json").read_text(encoding="utf-8")
            + (out / "report.md").read_text(encoding="utf-8"))


def test_redirect_loop_is_bounded_and_never_saves_token(tmp_path, capsys):
    with fixture_server() as url:
        assert scan(url + "/redirect-loop?token=INPUT_LOOP_PRIVATE", tmp_path) == 2
    data = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert len(data["target"]["redirect_chain"]) == 5
    assert any("상한" in warning for warning in data["warnings"])
    output = artifact_text(tmp_path) + capsys.readouterr().out
    assert "INPUT_LOOP_PRIVATE" not in output
    assert "LOOP_PRIVATE" not in output
    assert "REDACTED" in output


def test_redirect_to_non_http_scheme_rejected_and_safe(tmp_path, capsys):
    with fixture_server() as url:
        assert scan(url + "/redirect-invalid?api_key=INPUT_SCHEME_PRIVATE", tmp_path) == 2
    data = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert any("허용하지 않는 리다이렉트" in warning for warning in data["warnings"])
    output = artifact_text(tmp_path) + capsys.readouterr().out
    assert "INPUT_SCHEME_PRIVATE" not in output
    assert "REDIRECT_SCHEME_PRIVATE" not in output


def test_input_userinfo_not_sent_or_persisted(tmp_path, capsys):
    with fixture_server() as url:
        url_with_login = url.replace("http://", "http://alice:USERINFO_PRIVATE@")
        assert scan(url_with_login + "/next?access_token=QUERY_PRIVATE", tmp_path) == 0
    data = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert data["target"]["status_code"] == 200
    output = artifact_text(tmp_path) + capsys.readouterr().out
    for secret in ("USERINFO_PRIVATE", "QUERY_PRIVATE", "alice"):
        assert secret not in output
    assert "REDACTED" in output
