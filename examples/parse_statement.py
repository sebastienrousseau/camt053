#!/usr/bin/env python3
"""Example: parse an incoming statement into structured data.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/parse_statement.py

Reads a camt.053 statement and walks the typed model: group header, account,
balances, and entries (with their return reason codes, if any).
"""

from camt053 import parse_statement
from camt053.parse import describe_reason

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
        <NtryDtls><TxDtls>
          <RtrInf><Rsn><Cd>AC04</Cd></Rsn></RtrInf>
        </TxDtls></NtryDtls>
      </Ntry>
    </Stmt>
  </BkToCstmrStmt>
</Document>"""


def main() -> None:
    stmt = parse_statement(STATEMENT)
    print(f"Statement {stmt.id} for account {stmt.account.identifier()}")
    print(f"  Owner:    {stmt.account.owner_name}")
    print(f"  Currency: {stmt.account.currency}")
    for balance in stmt.balances:
        print(
            f"  Balance {balance.type_code}: "
            f"{balance.amount} {balance.currency} "
            f"{balance.credit_debit_indicator}"
        )
    print(f"  Entries:  {len(stmt.entries)}")
    for entry in stmt.entries:
        reason = (
            f" -> {entry.reason_code} ({describe_reason(entry.reason_code)})"
            if entry.reason_code
            else ""
        )
        print(
            f"    {entry.reference}: {entry.amount} {entry.currency} "
            f"{entry.credit_debit_indicator}{reason}"
        )


if __name__ == "__main__":
    main()
