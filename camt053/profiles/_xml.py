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

"""Internal XML helpers shared by every profile.

Kept private (leading underscore module) so the profile public surface
stays minimal.
"""

from __future__ import annotations

from typing import Any

from defusedxml.ElementTree import ParseError
from defusedxml.ElementTree import fromstring as _defused_fromstring


def parse_xml(xml: str) -> Any | None:
    """Return the root element of ``xml`` or ``None`` on parse failure.

    Always goes through ``defusedxml`` so payloads with DOCTYPE,
    entity expansion, or external references are refused.
    """
    try:
        return _defused_fromstring(xml)
    except (ParseError, ValueError):
        return None


def local_name(tag: str) -> str:
    """Strip the XML namespace from a tag.

    ``"{urn:iso:std:iso:20022:tech:xsd:camt.053.001.13}BkToCstmrStmt"``
    becomes ``"BkToCstmrStmt"``.
    """
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def iter_descendants(root: Any, name: str):
    """Yield every descendant whose local name equals ``name``."""
    for elem in root.iter():
        if local_name(elem.tag) == name:
            yield elem


def has_child(elem: Any, name: str) -> bool:
    """Return ``True`` iff ``elem`` has a direct child with local name ``name``."""
    return any(local_name(c.tag) == name for c in elem)
