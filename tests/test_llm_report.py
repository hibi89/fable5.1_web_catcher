"""Mocked SDK errors, request isolation, rendering, and on-disk report preservation."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scanner.llm_client import generate_structured, LLMServiceError
from scanner.llm_flow import run_llm_from_result
from scanner.llm_payload import build_llm_payload
from scanner.llm_report import render_llm_report
from tests.test_llm_payload import fixture
from tests.test_llm_validation import valid_output


class FakeClient:
    def __init__(self, response=None, errors=None):
        self.response = response
        self.errors = list(errors or [])
        self.calls = []
        self.responses = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.errors:
            raise self.errors.pop(0)
        return self.response


def response_for(data, status="completed", output_text=None):
    return SimpleNamespace(
        status=status, output=[],
        output_text=json.dumps(data, ensure_ascii=False) if output_text is None else output_text,
        usage=SimpleNamespace(input_tokens=55, output_tokens=12, total_tokens=67))


class FakeAPIError(Exception):
    def __init__(self, status_code):
        super().__init__("DO_NOT_LEAK_PRIVATE_URL")
        self.status_code = status_code


def test_mock_sdk_never_receives_raw_original_and_no_tools():
    data = fixture()
    payload = build_llm_payload(data)
    model = "model-user-supplied"
    client = FakeClient(response_for(valid_output(payload)))
    validated, usage = generate_structured(payload, model, client=client)
    assert validated == valid_output(payload)
    assert usage == {"input_tokens": 55, "output_tokens": 12, "total_tokens": 67}
    sent = json.dumps(client.calls)
    assert "internal.customer.example" not in sent
    assert "PRIVATE" not in sent
    assert "Ignore previous instructions" not in sent
    assert client.calls[0]["model"] == model
    assert client.calls[0]["store"] is False
    assert "tools" not in client.calls[0]
    assert client.calls[0]["text"]["format"]["strict"] is True
    assert client.calls[0]["input"][0]["role"] == "system"


@pytest.mark.parametrize("status,kind,calls", [
    (401, "authentication", 1), (429, "rate_limit", 2),
    (500, "server", 2), (400, "model_or_schema", 1),
])
def test_api_errors_typed_bounded_retry(status, kind, calls):
    payload = build_llm_payload(fixture())
    api = FakeClient(errors=[FakeAPIError(status), FakeAPIError(status)])
    with pytest.raises(LLMServiceError) as exc:
        generate_structured(payload, "manual-model", client=api, sleep=lambda _: None)
    assert exc.value.kind == kind
    assert len(api.calls) == calls
    assert "DO_NOT_LEAK" not in str(exc.value)


def test_timeout_refusal_truncation_invalid_json_errors():
    payload = build_llm_payload(fixture())

    class APITimeoutError(Exception):
        pass

    bad = FakeClient(errors=[APITimeoutError("token PRIVATE")])
    with pytest.raises(LLMServiceError) as exc:
        generate_structured(payload, "manual-model", client=bad)
    assert exc.value.kind == "timeout"
    for returned, expected in [
        (response_for(valid_output(payload), "incomplete"), "truncated"),
        (response_for(valid_output(payload), "failed"), "model_refusal"),
        (response_for(valid_output(payload), "completed", "not json"), "validation"),
    ]:
        with pytest.raises(LLMServiceError) as exc:
            generate_structured(payload, "manual-model", client=FakeClient(returned))
        assert exc.value.kind == expected


def test_missing_config_fail_closed_no_default():
    payload = build_llm_payload(fixture())
    with pytest.raises(LLMServiceError) as exc:
        generate_structured(payload, None, client=FakeClient())
    assert exc.value.kind == "model_missing"


def test_safe_korean_renderer_blocks_html_links_and_includes_local_scores():
    payload = build_llm_payload(fixture())
    report = valid_output(payload)
    report["summary"] = '<script>alert(1)</script> [click](https://bad.example) ![x](javascript:alert(1))'
    text = render_llm_report(report, payload)
    assert "<script>" not in text
    assert "&#x27;" not in text  # no quoting artifacts from fixture
    assert "&lt;script&gt;" in text
    assert "[click](https://" not in text
    assert "![" not in text
    assert "## 1. 요약" in text
    assert "## 7. 재구현 제안" in text
    assert "0.400" in text  # exact local Django rule value


def test_files_only_saved_when_validated_and_original_stays(tmp_path):
    data = fixture()
    source = tmp_path / "result.json"
    source.write_text(json.dumps(data), encoding="utf-8")
    base = tmp_path / "report.md"
    base.write_text("KEEP_ME", encoding="utf-8")
    original = source.read_bytes()
    payload = build_llm_payload(data)
    api = FakeClient(response_for(valid_output(payload)))
    assert run_llm_from_result(source, tmp_path, model="manual-model", client=api) == 0
    pack = json.loads((tmp_path / "llm_report.json").read_text(encoding="utf-8"))
    assert pack["api_usage"]["total_tokens"] == 67
    assert pack["model"] == "manual-model"
    assert len(pack["source_result_sha256"]) == 64
    assert source.read_bytes() == original
    assert base.read_text(encoding="utf-8") == "KEEP_ME"

    broken = FakeClient(response_for(valid_output(payload), output_text="{not json}"))
    previous = (tmp_path / "llm_report.json").read_bytes()
    assert run_llm_from_result(source, tmp_path, model="manual-model", client=broken) == 3
    assert (tmp_path / "llm_report.json").read_bytes() == previous
    assert base.read_text(encoding="utf-8") == "KEEP_ME"
