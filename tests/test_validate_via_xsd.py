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

"""Tests for XSD validation helpers."""

import os

from camt053.constants import REVERSAL_MESSAGE_TYPE
from camt053.parse import parse_statement
from camt053.xml.generate_xml import generate_reversal_for_statement
from camt053.xml.validate_via_xsd import (
    validate_via_xsd,
    validate_xml_string_via_xsd,
)

XSD = os.path.join(
    os.path.dirname(__file__),
    "..",
    "camt053",
    "templates",
    REVERSAL_MESSAGE_TYPE,
    f"{REVERSAL_MESSAGE_TYPE}.xsd",
)


def test_validate_file_valid(tmp_path, statement_xml):
    """A generated reversal written to disk validates against the XSD."""
    reversal = generate_reversal_for_statement(
        parse_statement(statement_xml), "AC04"
    )
    path = tmp_path / "reversal.xml"
    path.write_text(reversal)
    assert validate_via_xsd(str(path), XSD) is True


def test_validate_file_invalid_xml(tmp_path):
    """A non-conforming document fails file validation."""
    path = tmp_path / "bad.xml"
    path.write_text(
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:'
        'camt.053.001.14"><BkToCstmrStmt/></Document>'
    )
    assert validate_via_xsd(str(path), XSD) is False


def test_validate_file_parse_error(tmp_path):
    """A malformed XML file fails gracefully (returns False)."""
    path = tmp_path / "broken.xml"
    path.write_text("<Document><unclosed>")
    assert validate_via_xsd(str(path), XSD) is False


def test_validate_missing_xsd(tmp_path, statement_xml):
    """A missing XSD path fails gracefully."""
    path = tmp_path / "doc.xml"
    path.write_text(
        generate_reversal_for_statement(parse_statement(statement_xml), "AC04")
    )
    assert validate_via_xsd(str(path), str(tmp_path / "nope.xsd")) is False


def test_validate_string_invalid():
    """A malformed XML string fails string validation."""
    assert validate_xml_string_via_xsd("<nope", XSD) is False


def test_validate_string_bad_xsd():
    """A missing XSD path fails string validation."""
    assert validate_xml_string_via_xsd("<Document/>", "/no/such.xsd") is False
