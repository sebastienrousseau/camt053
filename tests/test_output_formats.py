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

"""Tests for reversal output-version selection and the pacs.004 format."""

import pytest

from camt053 import services
from camt053.constants import (
    PACS_RETURN_MESSAGE_TYPE,
    REVERSAL_MESSAGE_TYPE,
)
from camt053.exceptions import ReversalGenerationError
from camt053.xml.generate_xml import generate_reversal_xml
from camt053.xml.validate_via_xsd import validate_xml_string_via_xsd
from camt053.constants import TEMPLATES_DIR


def _xsd_for(message_type: str) -> str:
    """Return the bundled XSD path for a generated message type."""
    return str(TEMPLATES_DIR / message_type / f"{message_type}.xsd")


def test_default_version_is_camt_053_001_14(statement_xml):
    """The default reversal keeps the camt.053.001.14 namespace."""
    xml = services.generate_reversal(statement_xml)
    assert REVERSAL_MESSAGE_TYPE in xml
    assert validate_xml_string_via_xsd(xml, _xsd_for(REVERSAL_MESSAGE_TYPE))


def test_select_camt_053_001_08_version(statement_xml):
    """A caller can select the bundled camt.053.001.08 schema version."""
    xml = services.generate_reversal(statement_xml, version="camt.053.001.08")
    assert "camt.053.001.08" in xml
    assert "camt.053.001.14" not in xml
    assert validate_xml_string_via_xsd(xml, _xsd_for("camt.053.001.08"))


def test_unknown_version_raises(statement_xml):
    """An unknown camt.053 version is rejected with a clear error."""
    with pytest.raises(ReversalGenerationError, match="Unknown camt.053"):
        services.generate_reversal(statement_xml, version="camt.053.001.99")


def test_unknown_output_format_raises(statement_xml):
    """An unknown output format is rejected with a clear error."""
    with pytest.raises(ReversalGenerationError, match="Unknown output format"):
        services.generate_reversal(statement_xml, output_format="bogus")


def test_pacs004_output_validates_and_echoes_reason(statement_xml):
    """The pacs.004 PaymentReturn validates and carries the return reason."""
    xml = services.generate_reversal(statement_xml, output_format="pacs004")
    assert PACS_RETURN_MESSAGE_TYPE in xml
    assert "<PmtRtr>" in xml
    assert "<RtrRsnInf>" in xml
    assert "<Cd>AC04</Cd>" in xml
    assert validate_xml_string_via_xsd(xml, _xsd_for(PACS_RETURN_MESSAGE_TYPE))


def test_pacs004_carries_returned_amount(statement_xml):
    """The pacs.004 return carries the returned instructed amount."""
    xml = services.generate_reversal(statement_xml, output_format="pacs004")
    assert '<RtrdInstdAmt Ccy="EUR">1500.00</RtrdInstdAmt>' in xml


def test_pacs004_reason_flips_for_different_code(statement_xml):
    """Selecting another reason echoes that code into the pacs.004 return."""
    xml = services.generate_reversal(
        statement_xml, reason_code="AC06", output_format="pacs004"
    )
    assert "<Cd>AC06</Cd>" in xml
    assert "<Cd>AC04</Cd>" not in xml


def test_generate_from_records_with_version(reversal_record):
    """generate() honours the requested camt.053 version."""
    xml = services.generate([reversal_record], version="camt.053.001.08")
    assert "camt.053.001.08" in xml


def test_generate_from_records_pacs004(reversal_record):
    """generate() can emit a pacs.004 return from flat records."""
    xml = services.generate([reversal_record], output_format="pacs004")
    assert PACS_RETURN_MESSAGE_TYPE in xml
    assert "<Cd>AC04</Cd>" in xml


def test_generate_reversal_xml_empty_records_raises():
    """An empty record list is rejected before any rendering."""
    with pytest.raises(ReversalGenerationError, match="records list is empty"):
        generate_reversal_xml([])


def test_generate_reversal_for_statement_pacs004(statement_xml):
    """The statement convenience wrapper supports the pacs.004 format."""
    from camt053 import parse_statement
    from camt053.xml.generate_xml import generate_reversal_for_statement

    statement = parse_statement(statement_xml)
    xml = generate_reversal_for_statement(
        statement,
        reason_code="AC04",
        output_format="pacs004",
    )
    assert PACS_RETURN_MESSAGE_TYPE in xml
