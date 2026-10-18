"""Bounded, partial JSON *field hints* from approved response stream prefixes.

A prefix cannot establish the full schema; never reuse these hints as chart/API
lineage evidence. CDP events may contain sensitive values, which are held only
in a short-lived capped bytearray. Only sanitized field/type hints persist.
"""
from __future__ import annotations

import base64
import json

from .network import _json_shape

MAX_PREFIX_BYTES = 32_768
MAX_PREFIX_STREAMS = 20
MAX_PREFIX_HINTS = 10


def infer_prefix_fields(prefix: bytes):
    """Find first *complete* object inside a JSON root, not a full schema.

    The input may end in the middle of a multibyte UTF-8 codepoint or string.
    Reject invalid JSON roots; balance braces with string/escape awareness.
    We parse a single <=32KiB sample object using the same safe _json_shape.
    """
    if not isinstance(prefix, bytes) or not prefix or len(prefix) > MAX_PREFIX_BYTES:
        return None
    text = prefix.decode('utf-8', errors='ignore')
    if not text.lstrip().startswith(('{', '[')):
        return None
    stack = []
    quoted = False
    escaped = False
    for i, char in enumerate(text):
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
        elif char in ('{', '['):
            stack.append((char, i))
        elif char in ('}', ']'):
            if not stack:
                return None
            opening, start = stack.pop()
            if (opening, char) not in (('{', '}'), ('[', ']')):
                return None
            if char == '}':
                try:
                    value = json.loads(text[start:i + 1])
                except (ValueError, TypeError):
                    continue
                if isinstance(value, dict):
                    # The structure is of ONE completed object, not the
                    # entire response or necessarily even a whole row set.
                    return {'sample_kind': 'first_complete_object',
                            'completeness': 'partial_prefix_only',
                            'fields': _json_shape(value)}
    return None


class PrefixHintTracker:
    """Activate CDP streaming at requestWillBeSent, *before* fast responses finish."""

    def __init__(self, allow_url):
        self.allow_url = allow_url
        self._sessions = []
        self._pages = {}
        self._total = 0

    def attach_page(self, context, page):
        try:
            session = context.new_cdp_session(page)
            frame = session.send('Page.getFrameTree')['frameTree']['frame']['id']
            session.send('Network.enable')
        except Exception:
            return False
        by_request_id = {}
        by_key = {}
        self._pages[page] = by_key
        self._sessions.append(session)

        def append(state, data):
            if state['invalid'] or state['limit'] or not data:
                return
            if not isinstance(data, str):
                state['invalid'] = True
                return
            available = MAX_PREFIX_BYTES - len(state['prefix'])
            if available <= 0:
                state['limit'] = True
                return
            # Decode a bounded base64 prefix; never duplicate an unbounded
            # CDP data event by decoding it in full.
            take = min(len(data), ((available + 2) // 3) * 4)
            take -= take % 4
            if take <= 0:
                state['limit'] = True
                return
            try:
                sample = base64.b64decode(data[:take], validate=True)
            except (ValueError, base64.binascii.Error):
                state['invalid'] = True
                return
            state['prefix'].extend(sample[:available])
            if len(sample) > available or take < len(data) or len(state['prefix']) >= MAX_PREFIX_BYTES:
                state['limit'] = True

        def requested(event):
            if self._total >= MAX_PREFIX_STREAMS:
                return
            if event.get('frameId') != frame or event.get('type') not in ('Fetch', 'XHR'):
                return
            info = event.get('request') or {}
            url, method = info.get('url'), info.get('method')
            ident = event.get('requestId')
            if not all(isinstance(x, str) and x for x in (url, method, ident)):
                return
            if not self.allow_url(url):
                return
            state = {'prefix': bytearray(), 'invalid': False, 'limit': False,
                     'done': False, 'failed': False, 'enabled': False}
            by_request_id[ident] = state
            by_key.setdefault((url, method), []).append(state)
            self._total += 1
            try:
                answer = session.send('Network.streamResourceContent', {'requestId': ident})
                state['enabled'] = True
                append(state, answer.get('bufferedData', ''))
            except Exception:
                # Fail closed for request races, protocol incompatibility, etc.
                state['invalid'] = True

        def received(event):
            state = by_request_id.get(event.get('requestId'))
            if state is not None:
                append(state, event.get('data', ''))

        def finished(event):
            state = by_request_id.pop(event.get('requestId'), None)
            if state is not None:
                state['done'] = True

        def failed(event):
            state = by_request_id.pop(event.get('requestId'), None)
            if state is not None:
                state['failed'] = True
                state['done'] = True

        session.on('Network.requestWillBeSent', requested)
        session.on('Network.dataReceived', received)
        session.on('Network.loadingFinished', finished)
        session.on('Network.loadingFailed', failed)
        return True

    def hint_for(self, request):
        try:
            page = request.frame.page
            candidates = self._pages.get(page, {}).get((request.url, request.method), ())
            if len(candidates) != 1:
                return None
            state = candidates[0]
            if (not state['enabled'] or not state['done'] or
                    state['failed'] or state['invalid']):
                return None
            return infer_prefix_fields(bytes(state['prefix']))
        except Exception:
            return None

    def clear(self):
        # Release raw prefix buffers as soon as Record ends.
        self._pages.clear()
        self._sessions.clear()
