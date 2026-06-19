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

"""Security tests for the untrusted-XML defense-in-depth guard."""

import pytest

from camt053 import services
from camt053.security.xml_guard import (
    DEFAULT_MAX_XML_BYTES,
    XmlSecurityError,
    guard_xml_payload,
)

pytestmark = pytest.mark.security

_BILLION_LAUGHS = """<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
]>
<Document>&lol2;</Document>"""

_XXE = """<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<Document>&xxe;</Document>"""


def test_guard_accepts_clean_payload(statement_xml):
    """A normal statement passes the guard untouched."""
    assert guard_xml_payload(statement_xml) is None


def test_guard_rejects_oversized_payload():
    """A payload over the byte limit raises with reason too_large."""
    with pytest.raises(XmlSecurityError) as exc:
        guard_xml_payload("<a/>" + "x" * 100, max_bytes=10)
    assert exc.value.reason == "too_large"


def test_guard_rejects_doctype():
    """A billion-laughs DOCTYPE payload is refused before parsing."""
    with pytest.raises(XmlSecurityError) as exc:
        guard_xml_payload(_BILLION_LAUGHS)
    assert exc.value.reason == "doctype_forbidden"


def test_guard_rejects_xxe_entity():
    """An XXE external-entity payload is refused before parsing."""
    with pytest.raises(XmlSecurityError) as exc:
        guard_xml_payload(_XXE)
    assert exc.value.reason == "doctype_forbidden"


def test_guard_default_limit_is_one_mib():
    """The default limit is the documented 1 MiB."""
    assert DEFAULT_MAX_XML_BYTES == 1_048_576


def test_services_guard_xml_facade_rejects():
    """The services facade enforces the same guard."""
    with pytest.raises(XmlSecurityError):
        services.guard_xml(_XXE)


def test_services_guard_xml_facade_accepts(statement_xml):
    """The services facade passes a clean payload."""
    assert services.guard_xml(statement_xml) is None
