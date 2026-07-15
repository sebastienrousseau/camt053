#!/usr/bin/env python3
"""Example: parse -> typed model -> re-serialised, validated XML.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/serialize_roundtrip.py

Round-trips a statement through the typed model: ``parse_document`` builds
a ``ParsedDocument`` (statements, accounts, balances, entries),
``serialize_document`` / ``serialize_statement`` render it back to a
validated camt.053.001.14 document, and a second parse proves the data
survived byte-for-byte where it matters.
"""

from decimal import Decimal

from camt053 import (
    parse_document,
    serialize_document,
    serialize_statement,
)
from camt053.services import serialize_statement as serialize_service

STATEMENT = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">
  <BkToCstmrStmt>
    <GrpHdr><MsgId>STMT-MSG-0001</MsgId><CreDtTm>2026-06-15T08:00:00</CreDtTm></GrpHdr>
    <Stmt>
      <Id>STMT-0001</Id>
      <CreDtTm>2026-06-15T08:00:00</CreDtTm>
      <Acct>
        <Id><IBAN>GB29NWBK60161331926819</IBAN></Id>
        <Ccy>EUR</Ccy>
        <Ownr><Nm>Acme Treasury Ltd</Nm></Ownr>
      </Acct>
      <Bal><Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>
        <Amt Ccy="EUR">10000.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
        <Dt><Dt>2026-06-15</Dt></Dt></Bal>
      <Ntry>
        <NtryRef>NTRY-0001</NtryRef>
        <Amt Ccy="EUR">1500.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
        <Sts><Cd>BOOK</Cd></Sts>
        <NtryDtls><TxDtls>
          <RtrInf><Rsn><Cd>AC04</Cd></Rsn></RtrInf>
        </TxDtls></NtryDtls>
      </Ntry>
    </Stmt>
  </BkToCstmrStmt>
</Document>"""


def main() -> None:
    """Walk the typed model, re-serialise it, and verify the round-trip."""
    document = parse_document(STATEMENT)
    statement = document.statements[0]

    # The typed model: accounts, balances, entries, with Decimal amounts.
    print(f"account   {statement.account.identifier()}")
    balance = statement.balances[0]
    print(f"balance   {balance.amount_decimal} {balance.currency}")
    for entry in document.all_entries():
        print(
            f"entry     {entry.reference} "
            f"{entry.amount_decimal} {entry.currency} "
            f"returnable={entry.is_returnable()}"
        )
    ac04 = statement.entries_with_reason("AC04")
    print(f"AC04 entries on the statement: {len(ac04)}")
    assert statement.entries[0].amount_decimal == Decimal("1500.00")

    # Re-serialise: whole document, single statement, or via the facade.
    doc_xml = serialize_document(document)
    stmt_xml = serialize_statement(statement)
    svc_xml = serialize_service(STATEMENT)
    print(f"\nserialize_document:  {len(doc_xml)} bytes (XSD-validated)")
    print(f"serialize_statement: {len(stmt_xml)} bytes")
    print(f"services facade:     {len(svc_xml)} bytes")

    # The round-trip preserves the parsed data.
    again = parse_document(doc_xml)
    assert again.to_dict() == document.to_dict()
    print("round-trip: parse(serialize(parse(xml))) is stable")


if __name__ == "__main__":
    main()
