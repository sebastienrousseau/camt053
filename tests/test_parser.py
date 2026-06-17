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

"""Tests for the camt.05x statement parser."""

import pytest

from camt053.exceptions import StatementParseError
from camt053.parse.statement_parser import parse_document, parse_statement

CAMT052 = """<?xml version="1.0"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.052.001.14">
  <BkToCstmrAcctRpt>
    <GrpHdr><MsgId>RPT-1</MsgId><CreDtTm>2026-06-15T08:00:00</CreDtTm></GrpHdr>
    <Rpt>
      <Id>RPT-0001</Id>
      <Acct><Id><Othr><Id>ACC-XYZ</Id></Othr></Id></Acct>
      <Ntry><Amt Ccy="EUR">5.00</Amt><CdtDbtInd>CRDT</CdtDbtInd></Ntry>
    </Rpt>
  </BkToCstmrAcctRpt>
</Document>"""


@pytest.mark.smoke
def test_parse_document_basic(statement_xml):
    """A camt.053 document parses to its header and statements."""
    doc = parse_document(statement_xml)
    assert doc.message_type == "camt.053.001.14"
    assert doc.msg_id == "STMT-MSG-0001"
    assert doc.creation_date_time == "2026-06-15T08:00:00"
    assert len(doc.statements) == 1


def test_parse_account_fields(statement_xml):
    """Account identification, currency, owner, and servicer are read."""
    stmt = parse_statement(statement_xml)
    assert stmt.account.iban == "GB29NWBK60161331926819"
    assert stmt.account.currency == "EUR"
    assert stmt.account.owner_name == "Acme Treasury Ltd"
    assert stmt.account.servicer_bic == "NWBKGB2LXXX"
    assert stmt.account.identifier() == "GB29NWBK60161331926819"


def test_parse_balances(statement_xml):
    """Balances are parsed with type, amount, indicator, and date."""
    stmt = parse_statement(statement_xml)
    assert len(stmt.balances) == 1
    bal = stmt.balances[0]
    assert bal.type_code == "CLBD"
    assert bal.amount == "10000.00"
    assert bal.currency == "EUR"
    assert bal.credit_debit_indicator == "CRDT"
    assert bal.date == "2026-06-15"


def test_parse_entries_and_reasons(statement_xml):
    """Entries carry amounts, indicators, and convenience reason codes."""
    stmt = parse_statement(statement_xml)
    assert len(stmt.entries) == 3
    first = stmt.entries[0]
    assert first.reference == "NTRY-0001"
    assert first.amount == "1500.00"
    assert first.currency == "EUR"
    assert first.credit_debit_indicator == "CRDT"
    assert first.status == "BOOK"
    assert first.booking_date == "2026-06-15"
    assert first.reason_code == "AC04"
    assert first.is_returnable() is True
    assert stmt.entries[2].is_returnable() is False


def test_parse_transaction_details(statement_xml):
    """Transaction details expose refs, reason, and counterparty."""
    detail = parse_statement(statement_xml).entries[0].details[0]
    assert detail.end_to_end_id == "E2E-0001"
    assert detail.tx_id == "TX-0001"
    assert detail.reason_code == "AC04"
    assert detail.additional_info == "Beneficiary account closed"
    assert detail.counterparty_name == "Globex SA"
    assert detail.counterparty_account == "DE89370400440532013000"


def test_status_without_code_element(statement_xml):
    """A bare ``<Sts>BOOK</Sts>`` (no ``<Cd>``) is read as the status."""
    assert parse_statement(statement_xml).entries[2].status == "BOOK"


def test_entries_with_reason(statement_xml):
    """``entries_with_reason`` is case-insensitive and matches details."""
    stmt = parse_statement(statement_xml)
    assert len(stmt.entries_with_reason("ac04")) == 1
    assert len(stmt.entries_with_reason("AC06")) == 1
    assert stmt.entries_with_reason("MD07") == []


def test_all_entries_across_statements(statement_xml):
    """``all_entries`` flattens entries across statements."""
    assert len(parse_document(statement_xml).all_entries()) == 3


def test_parse_camt052_report():
    """A camt.052 account report parses via its container element."""
    doc = parse_document(CAMT052)
    assert doc.message_type == "camt.052.001.14"
    assert doc.statements[0].account.other_id == "ACC-XYZ"
    assert doc.statements[0].account.iban is None


DTTM_AND_CREDITOR = """<?xml version="1.0"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">
  <BkToCstmrStmt>
    <GrpHdr><MsgId>M</MsgId><CreDtTm>2026-06-15T08:00:00</CreDtTm></GrpHdr>
    <Stmt>
      <Id>S</Id>
      <Acct><Id><IBAN>GB29NWBK60161331926819</IBAN></Id></Acct>
      <Bal>
        <Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>
        <Amt Ccy="EUR">1.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
        <Dt><DtTm>2026-06-15T08:00:00</DtTm></Dt>
      </Bal>
      <Ntry>
        <Amt Ccy="EUR">9.99</Amt><CdtDbtInd>DBIT</CdtDbtInd>
        <RvslInd>true</RvslInd>
        <BookgDt><DtTm>2026-06-15T08:00:00</DtTm></BookgDt>
        <ValDt><DtTm>2026-06-16T08:00:00</DtTm></ValDt>
        <NtryDtls><TxDtls>
          <RtrInf><Rsn><Cd>AC04</Cd></Rsn></RtrInf>
          <RltdPties>
            <Cdtr><Pty><Nm>Beneficiary Co</Nm></Pty></Cdtr>
            <CdtrAcct><Id><IBAN>FR1420041010050500013M02606</IBAN></Id></CdtrAcct>
          </RltdPties>
        </TxDtls></NtryDtls>
      </Ntry>
    </Stmt>
  </BkToCstmrStmt>
</Document>"""


def test_parse_datetime_dates_and_creditor_party():
    """DtTm dates, reversal flag, and a Cdtr-only counterparty are read."""
    stmt = parse_statement(DTTM_AND_CREDITOR)
    assert stmt.balances[0].date == "2026-06-15T08:00:00"
    entry = stmt.entries[0]
    assert entry.reversal_indicator is True
    assert entry.booking_date == "2026-06-15T08:00:00"
    assert entry.value_date == "2026-06-16T08:00:00"
    assert entry.details[0].counterparty_name == "Beneficiary Co"
    assert entry.details[0].counterparty_account == (
        "FR1420041010050500013M02606"
    )


def test_related_parties_account_without_name():
    """RltdPties carrying only an account (no party name) is handled."""
    xml = (
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">'
        "<BkToCstmrStmt><GrpHdr><MsgId>M</MsgId></GrpHdr><Stmt><Id>S</Id>"
        "<Acct><Id><IBAN>GB29NWBK60161331926819</IBAN></Id></Acct>"
        '<Ntry><Amt Ccy="EUR">1.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>'
        "<NtryDtls><TxDtls>"
        "<RtrInf><Rsn><Cd>AC04</Cd></Rsn></RtrInf>"
        "<RltdPties><DbtrAcct><Id><IBAN>DE89370400440532013000</IBAN>"
        "</Id></DbtrAcct></RltdPties>"
        "</TxDtls></NtryDtls></Ntry></Stmt></BkToCstmrStmt></Document>"
    )
    detail = parse_statement(xml).entries[0].details[0]
    assert detail.counterparty_name is None
    assert detail.counterparty_account == "DE89370400440532013000"


def test_to_dict_roundtrip(statement_xml):
    """The parsed model serialises to plain JSON-friendly data."""
    data = parse_document(statement_xml).to_dict()
    assert data["msg_id"] == "STMT-MSG-0001"
    assert data["statements"][0]["entries"][0]["reason_code"] == "AC04"


def test_unversioned_namespace_falls_back_to_container_type():
    """A recognised container with no version in the namespace falls back."""
    xml = (
        "<Document><BkToCstmrStmt>"
        "<GrpHdr><MsgId>M</MsgId></GrpHdr>"
        "<Stmt><Id>S</Id></Stmt></BkToCstmrStmt></Document>"
    )
    assert parse_document(xml).message_type == "camt.053.001.14"


def test_statement_without_account():
    """A statement with no ``Acct`` yields an empty account, not an error."""
    xml = (
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">'
        "<BkToCstmrStmt><GrpHdr><MsgId>M</MsgId></GrpHdr>"
        "<Stmt><Id>S</Id></Stmt></BkToCstmrStmt></Document>"
    )
    stmt = parse_statement(xml)
    assert stmt.account.iban is None
    assert stmt.account.identifier() is None


def test_empty_xml_raises():
    """Empty input raises a StatementParseError."""
    with pytest.raises(StatementParseError, match="empty"):
        parse_document("   ")


def test_malformed_xml_raises():
    """Malformed XML raises a StatementParseError with a line number."""
    with pytest.raises(StatementParseError) as exc_info:
        parse_document("<Document><BkToCstmrStmt></Document>")
    assert exc_info.value.line is not None


def test_wrong_root_raises():
    """A non-Document root is rejected."""
    with pytest.raises(StatementParseError, match="Document"):
        parse_document("<Foo/>")


def test_empty_document_raises():
    """A Document with no container element is rejected."""
    with pytest.raises(StatementParseError, match="no message container"):
        parse_document(
            '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14"/>'
        )


def test_unknown_container_raises():
    """An unrecognised container element is rejected."""
    with pytest.raises(StatementParseError, match="Unrecognised"):
        parse_document("<Document><SomethingElse/></Document>")


def test_parse_statement_without_statement_element_raises():
    """A container with a group header but no statement element is rejected."""
    xml = (
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">'
        "<BkToCstmrStmt><GrpHdr><MsgId>X</MsgId></GrpHdr></BkToCstmrStmt>"
        "</Document>"
    )
    with pytest.raises(StatementParseError, match="no statement element"):
        parse_statement(xml)
