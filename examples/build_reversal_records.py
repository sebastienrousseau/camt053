#!/usr/bin/env python3
"""Example: the reversal-building primitives, step by step.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/build_reversal_records.py

``services.generate_reversal`` does parse -> select -> reverse -> render in
one call. This script takes the scenic route through the underlying
primitives in ``camt053.reversal``: build the flat reversing-entry records
without rendering any XML, and derive stable (idempotent) reversal
references.
"""

from camt053 import parse_document
from camt053.reversal.reversal import (
    build_reversal_record,
    build_reversal_records,
    build_reversal_records_for_statements,
    stable_reversal_reference,
)
from camt053.services import build_reversal

STATEMENT = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">
  <BkToCstmrStmt>
    <GrpHdr><MsgId>STMT-MSG-0001</MsgId><CreDtTm>2026-06-15T08:00:00</CreDtTm></GrpHdr>
    <Stmt>
      <Id>STMT-0001</Id>
      <CreDtTm>2026-06-15T08:00:00</CreDtTm>
      <Acct><Id><IBAN>GB29NWBK60161331926819</IBAN></Id><Ccy>EUR</Ccy></Acct>
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
    """Build reversing-entry records from a parsed statement."""
    document = parse_document(STATEMENT)
    statement = document.statements[0]

    # 1. Per-statement: select the AC04 entries and map them to records.
    records = build_reversal_records(statement, reason_code="AC04")
    record = records[0]
    print("build_reversal_records:")
    print(f"  entry_ref      {record['entry_ref']}")
    print(f"  original_ref   {record['original_ref']}")
    print(f"  credit_debit   {record['credit_debit']} (flipped from CRDT)")
    print(f"  reason         {record['reason_code']} {record['reason_name']}")

    # 2. Per-document: aggregate matches across every statement.
    all_records = build_reversal_records_for_statements(
        document.statements, reason_code="AC04"
    )
    print(
        f"\nbuild_reversal_records_for_statements: {len(all_records)} record(s)"
    )

    # 3. Single entry, explicit header context.
    entry = statement.entries[0]
    single = build_reversal_record(
        entry,
        statement,
        msg_id="RVSL-CUSTOM-0001",
        creation_date_time="2026-06-15T09:00:00",
        statement_id="RVSL-STMT-0001",
    )
    print(f"build_reversal_record: msg_id={single['statement_msg_id']}")

    # 4. The services facade wraps the same primitives.
    facade_records = build_reversal(STATEMENT, reason_code="AC04")
    print(f"services.build_reversal: {len(facade_records)} record(s)")

    # 5. Stable reversal references: same input, same output, <= 35 chars.
    short = stable_reversal_reference("NTRY-0001")
    long = stable_reversal_reference("X" * 100)
    print("\nstable_reversal_reference:")
    print(f"  short original -> {short}")
    print(f"  long original  -> {long} ({len(long)} chars)")
    assert short == stable_reversal_reference("NTRY-0001")


if __name__ == "__main__":
    main()
