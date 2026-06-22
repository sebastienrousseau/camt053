#!/usr/bin/env python3
"""Example: partial-batch lenient parsing (v0.0.6 B4).

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/parse_statement_lenient.py

The strict parser refuses the entire payload if any entry is
corrupt. The lenient parser (``parse_statement_lenient``) returns a
ParseReport envelope that surfaces the good entries plus a
diagnostic list for the corrupt ones, so a single bad entry never
silently drops the whole statement.
"""

from camt053.services import parse_statement_lenient

# A statement with one well-formed entry and one bad entry
# (negative amount text).
MIXED = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">
  <BkToCstmrStmt>
    <GrpHdr><MsgId>STMT-MSG-001</MsgId><CreDtTm>2026-06-15T08:00:00</CreDtTm></GrpHdr>
    <Stmt>
      <Id>STMT-001</Id>
      <CreDtTm>2026-06-15T08:00:00</CreDtTm>
      <Acct><Id><IBAN>GB29NWBK60161331926819</IBAN></Id><Ccy>EUR</Ccy></Acct>
      <Bal><Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp><Amt Ccy="EUR">10000.00</Amt><CdtDbtInd>CRDT</CdtDbtInd><Dt><Dt>2026-06-15</Dt></Dt></Bal>
      <Ntry>
        <NtryRef>NTRY-0001</NtryRef>
        <Amt Ccy="EUR">1500.00</Amt>
        <CdtDbtInd>CRDT</CdtDbtInd>
        <Sts><Cd>BOOK</Cd></Sts>
        <BookgDt><Dt>2026-06-15</Dt></BookgDt>
      </Ntry>
      <Ntry>
        <NtryRef>NTRY-CORRUPT</NtryRef>
        <Amt Ccy="EUR">not-a-number</Amt>
        <CdtDbtInd>DBIT</CdtDbtInd>
        <Sts><Cd>BOOK</Cd></Sts>
        <BookgDt><Dt>2026-06-15</Dt></BookgDt>
      </Ntry>
    </Stmt>
  </BkToCstmrStmt>
</Document>"""


def main() -> None:
    report = parse_statement_lenient(MIXED)
    print(f"parsed statements        : {len(report.get('statements', []))}")
    print(f"corrupt_entry_count      : {report.get('corrupt_entry_count', 0)}")
    diags = report.get("diagnostics", []) or []
    print(f"diagnostics              : {len(diags)}")
    for d in diags[:3]:
        print(f"  - {d}")


if __name__ == "__main__":
    main()
