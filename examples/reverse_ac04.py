#!/usr/bin/env python3
"""Example: the headline workflow -- reverse AC04 (Closed Account) entries.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/reverse_ac04.py

Reads an incoming camt.053 Bank-to-Customer Statement, finds the booked entries
that were returned with reason code AC04 (Closed Account), and generates a
validated camt.053.001.14 reversing entry -- exactly the "read this statement,
pull the AC04 transactions, and generate the reversing entry" workflow.
"""

from camt053 import services

# An incoming statement: a EUR 1,500 credit transfer was booked, then returned
# because the beneficiary account had been closed (AC04).
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
      <Bal>
        <Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>
        <Amt Ccy="EUR">10000.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
        <Dt><Dt>2026-06-15</Dt></Dt>
      </Bal>
      <Ntry>
        <NtryRef>NTRY-0001</NtryRef>
        <Amt Ccy="EUR">1500.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
        <Sts><Cd>BOOK</Cd></Sts>
        <BookgDt><Dt>2026-06-15</Dt></BookgDt>
        <NtryDtls><TxDtls>
          <Refs><EndToEndId>E2E-0001</EndToEndId></Refs>
          <RtrInf><Rsn><Cd>AC04</Cd></Rsn><AddtlInf>Account closed</AddtlInf></RtrInf>
          <RltdPties><Dbtr><Pty><Nm>Globex SA</Nm></Pty></Dbtr></RltdPties>
        </TxDtls></NtryDtls>
      </Ntry>
    </Stmt>
  </BkToCstmrStmt>
</Document>"""


def main() -> None:
    # 1. Inspect the AC04 entries on the statement.
    ac04 = services.filter_entries(STATEMENT, "AC04")
    print(f"AC04 (Closed Account) entries found: {len(ac04)}")
    for entry in ac04:
        print(
            f"  {entry['reference']}: {entry['amount']} {entry['currency']} "
            f"{entry['credit_debit_indicator']}"
        )

    # 2. Generate the reversing entry (one call: parse -> filter -> reverse).
    reversal = services.generate_reversal(STATEMENT, reason_code="AC04")
    print("\nReversing entry (camt.053.001.14), validated against ISO XSD:\n")
    print(reversal)


if __name__ == "__main__":
    main()
