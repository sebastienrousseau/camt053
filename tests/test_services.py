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


@pytest.mark.smoke
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


@pytest.mark.smoke
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


# A two-statement document whose ONLY AC04 match is in the SECOND statement.
_TWO_STMT_AC04_IN_SECOND = (
    '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">'
    "<BkToCstmrStmt>"
    "<GrpHdr><MsgId>MULTI</MsgId>"
    "<CreDtTm>2026-06-15T08:00:00</CreDtTm></GrpHdr>"
    "<Stmt><Id>STMT-A</Id><ElctrncSeqNb>1</ElctrncSeqNb>"
    "<CreDtTm>2026-06-15T08:00:00</CreDtTm>"
    "<Acct><Id><IBAN>GB29NWBK60161331926819</IBAN></Id><Ccy>EUR</Ccy></Acct>"
    "<Bal><Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>"
    '<Amt Ccy="EUR">100.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>'
    "<Dt><Dt>2026-06-15</Dt></Dt></Bal>"
    "<Ntry><NtryRef>A-1</NtryRef>"
    '<Amt Ccy="EUR">10.00</Amt><CdtDbtInd>DBIT</CdtDbtInd>'
    "<Sts>BOOK</Sts></Ntry>"
    "</Stmt>"
    "<Stmt><Id>STMT-B</Id><ElctrncSeqNb>2</ElctrncSeqNb>"
    "<CreDtTm>2026-06-15T08:00:00</CreDtTm>"
    "<Acct><Id><IBAN>GB29NWBK60161331926819</IBAN></Id><Ccy>EUR</Ccy></Acct>"
    "<Bal><Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>"
    '<Amt Ccy="EUR">200.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>'
    "<Dt><Dt>2026-06-15</Dt></Dt></Bal>"
    "<Ntry><NtryRef>B-1</NtryRef>"
    '<Amt Ccy="EUR">1500.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>'
    "<Sts><Cd>BOOK</Cd></Sts>"
    "<BookgDt><Dt>2026-06-15</Dt></BookgDt>"
    "<NtryDtls><TxDtls>"
    "<Refs><EndToEndId>E2E-B1</EndToEndId></Refs>"
    "<RtrInf><Rsn><Cd>AC04</Cd></Rsn></RtrInf>"
    "</TxDtls></NtryDtls>"
    "</Ntry>"
    "</Stmt>"
    "</BkToCstmrStmt></Document>"
)


def test_build_reversal_matches_later_statement():
    """An AC04 match in a later statement is reversed (#20)."""
    records = services.build_reversal(_TWO_STMT_AC04_IN_SECOND, "AC04")
    assert len(records) == 1
    assert records[0]["original_ref"] == "B-1"
    assert records[0]["credit_debit"] == "DBIT"
    # Header context comes from the first statement that has a match.
    assert records[0]["statement_id"] == "RVSL-STMT-B"


def test_generate_reversal_matches_later_statement():
    """The one-shot workflow reverses a match in a later statement (#20)."""
    xml = services.generate_reversal(_TWO_STMT_AC04_IN_SECOND, "AC04")
    assert xml.count("<RvslInd>true</RvslInd>") == 1
    assert "AC04" in xml


def test_load_openapi():
    """The OpenAPI document is serialisable and includes the reverse path."""
    spec = json.loads(services.load_openapi())
    assert "/reverse" in spec["paths"]


def test_load_openapi_explicit_app():
    """An explicit FastAPI app is used when supplied."""
    from camt053.api.app import app

    spec = json.loads(services.load_openapi(app))
    assert spec["info"]["title"] == "Camt053 API"
