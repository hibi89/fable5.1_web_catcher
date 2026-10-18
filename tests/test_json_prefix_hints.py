"""Bounded prefix field hints never become full JSON schema or raw values."""
import json

from scanner.json_prefix_hints import infer_prefix_fields, MAX_PREFIX_BYTES


def test_nested_large_json_first_row_produces_only_safe_fields():
    raw = (b'{"items":[{"date":"PRIVATE_DATE_VALUE","value":14,'
           b'"access_token":"PRIVATE_SECRET","enabled":true},'
           b'{"date":"SHOULD_NOT_PARSE_YET"')
    result = infer_prefix_fields(raw)
    assert result == {
        'sample_kind': 'first_complete_object',
        'completeness': 'partial_prefix_only',
        'fields': {'date': 'string', 'value': 'number',
                   '[REDACTED_KEY]': 'string', 'enabled': 'boolean'},
    }
    data = json.dumps(result)
    assert 'PRIVATE_' not in data
    assert 'SHOULD_NOT_PARSE_YET' not in data


def test_string_braces_and_truncated_utf8_do_not_create_false_objects():
    raw = b'{"items":[{"message":"{ } \\\" } secret", "value":3},'
    result = infer_prefix_fields(raw)
    assert result is not None
    assert result['fields'] == {'message': 'string', 'value': 'number'}
    assert infer_prefix_fields(b'{"items":["{\"false\":1}", 1,2,3,') is None
    assert infer_prefix_fields(b'{"items":[{"x":1]') is None


def test_hints_reject_non_json_root_and_oversized_prefix():
    assert infer_prefix_fields(b'<script>{"x":1}</script>') is None
    assert infer_prefix_fields(b' ') is None
    assert infer_prefix_fields(b'[' + b' ' * MAX_PREFIX_BYTES) is None
