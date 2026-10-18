"""Official OpenAI Python SDK -> actual HTTP request/response serialization,
with ALL traffic intercepted in an in-process httpx2 MockTransport.

There is no real API call, no network access and no real API key. These are
offline SDK contract tests, not live model-quality tests.
"""
from __future__ import annotations

import json

import httpx2
import pytest
from openai import OpenAI

from scanner.llm_client import LLMServiceError, generate_structured
from scanner.llm_payload import build_llm_payload
from tests.test_llm_payload import fixture
from tests.test_llm_validation import valid_output

BASE = "https://api-fixture.invalid/v1"
TOKEN = "mock-placeholder-no-real-credential"


def _result(analysis=None, *, status="completed", with_refusal=False):
    if with_refusal:
        content = [{"type": "refusal", "refusal": "Request refused"}]
    else:
        content = [{"type": "output_text",
                    "text": json.dumps(analysis, ensure_ascii=False),
                    "annotations": []}]
    return {
        "id": "resp_step4_fixture",
        "object": "response",
        "created_at": 1792350000,
        "status": status,
        "model": "manual-fixture-model",
        "output": [{
            "id": "msg_step4_fixture",
            "type": "message",
            "status": "completed",
            "role": "assistant",
            "content": content,
        }],
        "usage": {
            "input_tokens": 89,
            "output_tokens": 25,
            "total_tokens": 114,
        },
    }


def _client(handler):
    transport = httpx2.MockTransport(handler)
    return OpenAI(api_key=TOKEN, base_url=BASE, max_retries=0,
                  http_client=httpx2.Client(transport=transport, trust_env=False))


def test_official_sdk_success_wire_request_and_validated_output():
    source = fixture()
    payload = build_llm_payload(source)
    analysis = valid_output(payload)
    seen = []

    def handler(request):
        seen.append((request.method, str(request.url)))
        assert request.method == "POST"
        assert str(request.url).startswith(BASE + "/responses")
        req = json.loads(request.content)
        assert req["model"] == "manual-fixture-model"
        assert req["store"] is False
        assert req["max_output_tokens"] == 3000
        assert "tools" not in req and "tool_choice" not in req
        assert req["text"]["format"]["type"] == "json_schema"
        assert req["text"]["format"]["strict"] is True
        assert req["text"]["format"]["schema"]["additionalProperties"] is False
        assert req["input"][0]["role"] == "system"
        assert req["input"][1]["role"] == "user"
        wire = json.dumps(req, ensure_ascii=False)
        for secret in ("internal.customer.example", "PRIVATE", "john@example.com",
                       "Ignore previous instructions", "access_token=QUERY"):
            assert secret not in wire
        assert "origin_1" in wire
        return httpx2.Response(200, request=request, json=_result(analysis))

    with _client(handler) as client:
        output, usage = generate_structured(payload, "manual-fixture-model",
                                            client=client)
    assert output == analysis
    assert usage == {"input_tokens": 89, "output_tokens": 25,
                     "total_tokens": 114}
    assert len(seen) == 1


@pytest.mark.parametrize("status,expected_kind,attempts", [
    (400, "model_or_schema", 1),
    (401, "authentication", 1),
    (429, "rate_limit", 2),
    (500, "server", 2),
])
def test_official_sdk_api_status_errors_bounded_retry(status, expected_kind, attempts):
    payload = build_llm_payload(fixture())
    events = []

    def handler(request):
        events.append(request.method)
        return httpx2.Response(
            status, request=request,
            json={"error": {"message": "FIXTURE_ONLY", "type": "invalid_request_error"}},
        )

    with _client(handler) as client:
        with pytest.raises(LLMServiceError) as caught:
            generate_structured(payload, "manual-fixture-model",
                                client=client, sleep=lambda _: None)
    assert caught.value.kind == expected_kind
    assert len(events) == attempts
    assert "FIXTURE_ONLY" not in str(caught.value)


@pytest.mark.parametrize("status,refusal,kind", [
    ("incomplete", False, "truncated"),
    ("completed", True, "model_refusal"),
])
def test_official_sdk_incomplete_or_refusal_is_not_persisted(status, refusal, kind):
    payload = build_llm_payload(fixture())

    def handler(request):
        return httpx2.Response(200, request=request,
                               json=_result(valid_output(payload), status=status,
                                            with_refusal=refusal))

    with _client(handler) as client:
        with pytest.raises(LLMServiceError) as caught:
            generate_structured(payload, "manual-fixture-model", client=client)
    assert caught.value.kind == kind
