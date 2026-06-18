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

"""Resilience tests for the camt.05x statement parser (#16).

Malformed-but-recoverable statements must degrade gracefully (missing
optionals, unknown / extra elements, unexpected namespaces and prefixes are
non-fatal), while genuinely non-well-formed XML must still raise a
:class:`StatementParseError` carrying precise source-line context.
"""

from defusedxml.ElementTree import ParseError

from camt053.exceptions import StatementParseError
from camt053.parse.statement_parser import (
    _malformed_error,
    parse_document,
    parse_statement,
)


def _wrap(body: str, ns: str = "camt.053.001.14") -> str:
    """Wrap a statement body in a minimal versioned Document envelope."""
    return (
        f'<Document xmlns="urn:iso:std:iso:20022:tech:xsd:{ns}">'
        f"<BkToCstmrStmt><GrpHdr><MsgId>M</MsgId></GrpHdr>"
        f"<Stmt><Id>S</Id>{body}</Stmt></BkToCstmrStmt></Document>"
    )


# ── Graceful degradation: missing optional elements ──────────────────


def test_missing_all_optionals_yields_empty_not_error():
    """A statement stripped of every optional element still parses."""
    stmt = parse_statement(_wrap(""))
    assert stmt.id == "S"
    assert stmt.account.iban is None
    assert stmt.account.owner_name is None
    assert stmt.balances == []
    assert stmt.entries == []


def test_entry_without_optional_fields():
    """An entry missing amount, status, dates, and reason degrades."""
    stmt = parse_statement(_wrap("<Ntry></Ntry>"))
    entry = stmt.entries[0]
    assert entry.amount is None
    assert entry.currency is None
    assert entry.status is None
    assert entry.booking_date is None
    assert entry.reason_code is None
    assert entry.is_returnable() is False


def test_amount_element_without_text_is_none():
    """An empty ``<Amt/>`` (no text) reads as a ``None`` amount."""
    stmt = parse_statement(_wrap('<Ntry><Amt Ccy="EUR"></Amt></Ntry>'))
    entry = stmt.entries[0]
    assert entry.amount is None
    assert entry.currency == "EUR"


def test_whitespace_only_text_is_none():
    """A whitespace-only element value is normalised to ``None``."""
    stmt = parse_statement(_wrap("<Ntry><NtryRef>   </NtryRef></Ntry>"))
    assert stmt.entries[0].reference is None


def test_empty_status_element_is_none():
    """A bare ``<Sts></Sts>`` with no code and no text reads as ``None``."""
    stmt = parse_statement(_wrap("<Ntry><Sts></Sts></Ntry>"))
    assert stmt.entries[0].status is None


def test_balance_without_amount_or_date():
    """A balance with no amount / date element keeps those fields ``None``."""
    stmt = parse_statement(
        _wrap("<Bal><Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp></Bal>")
    )
    bal = stmt.balances[0]
    assert bal.type_code == "CLBD"
    assert bal.amount is None
    assert bal.currency is None
    assert bal.date is None


# ── Graceful degradation: unknown / extra elements ───────────────────


def test_unknown_elements_are_ignored():
    """Vendor extensions and unexpected siblings are skipped, not fatal."""
    body = (
        "<VendorExtension><Foo>bar</Foo></VendorExtension>"
        '<Ntry><NtryRef>N1</NtryRef><Amt Ccy="EUR">1.00</Amt>'
        "<UnknownChild>ignored</UnknownChild>"
        "<CdtDbtInd>CRDT</CdtDbtInd></Ntry>"
    )
    stmt = parse_statement(_wrap(body))
    assert stmt.entries[0].reference == "N1"
    assert stmt.entries[0].amount == "1.00"


def test_extra_statement_siblings_ignored():
    """Unrecognised container children are not treated as statements."""
    xml = (
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">'
        "<BkToCstmrStmt><GrpHdr><MsgId>M</MsgId></GrpHdr>"
        "<SomeOtherThing/>"
        "<Stmt><Id>S</Id></Stmt></BkToCstmrStmt></Document>"
    )
    doc = parse_document(xml)
    assert len(doc.statements) == 1


# ── Graceful degradation: unexpected namespaces / prefixes ───────────


def test_prefixed_document_root_is_recognised():
    """A namespace-prefixed ``<camt:Document>`` root parses normally."""
    xml = (
        "<camt:Document "
        'xmlns:camt="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">'
        "<camt:BkToCstmrStmt><camt:GrpHdr><camt:MsgId>M</camt:MsgId>"
        "</camt:GrpHdr><camt:Stmt><camt:Id>S</camt:Id></camt:Stmt>"
        "</camt:BkToCstmrStmt></camt:Document>"
    )
    doc = parse_document(xml)
    assert doc.message_type == "camt.053.001.14"
    assert doc.statements[0].id == "S"


def test_non_iso_namespace_is_tolerated():
    """An unexpected (non-ISO) namespace URI is matched by local name."""
    xml = (
        '<Document xmlns="urn:example:custom:namespace">'
        "<BkToCstmrStmt><GrpHdr><MsgId>M</MsgId></GrpHdr>"
        "<Stmt><Id>S</Id></Stmt></BkToCstmrStmt></Document>"
    )
    doc = parse_document(xml)
    # Unknown namespace -> version falls back to the container's message type.
    assert doc.message_type == "camt.053.001.14"


def test_mixed_namespaces_across_children():
    """Children in differing namespaces are still matched by local name."""
    xml = (
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14" '
        'xmlns:x="urn:example:other">'
        "<BkToCstmrStmt><GrpHdr><MsgId>M</MsgId></GrpHdr>"
        "<Stmt><Id>S</Id><x:Ntry><x:NtryRef>N1</x:NtryRef>"
        '<x:Amt Ccy="EUR">2.00</x:Amt></x:Ntry></Stmt>'
        "</BkToCstmrStmt></Document>"
    )
    stmt = parse_statement(xml)
    assert stmt.entries[0].reference == "N1"
    assert stmt.entries[0].amount == "2.00"


# ── Non-recoverable: precise error context ───────────────────────────


def test_unclosed_tag_reports_line():
    """A non-well-formed document raises with a 1-based source line."""
    xml = (
        "<Document>\n"
        "  <BkToCstmrStmt>\n"
        "    <Stmt><Id>S</Id>\n"
        "  </BkToCstmrStmt>\n"
        "</Document>"
    )
    try:
        parse_document(xml)
    except StatementParseError as exc:
        assert exc.line is not None
        assert exc.line >= 1
        assert "Malformed statement XML" in str(exc)
    else:  # pragma: no cover - the document is genuinely malformed
        raise AssertionError("expected StatementParseError")


def test_malformed_error_includes_column_when_available():
    """When expat reports a column, it is folded into the message."""
    err = _malformed_error(ParseError("not well-formed: line 3, column 7"))
    assert err.line == 3
    assert "line 3, column 7" in str(err)


def test_malformed_error_line_without_column():
    """A line-only parse error still yields a precise line-based message."""
    err = _malformed_error(ParseError("mismatched tag: line 5"))
    assert err.line == 5
    assert "line 5" in str(err)
    assert "column" not in str(err)


def test_malformed_error_without_position_falls_back():
    """A parse error with no position yields ``line=None`` and a clear text."""
    err = _malformed_error(ParseError("syntax error"))
    assert err.line is None
    assert "an unknown position" in str(err)
