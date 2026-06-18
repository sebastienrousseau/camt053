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

"""Round-trip re-serialisation tests for the statement serialiser (#18)."""

from pathlib import Path

import pytest

from camt053 import services
from camt053.exceptions import XMLGenerationError
from camt053.models import Balance, Entry, ParsedDocument, Statement
from camt053.parse.statement_parser import parse_document, parse_statement
from camt053.xml.serialize_statement import (
    serialize_document,
    serialize_statement,
)

GOLD_MASTER = (
    Path(__file__).parent / "gold_master" / "statement_ac04.xml"
).read_text()


# ── Round-trip invariant on the gold-master statement ────────────────


def test_gold_master_round_trips(statement_xml):
    """Re-serialising preserves the full parsed model."""
    doc1 = parse_document(statement_xml)
    doc2 = parse_document(serialize_document(doc1))
    assert doc1.to_dict() == doc2.to_dict()


def test_gold_master_file_round_trips():
    """The bundled gold-master statement round-trips intact."""
    doc1 = parse_document(GOLD_MASTER)
    doc2 = parse_document(serialize_document(doc1))
    assert doc1.to_dict() == doc2.to_dict()


def test_round_trip_preserves_entry_fields(statement_xml):
    """References, amounts, currencies, indicators, and reasons survive."""
    doc2 = parse_document(serialize_document(parse_document(statement_xml)))
    entries = doc2.all_entries()
    assert [e.reference for e in entries] == [
        "NTRY-0001",
        "NTRY-0002",
        "NTRY-0003",
    ]
    assert [e.amount for e in entries] == ["1500.00", "980.50", "42.00"]
    assert {e.currency for e in entries} == {"EUR"}
    assert [e.credit_debit_indicator for e in entries] == [
        "CRDT",
        "CRDT",
        "DBIT",
    ]
    assert entries[0].reason_code == "AC04"
    assert entries[1].reason_code == "AC06"
    assert entries[0].details[0].counterparty_name == "Globex SA"
    assert (
        entries[0].details[0].counterparty_account == "DE89370400440532013000"
    )


def test_round_trip_preserves_account_and_balances(statement_xml):
    """Account identification and balances are reproduced."""
    doc2 = parse_document(serialize_document(parse_document(statement_xml)))
    stmt = doc2.statements[0]
    assert stmt.account.iban == "GB29NWBK60161331926819"
    assert stmt.account.owner_name == "Acme Treasury Ltd"
    assert stmt.account.servicer_bic == "NWBKGB2LXXX"
    assert stmt.balances[0].type_code == "CLBD"
    assert stmt.balances[0].amount == "10000.00"
    assert stmt.balances[0].date == "2026-06-15"


def test_serialisation_is_deterministic(statement_xml):
    """The same parsed model renders to identical bytes every time."""
    doc = parse_document(statement_xml)
    assert serialize_document(doc) == serialize_document(doc)


def test_serialised_output_is_valid(statement_xml):
    """The re-serialised document validates against the bundled XSD."""
    xml = serialize_document(parse_document(statement_xml))
    report = services.validate_statement(xml)
    assert report["valid"] is True
    assert report["message_type"] == "camt.053.001.14"


# ── serialize_statement convenience + services facade ────────────────


def test_serialize_statement_single(statement_xml):
    """serialize_statement wraps one statement and round-trips it."""
    stmt = parse_statement(statement_xml)
    out = serialize_statement(stmt)
    round_tripped = parse_statement(out)
    assert round_tripped.id == stmt.id
    assert round_tripped.account.iban == stmt.account.iban


def test_services_serialize_statement(statement_xml):
    """services.serialize_statement parses then re-serialises raw XML."""
    out = services.serialize_statement(statement_xml)
    assert (
        parse_document(out).to_dict()
        == parse_document(statement_xml).to_dict()
    )


# ── Edge cases / schema-mandatory defaults ───────────────────────────


def test_other_id_account_serialises_as_othr():
    """An account identified by a proprietary id renders an ``Othr`` block."""
    src = (
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.052.001.14">'
        "<BkToCstmrAcctRpt><GrpHdr><MsgId>M</MsgId>"
        "<CreDtTm>2026-06-15T08:00:00</CreDtTm></GrpHdr>"
        "<Rpt><Id>R</Id><CreDtTm>2026-06-15T08:00:00</CreDtTm>"
        "<Acct><Id><Othr><Id>ACC-XYZ</Id></Othr></Id></Acct>"
        "<Bal><Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>"
        '<Amt Ccy="EUR">1.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>'
        "<Dt><Dt>2026-06-15</Dt></Dt></Bal></Rpt>"
        "</BkToCstmrAcctRpt></Document>"
    )
    out = serialize_document(parse_document(src))
    stmt = parse_statement(out)
    assert stmt.account.iban is None
    assert stmt.account.other_id == "ACC-XYZ"


def test_datetime_dates_preserved():
    """``DtTm`` balance / booking / value dates round-trip as date-times."""
    src = (
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">'
        "<BkToCstmrStmt><GrpHdr><MsgId>M</MsgId>"
        "<CreDtTm>2026-06-15T08:00:00</CreDtTm></GrpHdr>"
        "<Stmt><Id>S</Id><Acct><Id><IBAN>GB29NWBK60161331926819</IBAN>"
        "</Id></Acct>"
        "<Bal><Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>"
        '<Amt Ccy="EUR">1.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>'
        "<Dt><DtTm>2026-06-15T08:00:00</DtTm></Dt></Bal>"
        '<Ntry><Amt Ccy="EUR">9.99</Amt><CdtDbtInd>DBIT</CdtDbtInd>'
        "<BookgDt><DtTm>2026-06-15T08:00:00</DtTm></BookgDt>"
        "<ValDt><DtTm>2026-06-16T08:00:00</DtTm></ValDt></Ntry>"
        "</Stmt></BkToCstmrStmt></Document>"
    )
    stmt = parse_statement(serialize_document(parse_document(src)))
    assert stmt.balances[0].date == "2026-06-15T08:00:00"
    assert stmt.entries[0].booking_date == "2026-06-15T08:00:00"
    assert stmt.entries[0].value_date == "2026-06-16T08:00:00"


def test_statement_without_balance_gets_synthetic():
    """A statement carrying no balance still validates (synthetic balance)."""
    stmt = Statement(
        id="S",
        entries=[
            Entry(
                reference="N1",
                amount="5.00",
                currency="EUR",
                credit_debit_indicator="CRDT",
            )
        ],
    )
    out = serialize_statement(stmt)
    parsed = parse_statement(out)
    assert len(parsed.balances) == 1
    assert parsed.balances[0].type_code == "CLBD"


def test_minimal_entry_fills_mandatory_defaults():
    """An entry missing amount / status / indicator gets schema defaults."""
    stmt = Statement(
        id="S",
        balances=[
            Balance(
                type_code="CLBD",
                amount="0",
                currency="EUR",
                credit_debit_indicator="CRDT",
                date="2026-06-15",
            )
        ],
        entries=[Entry()],
    )
    out = serialize_statement(stmt)
    entry = parse_statement(out).entries[0]
    assert entry.amount == "0"
    assert entry.currency == "EUR"
    assert entry.credit_debit_indicator == "CRDT"
    assert entry.status == "BOOK"


def test_empty_account_serialises():
    """A statement with an empty account omits ``Acct/Id`` and still validates."""
    stmt = Statement(
        id="S",
        balances=[
            Balance(
                type_code="CLBD",
                amount="0",
                currency="EUR",
                credit_debit_indicator="CRDT",
                date="2026-06-15",
            )
        ],
    )
    parsed = parse_statement(serialize_statement(stmt))
    assert parsed.account.iban is None
    assert parsed.account.other_id is None


def test_entry_with_additional_info_only():
    """A detail carrying only AddtlInf (no reason) still renders a RtrInf."""
    stmt = Statement(
        id="S",
        balances=[
            Balance(
                type_code="CLBD",
                amount="0",
                currency="EUR",
                credit_debit_indicator="CRDT",
                date="2026-06-15",
            )
        ],
        entries=[
            Entry(
                reference="N1",
                amount="5.00",
                currency="EUR",
                credit_debit_indicator="CRDT",
                details=[__detail_with_info()],
            )
        ],
    )
    detail = parse_statement(serialize_statement(stmt)).entries[0].details[0]
    assert detail.additional_info == "Some narrative"
    assert detail.reason_code is None


def __detail_with_info():
    """Build a transaction detail carrying only additional info."""
    from camt053.models import TransactionDetails

    return TransactionDetails(additional_info="Some narrative")


# ── Error handling ───────────────────────────────────────────────────


def test_serialize_document_without_statements_raises():
    """Serialising a statement-less document is an explicit error."""
    doc = ParsedDocument(message_type="camt.053.001.14", statements=[])
    with pytest.raises(XMLGenerationError, match="no statement"):
        serialize_document(doc)


def test_serialise_invalid_value_fails_validation():
    """A value the XSD rejects raises an XMLGenerationError on validation."""
    stmt = Statement(
        id="S",
        balances=[
            Balance(
                type_code="CLBD",
                amount="0",
                currency="EUR",
                credit_debit_indicator="CRDT",
                date="2026-06-15",
            )
        ],
        entries=[
            Entry(
                reference="N1",
                # A non-numeric amount renders but is rejected by the
                # ActiveOrHistoricCurrencyAndAmount decimal type.
                amount="NOT-A-NUMBER",
                currency="EUR",
                credit_debit_indicator="CRDT",
            )
        ],
    )
    with pytest.raises(XMLGenerationError, match="failed validation"):
        serialize_statement(stmt)
