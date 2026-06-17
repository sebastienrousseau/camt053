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

"""Tests for the shared service facade."""

import json

import pytest

from camt053 import services
from camt053.exceptions import ReversalGenerationError, StatementParseError


def test_list_message_types():
    """Every supported message type is listed with its name."""
    rows = services.list_message_types()
    assert len(rows) == 3
    assert {
        "message_type": "camt.053.001.14",
        "name": "Bank To Customer Statement",
    } in rows


def test_list_return_reasons():
    """Return reasons are exposed via the facade."""
    rows = services.list_return_reasons()
    assert {"code": "AC04", "name": "Closed Account Number"} in rows


def test_get_input_schema_and_required_fields():
    """The input schema and its required fields are available."""
    schema = services.get_input_schema("camt.053.001.14")
    assert schema["properties"]["reason_code"]["maxLength"] == 4
    required = services.get_required_fields("camt.053.001.14")
    assert "reason_code" in required


def test_get_input_schema_unsupported_raises():
    """An unsupported message type raises ValueError."""
    with pytest.raises(ValueError):
        services.get_input_schema("camt.999.001.01")


def test_validate_records(reversal_record):
    """A valid record passes; a record missing a required field fails."""
    ok = services.validate_records("camt.053.001.14", [reversal_record])
    assert ok["valid"] is True
    assert ok["valid_count"] == 1

    bad = dict(reversal_record)
    bad.pop("reason_code")
    report = services.validate_records("camt.053.001.14", [bad])
    assert report["valid"] is False
    assert report["errors"]


def test_validate_identifier():
    """IBAN/BIC/LEI validation is exposed and unsupported kinds raise."""
    assert services.validate_identifier("bic", "NWBKGB2LXXX")["valid"] is True
    assert services.validate_identifier("iban", "NOPE")["valid"] is False
    with pytest.raises(ValueError):
        services.validate_identifier("ssn", "123")


def test_parse_statement(statement_xml):
    """Parsing returns the document as plain data."""
    doc = services.parse_statement(statement_xml)
    assert doc["msg_id"] == "STMT-MSG-0001"
    assert len(doc["statements"][0]["entries"]) == 3


def test_list_and_filter_entries(statement_xml):
    """Entries can be listed and filtered by reason code."""
    assert len(services.list_entries(statement_xml)) == 3
    assert len(services.filter_entries(statement_xml, "AC04")) == 1
    assert services.filter_entries(statement_xml, "MD07") == []


def test_build_reversal(statement_xml):
    """Reversing-entry records are built from the statement."""
    records = services.build_reversal(statement_xml, "AC04")
    assert records[0]["credit_debit"] == "DBIT"


def test_generate_reversal_default_ac04(statement_xml):
    """The default one-shot workflow reverses AC04 entries."""
    xml = services.generate_reversal(statement_xml)
    assert "<RvslInd>true</RvslInd>" in xml
    assert "AC04" in xml


def test_generate_reversal_no_match_raises(statement_xml):
    """A reason with no matching entry raises."""
    with pytest.raises(ReversalGenerationError):
        services.generate_reversal(statement_xml, "MD07")


def test_generate_from_records(reversal_record):
    """The record-driven generate entry point renders XML."""
    xml = services.generate([reversal_record])
    assert xml.lstrip().startswith("<?xml")


def test_generate_reversal_bad_xml_raises():
    """Malformed input raises a parse error from the facade."""
    with pytest.raises(StatementParseError):
        services.generate_reversal("<not-a-doc/>")


_NO_STMT = (
    '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">'
    "<BkToCstmrStmt><GrpHdr><MsgId>X</MsgId>"
    "<CreDtTm>2026-06-15T08:00:00</CreDtTm></GrpHdr></BkToCstmrStmt>"
    "</Document>"
)


def test_build_reversal_no_statement_raises():
    """Building a reversal from a statement-less document raises."""
    with pytest.raises(StatementParseError):
        services.build_reversal(_NO_STMT, "AC04")


def test_generate_reversal_no_statement_raises():
    """Generating a reversal from a statement-less document raises."""
    with pytest.raises(StatementParseError):
        services.generate_reversal(_NO_STMT, "AC04")


def test_load_openapi():
    """The OpenAPI document is serialisable and includes the reverse path."""
    spec = json.loads(services.load_openapi())
    assert "/reverse" in spec["paths"]
