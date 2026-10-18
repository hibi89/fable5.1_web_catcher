"""Schema, cross-reference and score injection guards."""
import json
import pytest

from scanner.llm_payload import build_llm_payload
from scanner.llm_validate import LLMValidationError, validate_llm_output, response_json_schema
from tests.test_llm_payload import fixture


def valid_output(payload):
    backend = next(x for x in payload["findings"] if x["category"] == "backend_inferred")
    pair = payload["chart_api_candidates"][0]
    return {
        "summary": "단서는 제한적이며 확정 백엔드는 unknown입니다.",
        "backend_assessments": [{
            "finding_id": backend["id"], "evidence_ids": backend["evidence_ids"],
            "explanation": "관찰된 쿠키 이름은 프레임워크 관례의 약한 단서입니다.",
            "caveats": "실제 서버 코드와 DB는 확인하지 못했습니다.",
        }],
        "chart_api_assessments": [{
            "chart_id": pair["chart_id"], "endpoint_id": pair["endpoint_id"],
            "evidence_ids": [payload["evidence"][0]["id"]],
            "explanation": "타이밍과 구조적 단서에 기반한 연관 후보입니다.",
            "caveats": "인과관계가 입증되지는 않았습니다.",
        }],
        "limitations": ["부분적으로 관찰했으며 자료가 생략되었을 수 있습니다."],
        "implementation_suggestions": [{
            "title": "검증 가능한 MVP 구현",
            "description": "필터 상태와 API 연결을 테스트 가능한 단위로 새롭게 구현합니다.",
            "caveats": "추천 기술은 관찰된 원 사이트 기술이 아닙니다.",
        }],
    }


def test_strict_schema_uses_required_and_no_extra_fields():
    schema = response_json_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    for p in ("backend_assessments", "chart_api_assessments", "implementation_suggestions"):
        v = schema["properties"][p]["items"]
        assert v["additionalProperties"] is False
        assert set(v["required"]) == set(v["properties"])


def test_valid_report_and_nonexistent_reference_rejected():
    payload = build_llm_payload(fixture())
    report = valid_output(payload)
    assert validate_llm_output(report, payload) == report
    tamper = json.loads(json.dumps(report))
    tamper["backend_assessments"][0]["finding_id"] = "fake-finding"
    with pytest.raises(LLMValidationError):
        validate_llm_output(tamper, payload)
    tamper = json.loads(json.dumps(report))
    tamper["chart_api_assessments"][0]["endpoint_id"] = "not-observed"
    with pytest.raises(LLMValidationError):
        validate_llm_output(tamper, payload)
    tamper = json.loads(json.dumps(report))
    tamper["backend_assessments"][0]["evidence_ids"] = ["unknown-evidence"]
    with pytest.raises(LLMValidationError):
        validate_llm_output(tamper, payload)


def test_model_cannot_set_score_extra_fields_or_duplicate_keys():
    payload = build_llm_payload(fixture())
    report = valid_output(payload)
    report["backend_assessments"][0]["confidence"] = 1.0
    with pytest.raises(LLMValidationError):
        validate_llm_output(report, payload)
    assert "confidence" not in response_json_schema()["properties"]
    with pytest.raises(LLMValidationError):
        validate_llm_output('{"summary":"one","summary":"two"}', payload)


def test_unseen_technology_as_finding_ref_and_in_narrative_rejected():
    payload = build_llm_payload(fixture())
    report = valid_output(payload)
    report["backend_assessments"][0]["explanation"] = "Spring Boot 서버임이 확정됩니다."
    with pytest.raises(LLMValidationError):
        validate_llm_output(report, payload)


def test_refuses_freeform_structure_or_oversize_text():
    payload = build_llm_payload(fixture())
    report = valid_output(payload)
    report["summary"] = "A" * 901
    with pytest.raises(LLMValidationError):
        validate_llm_output(report, payload)
    report = valid_output(payload)
    report["chart_api_assessments"].append({"other": "nonexistent"})
    with pytest.raises(LLMValidationError):
        validate_llm_output(report, payload)
