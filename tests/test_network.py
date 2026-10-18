"""Fast offline unit tests of the passive network collector (no browser required)."""
from __future__ import annotations

import json

from scanner.models import blank_result
from scanner.network import (MAX_JSON_BYTES, MAX_ENDPOINTS, NetworkCollector,
                             _is_graphql, _json_shape, _length, _mime)


class FakeRequest:
    resource_type = 'fetch'
    method = 'GET'

    def __init__(self, url, *, transfer_bytes=None, size_error=False):
        self.url = url
        self.transfer_bytes = transfer_bytes
        self.size_error = size_error

    def sizes(self):
        if self.size_error:
            raise RuntimeError('measurement unavailable')
        return {} if self.transfer_bytes is None else {'responseBodySize': self.transfer_bytes}


class FakeResponse:
    status = 200

    def __init__(self, request, body, *, mime='application/json', declared=None, encoding=None):
        self.request = request
        self._body = body
        self.body_calls = 0
        self.headers = {'content-type': mime}
        if declared is not None:
            self.headers['content-length'] = str(declared)
        if encoding:
            self.headers['content-encoding'] = encoding

    def body(self):
        self.body_calls += 1
        return self._body


def test_value_free_types_depth_and_secret_keys():
    value = {'data': [{'date': 'PRIVATE_DATE', 'value': 23,
                       'password': 'PASSWORD_PRIVATE', 'null': None}],
             'token': 'TOKEN_PRIVATE', 'flag': False}
    shape = _json_shape(value)
    assert shape == {'data': [{'date': 'string', 'value': 'number',
                                '[REDACTED_KEY]': 'string', 'null': 'null'}],
                     '[REDACTED_KEY]': 'string', 'flag': 'boolean'}
    assert not any(secret in str(shape) for secret in ('PRIVATE_DATE', 'PASSWORD_PRIVATE', 'TOKEN_PRIVATE'))
    assert _json_shape([1, 'text', True]) == ['number', 'string', 'boolean']
    assert _json_shape({'x': {'x': {'x': {'x': {'x': {'x': 'SECRET'}}}}}})['x']['x']['x']['x']['x'] == 'truncated'


def test_observed_request_response_and_body_ephemeral():
    result = blank_result('https://example.test')
    collector = NetworkCollector(result)
    request = FakeRequest('https://example.test/graphql?access_token=NETWORK_PRIVATE')
    body = json.dumps({'data': [{'date': 'SECRET_DATE', 'value': 3}]}).encode()
    response = FakeResponse(request, body, declared=len(body))
    collector.on_request(request)
    collector.on_response(response)
    assert response.body_calls == 0
    collector.on_finished(request)
    collector.finalize()
    row = result['api']['endpoints'][0]
    assert row['id'] == 'api-0001'
    assert row['status'] == 200
    assert row['graphql_candidate'] is True
    assert row['method'] == 'GET'
    assert row['json_structure'] == {'data': [{'date': 'string', 'value': 'number'}]}
    assert row['response_body_analysis'] == 'structure_only'
    assert row['request_started_at_ms'] <= row['response_received_at_ms']
    assert response.body_calls == 1
    output = json.dumps(result, ensure_ascii=False)
    assert 'SECRET_DATE' not in output and 'NETWORK_PRIVATE' not in output
    assert result['api']['candidates'] == []


def test_unknown_size_large_non_json_invalid_and_failed_persist():
    result = blank_result('https://example.test')
    collector = NetworkCollector(result)
    scenarios = [
        ('unknown', b'{}', 'application/json', None, 'size_unknown'),
        ('large', b'{}', 'application/json', MAX_JSON_BYTES + 1, 'too_large'),
        ('plain', b'private', 'text/plain', 7, 'non_json'),
        ('badjson', b'not json', 'application/json', 8, 'invalid_json'),
    ]
    for path, body, mime, size, expected in scenarios:
        req = FakeRequest('https://example.test/api/' + path)
        res = FakeResponse(req, body, mime=mime, declared=size)
        collector.on_request(req)
        collector.on_response(res)
        collector.on_finished(req)
        collector.finalize()
        row = result['api']['endpoints'][-1]
        assert row['response_body_analysis'] == expected
        assert res.body_calls == (1 if expected == 'invalid_json' else 0)
    failed = FakeRequest('https://example.test/api/failed')
    collector.on_request(failed)
    collector.on_failed(failed)
    assert result['api']['endpoints'][-1]['response_body_analysis'] == 'request_failed'
    assert all(e['json_structure'] is None for e in result['api']['endpoints'])


def test_bounded_request_list_and_mime_graphql():
    result = blank_result('https://example.test')
    c = NetworkCollector(result)
    for i in range(MAX_ENDPOINTS + 5):
        c.on_request(FakeRequest(f'https://example.test/api/{i}'))
    c.finalize()
    assert len(result['api']['endpoints']) == MAX_ENDPOINTS
    assert any('상한' in w for w in result['warnings'])
    assert _mime({'content-type': 'application/problem+json; charset=utf-8'}) == 'application/problem+json'
    assert _mime({'content-type': 'text/plain\r\nTOKEN_PRIVATE'}) is None
    assert _length({'content-length': 'unknown'}) is None
    assert _is_graphql('https://example.test/graphql', None)
    assert not _is_graphql('https://example.test/api/data', 'application/json')


def test_missing_content_length_uses_finished_measured_bytes_only():
    result = blank_result('https://example.test')
    collector = NetworkCollector(result, allow_unknown_length=True)
    body = json.dumps({'points': [{'date': 'SENSITIVE_DATE',
                                    'value': 14, 'token': 'SENSITIVE_TOKEN'}]}).encode()
    req = FakeRequest('https://example.test/api/chunked?access_token=PRIVATE',
                      transfer_bytes=len(body))
    response = FakeResponse(req, body)
    collector.on_request(req)
    collector.on_response(response)
    row = result['api']['endpoints'][0]
    assert row['response_body_analysis'] == 'waiting_for_finished_size_check'
    collector.flush_completed()
    assert response.body_calls == 0
    collector.on_finished(req)
    assert row['response_body_analysis'] == 'ready'
    collector.finalize()
    assert row['response_body_analysis'] == 'structure_only'
    assert row['json_structure'] == {'points': [{'date': 'string', 'value': 'number',
                                                 '[REDACTED_KEY]': 'string'}]}
    assert response.body_calls == 1
    serialized = json.dumps(result)
    for secret in ('SENSITIVE_DATE', 'SENSITIVE_TOKEN', 'PRIVATE'):
        assert secret not in serialized


def test_missing_length_rejects_large_compressed_or_unmeasurable_body_without_read():
    for transfer_bytes, encoding, size_error, expected in [
        (MAX_JSON_BYTES + 1, None, False, 'too_large'),
        (123, 'gzip', False, 'compressed_size_unknown'),
        (123, 'br', False, 'compressed_size_unknown'),
        (None, None, True, 'size_unknown'),
        (None, None, False, 'size_unknown'),
    ]:
        data = blank_result('https://example.test')
        c = NetworkCollector(data, allow_unknown_length=True)
        req = FakeRequest('https://example.test/api/test',
                          transfer_bytes=transfer_bytes, size_error=size_error)
        response = FakeResponse(req, b'{"password":"SENSITIVE"}', encoding=encoding)
        c.on_request(req)
        c.on_response(response)
        c.on_finished(req)
        c.finalize()
        row = data['api']['endpoints'][0]
        assert row['response_body_analysis'] == expected
        assert row['json_structure'] is None
        assert response.body_calls == 0
        assert 'SENSITIVE' not in json.dumps(data)


def test_missing_length_measurement_underreports_but_decoded_body_exceeds_limit():
    data = blank_result('https://example.test')
    collector = NetworkCollector(data, allow_unknown_length=True)
    req = FakeRequest('https://example.test/api/chunked', transfer_bytes=32)
    response = FakeResponse(req, b'{' + b' ' * MAX_JSON_BYTES + b'}')
    collector.on_request(req)
    collector.on_response(response)
    collector.on_finished(req)
    collector.finalize()
    row = data['api']['endpoints'][0]
    assert row['response_body_analysis'] == 'decoded_too_large'
    assert row['json_structure'] is None
    assert response.body_calls == 1
