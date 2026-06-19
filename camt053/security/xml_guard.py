# Copyright (C) 2023-2026 Sebastien Rousseau.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Defense-in-depth limits for untrusted XML payloads.

The statement parser already neutralises XXE and entity-expansion attacks by
parsing with :mod:`defusedxml`. This module adds a cheap, parser-agnostic
*pre-flight* check that callers (notably the REST API) run **before** parsing,
so obviously hostile payloads are rejected without engaging the XML parser at
all:

* a configurable **maximum byte size** (reject oversized payloads early), and
* a refusal of any inline **DTD / entity declaration** (``<!DOCTYPE`` /
  ``<!ENTITY``), the vector behind classic XXE and "billion laughs"
  entity-expansion bombs.

These checks are deliberately conservative and string-based: real camt.05x
statements never carry a DOCTYPE, so rejecting them outright costs nothing and
closes the attack surface defence-in-depth alongside :mod:`defusedxml`.
"""

from __future__ import annotations

import re

__all__ = [
    "XmlSecurityError",
    "DEFAULT_MAX_XML_BYTES",
    "guard_xml_payload",
]

#: The default maximum accepted XML payload size, in bytes (1 MiB). Generous
#: for real statements yet small enough to bound parser work on hostile input.
DEFAULT_MAX_XML_BYTES = 1_048_576

# Matches an inline DTD or entity declaration anywhere in the document. ``(?i)``
# keeps it case-insensitive; the parser tolerates leading whitespace / BOM, so
# we scan the whole payload rather than only its prefix.
_DOCTYPE_RE = re.compile(r"<!(?:DOCTYPE|ENTITY)\b", re.IGNORECASE)


class XmlSecurityError(ValueError):
    """Raised when an XML payload violates a security limit.

    Carries a stable :attr:`reason` so callers (e.g. the REST layer) can map
    the failure onto a precise status code: ``"too_large"`` for an oversized
    payload, ``"doctype_forbidden"`` for an inline DTD / entity declaration.
    """

    def __init__(self, message: str, *, reason: str) -> None:
        """Initialise with a human message and a machine-readable reason."""
        super().__init__(message)
        self.reason = reason


def guard_xml_payload(
    xml: str,
    *,
    max_bytes: int = DEFAULT_MAX_XML_BYTES,
) -> None:
    """Reject an XML payload that breaches a configured security limit.

    Run this before handing untrusted XML to the parser. It enforces a maximum
    encoded size and refuses any inline DTD / entity declaration.

    Args:
        xml: The raw XML payload as a string.
        max_bytes: The maximum accepted UTF-8 size in bytes (default
            :data:`DEFAULT_MAX_XML_BYTES`).

    Raises:
        XmlSecurityError: If the payload exceeds ``max_bytes``
            (``reason="too_large"``) or contains a ``<!DOCTYPE`` / ``<!ENTITY``
            declaration (``reason="doctype_forbidden"``).
    """
    size = len(xml.encode("utf-8"))
    if size > max_bytes:
        raise XmlSecurityError(
            f"XML payload is too large: {size} bytes exceeds the "
            f"{max_bytes}-byte limit.",
            reason="too_large",
        )
    if _DOCTYPE_RE.search(xml):
        raise XmlSecurityError(
            "XML payload contains a DOCTYPE or ENTITY declaration, which is "
            "rejected to prevent XXE and entity-expansion attacks.",
            reason="doctype_forbidden",
        )
