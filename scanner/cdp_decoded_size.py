"""Read-only CDP decoded-size metadata for Step 3's approved main-frame JSON.

CDP Network.dataReceived.dataLength counts decoded bytes even for gzip/br.
Only numeric lengths and transient request identifiers are observed: no data,
headers, response bodies, cookies, or CDP resource dumps. The caller must
ensure origin and auth scopes before the metadata is used for a body read.
"""
from __future__ import annotations

from .network import MAX_JSON_BYTES

MAX_CDP_TRACKED_REQUESTS = 300


class DecodedLengthTracker:
    """Observe network lengths without streaming/request interception.

    Exact association is intentionally conservative: duplicate same-URL,
    same-method requests on a page are ambiguous and must be excluded.
    """

    def __init__(self, allow_url):
        self.allow_url = allow_url
        self._sessions = []
        self._by_page = {}
        self._total = 0

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

        def received(event):
            state = active.get(event.get('requestId'))
            if state is None:
                return
            n = event.get('dataLength')
            if type(n) is not int or n < 0:
                state['invalid'] = True
                return
            state['events'] += 1
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

    def clear(self):
        self._by_page.clear()
        self._sessions.clear()
