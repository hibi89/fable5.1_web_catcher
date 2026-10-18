"""Read-only CDP decoded-size metadata for Step 3's approved main-frame JSON.

CDP Network.dataReceived.dataLength counts decoded bytes even for gzip/br.
Only numeric lengths and transient request identifiers are observed: no data,
headers, response bodies, cookies, or CDP resource dumps. The caller must
ensure origin and auth scopes before the metadata is used for a body read.
"""
from __future__ import annotations

import base64
import binascii

from .network import MAX_JSON_BYTES
from .json_prefix_hints import (MAX_PREFIX_BYTES, MAX_PREFIX_STREAMS,
                                infer_prefix_fields)

MAX_CDP_TRACKED_REQUESTS = 300


class DecodedLengthTracker:
    """Observe network lengths without streaming/request interception.

    Exact association is intentionally conservative: duplicate same-URL,
    same-method requests on a page are ambiguous and must be excluded.
    """

    def __init__(self, allow_url, *, capture_prefix=False):
        self.allow_url = allow_url
        self.capture_prefix = capture_prefix
        self._sessions = []
        self._by_page = {}
        self._total = 0
        self._prefix_streams = 0

    def attach_page(self, context, page):
        try:
            session = context.new_cdp_session(page)
            # Session is per page and only reports numeric dataLength;
            # never request response bodies using CDP.
            frame_tree = session.send('Page.getFrameTree')
            main_frame = frame_tree['frameTree']['frame']['id']
            session.send('Network.enable')
        except Exception:
            return False
        active = {}
        matches = {}
        self._by_page[page] = matches
        self._sessions.append(session)

        def append_prefix(state, data):
            prefix = state.get('prefix')
            if prefix is None or state.get('prefix_invalid') or not data:
                return
            if not isinstance(data, str):
                state['prefix_invalid'] = True
                return
            space = MAX_PREFIX_BYTES - len(prefix)
            if space <= 0:
                return
            take = min(len(data), ((space + 2) // 3) * 4)
            take -= take % 4
            if take <= 0:
                return
            try:
                chunk = base64.b64decode(data[:take], validate=True)
            except (ValueError, binascii.Error):
                state['prefix_invalid'] = True
                return
            prefix.extend(chunk[:space])

        def requested(event):
            if self._total >= MAX_CDP_TRACKED_REQUESTS:
                return
            if event.get('frameId') != main_frame:
                return
            request = event.get('request') or {}
            url = request.get('url')
            method = request.get('method')
            if not isinstance(url, str) or not isinstance(method, str):
                return
            if not self.allow_url(url):
                return
            ident = event.get('requestId')
            if not isinstance(ident, str) or not ident:
                return
            state = {'decoded': 0, 'over': False, 'invalid': False,
                     'events': 0, 'done': False, 'failed': False}
            active[ident] = state
            matches.setdefault((url, method), []).append(state)
            self._total += 1
            if (self.capture_prefix and self._prefix_streams < MAX_PREFIX_STREAMS
                    and event.get('type') in ('Fetch', 'XHR')):
                self._prefix_streams += 1
                state['prefix'] = bytearray()
                state['prefix_invalid'] = False
                try:
                    answer = session.send('Network.streamResourceContent',
                                          {'requestId': ident})
                    state['prefix_enabled'] = True
                    append_prefix(state, answer.get('bufferedData', ''))
                except Exception:
                    state['prefix_invalid'] = True

        def received(event):
            state = active.get(event.get('requestId'))
            if state is None:
                return
            n = event.get('dataLength')
            if type(n) is not int or n < 0:
                state['invalid'] = True
                return
            state['events'] += 1
            if state.get('prefix_enabled'):
                append_prefix(state, event.get('data', ''))
            # Saturate at CAP+1 to keep arithmetic bounded.
            if n > MAX_JSON_BYTES - state['decoded']:
                state['decoded'] = MAX_JSON_BYTES + 1
                state['over'] = True
            else:
                state['decoded'] += n

        def finished(event):
            state = active.pop(event.get('requestId'), None)
            if state is not None:
                state['done'] = True

        def failed(event):
            state = active.pop(event.get('requestId'), None)
            if state is not None:
                state['failed'] = True
                state['done'] = True

        session.on('Network.requestWillBeSent', requested)
        session.on('Network.dataReceived', received)
        session.on('Network.loadingFinished', finished)
        session.on('Network.loadingFailed', failed)
        return True

    def decide(self, request):
        """Return (status, decoded_bytes), never infer from encoded bytes.

        'pending': wait for CDP loadingFinished; 'ready': already completed
        with measured decoded length <=128KiB. False negatives are fine.
        """
        try:
            page = request.frame.page
            key = (request.url, request.method)
            matches = self._by_page.get(page, {}).get(key, ())
            if len(matches) != 1:
                return ('ambiguous_or_missing', None)
            state = matches[0]
            if not state['done']:
                return ('pending', None)
            if state['failed'] or state['invalid'] or state['events'] == 0:
                return ('invalid_or_missing', None)
            if state['over'] or state['decoded'] > MAX_JSON_BYTES:
                return ('decoded_too_large', None)
            if state['decoded'] <= 0:
                return ('invalid_or_missing', None)
            return ('ready', state['decoded'])
        except Exception:
            return ('invalid_or_missing', None)

    def refusal_reason(self, request):
        """Value-free status for a CDP-observation refusal.

        This is metadata only. It never contains request URL, ID, body,
        headers, origin, private field name, or timing identifier.
        """
        try:
            matches = self._by_page.get(request.frame.page, {}).get(
                (request.url, request.method), ())
            if len(matches) == 0:
                return 'request_unmatched'
            if len(matches) > 1:
                return 'request_ambiguous'
            state = matches[0]
            if state['failed']:
                return 'loading_failed'
            if state['invalid']:
                return 'invalid_data_length'
            if not state['done']:
                return 'loading_incomplete'
            if state['events'] == 0:
                return 'no_data_events'
            if state['over']:
                return 'exceeds_decoded_cap'
            if state['decoded'] <= 0:
                return 'nonpositive_decoded_length'
            return 'ready'
        except Exception:
            return 'diagnostic_unavailable'

    def hint_for(self, request):
        """A first-object type sample only; never a complete response schema."""
        try:
            page = request.frame.page
            key = (request.url, request.method)
            matches = self._by_page.get(page, {}).get(key, ())
            if len(matches) != 1:
                return None
            state = matches[0]
            if (not state['done'] or state['failed'] or
                    not state.get('prefix_enabled') or state.get('prefix_invalid')):
                return None
            return infer_prefix_fields(bytes(state.get('prefix', b'')))
        except Exception:
            return None

    def clear(self):
        self._by_page.clear()
        self._sessions.clear()
