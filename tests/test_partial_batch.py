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

"""Tests for B4: lenient / partial-batch parsing mode."""

from __future__ import annotations

import pytest

from camt053 import services
from camt053.exceptions import StatementParseError
from camt053.parse import statement_parser
from camt053.parse.report import EntryDiagnostic, ParseReport
from camt053.parse.statement_parser import parse_document_lenient

_TWO_ENTRY_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08">'
    "<BkToCstmrStmt>"
    "<GrpHdr><MsgId>M</MsgId>"
    "<CreDtTm>2026-06-21T10:00:00</CreDtTm></GrpHdr>"
    "<Stmt><Id>S</Id>"
    "<Acct><Id><IBAN>DE89370400440532013000</IBAN></Id></Acct>"
    "<Ntry><NtryRef>NTRY-001</NtryRef>"
    "<Amt Ccy='EUR'>100.00</Amt>"
    "<CdtDbtInd>CRDT</CdtDbtInd></Ntry>"
    "<Ntry><NtryRef>NTRY-002</NtryRef>"
    "<Amt Ccy='EUR'>200.00</Amt>"
    "<CdtDbtInd>DBIT</CdtDbtInd></Ntry>"
    "</Stmt></BkToCstmrStmt></Document>"
)


def test_clean_document_yields_zero_diagnostics():
    """A well-formed document returns ``corrupt_entry_count=0``."""
    report = parse_document_lenient(_TWO_ENTRY_XML)
    assert isinstance(report, ParseReport)
    assert report.corrupt_entry_count == 0
    assert report.diagnostics == []
    assert len(report.document.statements[0].entries) == 2


def test_per_entry_failure_is_captured(monkeypatch):
    """A per-entry exception is skipped + recorded; siblings survive."""
    real_parse_entry = statement_parser._parse_entry

    def selectively_failing(ntry):
        ref_node = ntry.find(
            "{urn:iso:std:iso:20022:tech:xsd:camt.053.001.08}NtryRef"
        )
        if ref_node is not None and ref_node.text == "NTRY-002":
            raise ValueError("synthetic corruption in NTRY-002")
        return real_parse_entry(ntry)

    monkeypatch.setattr(statement_parser, "_parse_entry", selectively_failing)
    report = parse_document_lenient(_TWO_ENTRY_XML)
    assert report.corrupt_entry_count == 1
    assert len(report.document.statements[0].entries) == 1
    assert report.document.statements[0].entries[0].reference == "NTRY-001"
    diag = report.diagnostics[0]
    assert isinstance(diag, EntryDiagnostic)
    assert diag.stmt_index == 0
    assert diag.entry_index == 1
    assert diag.code == "ENTRY_PARSE_FAILED"
    assert "synthetic corruption" in diag.message


def test_empty_xml_still_raises():
    """Document-level failures still raise (not recoverable mid-stream)."""
    with pytest.raises(StatementParseError, match="empty"):
        parse_document_lenient("")
    with pytest.raises(StatementParseError, match="empty"):
        parse_document_lenient("   ")


def test_malformed_xml_still_raises():
    """A truly malformed payload raises StatementParseError."""
    with pytest.raises(StatementParseError):
        parse_document_lenient("<Document>unclosed")


def test_non_document_root_still_raises():
    """A non-Document root element still raises (document-level error)."""
    with pytest.raises(StatementParseError, match="Document"):
        parse_document_lenient("<NotADocument/>")


def test_unrecognised_container_still_raises():
    """An unknown message container raises with the supported list."""
    xml = (
        '<?xml version="1.0"?>'
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08">'
        "<NotAMessageContainer/></Document>"
    )
    with pytest.raises(StatementParseError, match="Unrecognised"):
        parse_document_lenient(xml)


def test_no_container_element_raises():
    """A Document with no child container raises a clear error."""
    xml = (
        '<?xml version="1.0"?>'
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08">'
        "</Document>"
    )
    with pytest.raises(StatementParseError, match="message container"):
        parse_document_lenient(xml)


def test_report_to_dict_roundtrip_shape():
    """``ParseReport.to_dict()`` carries the canonical shape."""
    report = parse_document_lenient(_TWO_ENTRY_XML)
    payload = report.to_dict()
    assert set(payload.keys()) == {
        "document",
        "corrupt_entry_count",
        "diagnostics",
    }
    assert payload["corrupt_entry_count"] == 0
    assert payload["diagnostics"] == []
    assert "statements" in payload["document"]


def test_entry_diagnostic_to_dict_shape():
    """``EntryDiagnostic.to_dict()`` carries the canonical four keys."""
    diag = EntryDiagnostic(
        stmt_index=0, entry_index=2, code="X", message="boom"
    )
    assert diag.to_dict() == {
        "stmt_index": 0,
        "entry_index": 2,
        "code": "X",
        "message": "boom",
    }


def test_services_parse_statement_lenient_returns_dict():
    """The services wrapper accepts XML + returns a JSON-able dict."""
    payload = services.parse_statement_lenient(_TWO_ENTRY_XML)
    assert payload["corrupt_entry_count"] == 0
    assert payload["diagnostics"] == []
    # The document shape matches the strict parser's parse_statement.
    strict_payload = services.parse_statement(_TWO_ENTRY_XML)
    assert payload["document"] == strict_payload


def test_lenient_handles_multiple_failures_in_order(monkeypatch):
    """Two failures get two diagnostics in source order, indices intact."""
    real_parse_entry = statement_parser._parse_entry

    def fail_both(ntry):
        ref_node = ntry.find(
            "{urn:iso:std:iso:20022:tech:xsd:camt.053.001.08}NtryRef"
        )
        if ref_node is not None and ref_node.text in {"NTRY-001", "NTRY-002"}:
            raise RuntimeError(f"fail {ref_node.text}")
        return real_parse_entry(ntry)

    monkeypatch.setattr(statement_parser, "_parse_entry", fail_both)
    report = parse_document_lenient(_TWO_ENTRY_XML)
    assert report.corrupt_entry_count == 2
    assert [d.entry_index for d in report.diagnostics] == [0, 1]
    assert report.document.statements[0].entries == []
