"""Passive, bounded XHR/fetch metadata and value-free JSON shape collection.

Only requests actually observed by the page are recorded. Browser responses are
read *after* requestfinished, never while dispatching Playwright callbacks.
"""
from __future__ import annotations

import json
import re
import time
from urllib.parse import urlsplit

from .sanitize import SECRET_KEYS, safe_text, safe_url

MAX_ENDPOINTS = 150
MAX_JSON_BODIES = 20
MAX_JSON_BYTES = 131_072
MAX_SHAPE_DEPTH = 5
MAX_OBJECT_KEYS = 24
MAX_ARRAY_SAMPLES = 3
_CONTENT_TYPE = re.compile(r'^[a-z0-9!#$&^_.+\-]+/[a-z0-9!#$&^_.+\-]+$', re.I)
_GRAPHQL_PATH = re.compile(r'/(?:graphql|gql)(?:/|$)', re.I)


def _clock_ms() -> int:
    """Epoch milliseconds shared with JS performance.timeOrigin + performance.now."""
    return int(time.time() * 1000)


def _json_shape(value, depth: int = 0):
    """Type/field-only structure. Never copy primitive response values."""
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, (int, float)):
        return 'number'
    if isinstance(value, str):
        return 'string'
    if depth >= MAX_SHAPE_DEPTH:
        return 'truncated'
    if isinstance(value, list):
        shapes = []
        for item in value[:MAX_ARRAY_SAMPLES]:
            shape = _json_shape(item, depth + 1)
            if shape not in shapes:
                shapes.append(shape)
        return shapes[:MAX_ARRAY_SAMPLES]
    if isinstance(value, dict):
        result = {}
        for key in list(value)[:MAX_OBJECT_KEYS]:
            name = '[REDACTED_KEY]' if SECRET_KEYS.search(str(key)) else safe_text(key, 60)
            if name in result:
                continue
            result[name] = _json_shape(value[key], depth + 1)
        if len(value) > MAX_OBJECT_KEYS:
            result['[more_keys]'] = 'truncated'
        return result
    return 'unknown'


def _mime(headers) -> str | None:
    raw = headers.get('content-type', '') if isinstance(headers, dict) else ''
    value = raw.split(';', 1)[0].strip().lower()
    return value if _CONTENT_TYPE.fullmatch(value) else None


def _length(headers) -> int | None:
    try:
        value = headers.get('content-length', '')
        if not re.fullmatch(r'\d{1,12}', value):
            return None
        return int(value)
    except (AttributeError, TypeError, ValueError):
        return None


def _safe_transfer_bytes(request) -> int | None:
    """Exact observed encoded body size, only after requestfinished.

    Playwright reports responseBodySize as encoded transfer bytes. Do not
    mistake the header count or missing measurement for a safe byte cap.
    The decoded body is also checked after reading. As with known-length
    responses, an absolute browser/decoder memory bound is not guaranteed.
    """
    try:
        count = request.sizes().get('responseBodySize')
        if type(count) is int and count >= 0:
            return count
    except Exception:
        pass
    return None


def _is_json(mime: str | None) -> bool:
    return bool(mime and (mime == 'application/json' or mime.endswith('+json')))


def _is_graphql(url: str, mime: str | None) -> bool:
    return bool(_GRAPHQL_PATH.search(urlsplit(url).path) or mime == 'application/graphql')


class NetworkCollector:
    """Attach four passive listeners before page.goto; flush after bounded wait."""

    def __init__(self, result: dict, *, allow_unknown_length: bool = False):
        self.result = result
        # Opt-in only for Step 3 Record; Step 2's original policy is immutable.
        self.allow_unknown_length = allow_unknown_length
        self.records = result['api']['endpoints']
        self._request_rows = {}
        self._body_queue = {}
        self._expected_decoded_bytes = {}  # CDP measurement, Record only.
        self._over_limit = False
        self._body_limit = False
        self._body_reads = 0
        self.max_endpoints = MAX_ENDPOINTS

    def attach(self, page):
        page.on('request', self.on_request)
        page.on('response', self.on_response)
        page.on('requestfinished', self.on_finished)
        page.on('requestfailed', self.on_failed)

    def on_request(self, request):
        if request.resource_type not in ('xhr', 'fetch'):
            return
        if len(self.records) >= self.max_endpoints:
            self._over_limit = True
            return
        url = request.url
        row = {
            'id': f'api-{len(self.records)+1:04d}',
            'url': safe_url(url),
            'method': request.method[:12],
            'resource_type': request.resource_type,
            'request_started_at_ms': _clock_ms(),
            'response_received_at_ms': None,
            'status': None,
            'content_type': None,
            'graphql_candidate': _is_graphql(url, None),
            'response_body_analysis': 'pending',
            'json_structure': None,
        }
        self.records.append(row)
        self._request_rows[request] = row

    def on_response(self, response):
        request = response.request
        row = self._request_rows.get(request)
        if row is None:
            return
        row['response_received_at_ms'] = _clock_ms()
        row['status'] = response.status
        headers = response.headers
        mime = _mime(headers)
        row['content_type'] = mime
        row['graphql_candidate'] = row['graphql_candidate'] or _is_graphql(request.url, mime)
        if not _is_json(mime):
            row['response_body_analysis'] = 'non_json'
            return
        length = _length(headers)
        if length is None and not self.allow_unknown_length:
            row['response_body_analysis'] = 'size_unknown'
        elif length is None:
            # A chunked/streamed JSON response can omit Content-Length.
            # At requestfinished consult Playwright's observed transfer size
            # before considering a body read. Compressed unknown-length
            # bodies have unbounded decoded size, so never use that fallback.
            row['response_body_analysis'] = 'waiting_for_finished_size_check'
            self._body_queue[request] = response
        elif length > MAX_JSON_BYTES:
            row['response_body_analysis'] = 'too_large'
        else:
            row['response_body_analysis'] = 'waiting_for_requestfinished'
            self._body_queue[request] = response

    def on_finished(self, request):
        row = self._request_rows.get(request)
        if row is None:
            return
        if row['response_body_analysis'] == 'waiting_for_requestfinished':
            row['response_body_analysis'] = 'ready'
        elif row['response_body_analysis'] == 'waiting_for_finished_size_check':
            response = self._body_queue.get(request)
            if response is None:
                row['response_body_analysis'] = 'size_unknown'
                return
            headers = response.headers
            encoding = headers.get('content-encoding', '').strip().lower()
            if encoding and encoding != 'identity':
                row['response_body_analysis'] = 'compressed_size_unknown'
                self._body_queue.pop(request, None)
                return
            wire_bytes = _safe_transfer_bytes(request)
            if wire_bytes is None:
                row['response_body_analysis'] = 'size_unknown'
                self._body_queue.pop(request, None)
            elif wire_bytes > MAX_JSON_BYTES:
                row['response_body_analysis'] = 'too_large'
                self._body_queue.pop(request, None)
            else:
                row['response_body_analysis'] = 'ready'

    def on_failed(self, request):
        row = self._request_rows.get(request)
        if row is not None:
            row['response_body_analysis'] = 'request_failed'
            self._body_queue.pop(request, None)

    def flush_completed(self):
        """Incrementally summarize finished responses before a Record navigation.

        Reuses the Step 2 parser and body/shape limits; does not clear pending
        request associations or wait for WebSocket/SSE streams.
        """
        for request, response in list(self._body_queue.items()):
            row = self._request_rows.get(request)
            if row is None or row['response_body_analysis'] != 'ready':
                continue
            if self._body_reads >= MAX_JSON_BODIES:
                self._body_limit = True
                row['response_body_analysis'] = 'body_read_limit'
                continue
            self._body_reads += 1
            try:
                body = response.body()  # Request completed; body stays ephemeral.
                expected = self._expected_decoded_bytes.pop(request, None)
                if expected is not None and len(body) != expected:
                    row['response_body_analysis'] = 'decoded_length_mismatch'
                    continue
                if len(body) > MAX_JSON_BYTES:
                    row['response_body_analysis'] = 'decoded_too_large'
                    continue
                data = json.loads(body)
                row['json_structure'] = _json_shape(data)
                row['response_body_analysis'] = 'structure_only'
            except (ValueError, TypeError, UnicodeError):
                row['response_body_analysis'] = 'invalid_json'
            except Exception:
                row['response_body_analysis'] = 'read_error'
            finally:
                self._body_queue.pop(request, None)
        # Release decoded-body candidates promptly; keep request metadata for mapping.
        for request, response in list(self._body_queue.items()):
            row = self._request_rows.get(request)
            if row is None or row['response_body_analysis'] not in (
                    'waiting_for_requestfinished', 'waiting_for_finished_size_check',
                    'cdp_decoded_waiting_finish', 'cdp_decoded_pending'):
                self._body_queue.pop(request, None)

    def finalize(self):
        """Final read before shutdown; preserve existing Step 2 semantics."""
        self.flush_completed()
        if self._over_limit:
            self.result['warnings'].append(f'XHR/fetch 수집 건수 상한 {self.max_endpoints}건 적용')
        if self._body_limit:
            self.result['warnings'].append(f'JSON 본문 분석 건수 상한 {MAX_JSON_BODIES}건 적용')
        self._request_rows.clear()
        self._body_queue.clear()
        self._expected_decoded_bytes.clear()
