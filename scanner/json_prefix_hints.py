"""Bounded, partial JSON *field hints* from approved response stream prefixes.

A prefix cannot establish the full schema; never reuse these hints as chart/API
lineage evidence. CDP events may contain sensitive values, which are held only
in a short-lived capped bytearray. Only sanitized field/type hints persist.
"""
from __future__ import annotations

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


