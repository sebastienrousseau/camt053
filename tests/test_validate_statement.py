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

"""Tests for validating statements against the official ISO camt XSD."""

import os

import pytest

from camt053 import services
from camt053.exceptions import StatementParseError

GOLD = os.path.join(os.path.dirname(__file__), "gold_master")

# A well-formed camt.053.001.04 document missing the mandatory GrpHdr content.
_INVALID_DOC = (
    '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.04">'
    "<BkToCstmrStmt><GrpHdr></GrpHdr><Stmt></Stmt></BkToCstmrStmt>"
    "</Document>"
)

# A document whose namespace has no bundled official XSD.
_UNSUPPORTED_NS = (
    '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.99">'
    "<BkToCstmrStmt><Stmt><Id>X</Id></Stmt></BkToCstmrStmt></Document>"
)


def test_validate_official_business_sample():
    """The official business sample validates as valid."""
    with open(
        os.path.join(GOLD, "business_sample_camt.053.001.04.xml"),
        encoding="utf-8",
    ) as handle:
        xml = handle.read()
    report = services.validate_statement(xml)
    assert report["valid"] is True
    assert report["message_type"] == "camt.053.001.04"
    assert report["errors"] == []


def test_validate_invalid_document():
    """A well-formed but schema-invalid document reports errors."""
    report = services.validate_statement(_INVALID_DOC)
    assert report["valid"] is False
    assert report["message_type"] == "camt.053.001.04"
    assert report["errors"]


def test_validate_unsupported_namespace_raises():
    """A namespace with no bundled XSD raises a clear typed error."""
    with pytest.raises(StatementParseError, match="No bundled XSD"):
        services.validate_statement(_UNSUPPORTED_NS)


def test_validate_malformed_xml_raises():
    """Malformed XML raises a parse error from the facade."""
    with pytest.raises(StatementParseError):
        services.validate_statement("<not-a-doc")
