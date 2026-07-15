#!/usr/bin/env python3
"""Example: memory-bounded streaming and entry filtering.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/stream_entries.py

For very large statements, ``iter_statement_entries`` (and its facade
counterpart ``services.iter_entries``) yields each entry the moment its
``<Ntry>`` element closes, so peak memory stays bounded to a single entry.
``services.list_entries`` returns the same entries as a list (optionally
via the streaming path), and ``services.filter_entries`` ANDs reason /
status / date / amount criteria.
"""

from camt053.parse.statement_parser import iter_statement_entries
from camt053.services import filter_entries, iter_entries, list_entries

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
        <BookgDt><Dt>2026-06-14</Dt></BookgDt>
        <NtryDtls><TxDtls>
          <RtrInf><Rsn><Cd>AC04</Cd></Rsn></RtrInf>
        </TxDtls></NtryDtls>
      </Ntry>
      <Ntry>
        <NtryRef>NTRY-0002</NtryRef>
        <Amt Ccy="EUR">250.00</Amt><CdtDbtInd>DBIT</CdtDbtInd>
        <Sts><Cd>BOOK</Cd></Sts>
        <BookgDt><Dt>2026-06-15</Dt></BookgDt>
      </Ntry>
      <Ntry>
        <NtryRef>NTRY-0003</NtryRef>
        <Amt Ccy="EUR">9000.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
        <Sts><Cd>PDNG</Cd></Sts>
        <BookgDt><Dt>2026-06-15</Dt></BookgDt>
      </Ntry>
    </Stmt>
  </BkToCstmrStmt>
</Document>"""


def main() -> None:
    """Stream, list, and filter the entries of a three-entry statement."""
    # 1. Typed streaming: Entry objects, one at a time.
    print("iter_statement_entries (typed, streaming):")
    for entry in iter_statement_entries(STATEMENT):
        print(f"  {entry.reference}: {entry.amount} {entry.currency}")

    # 2. Facade streaming: JSON-ready dicts, one at a time.
    first = next(iter_entries(STATEMENT))
    print(f"\niter_entries first item: {first['reference']}")

    # 3. Listing: tree-parse and streaming paths return identical data.
    eager = list_entries(STATEMENT)
    streamed = list_entries(STATEMENT, streaming=True)
    assert eager == streamed
    print(f"list_entries: {len(eager)} entries (eager == streaming)")

    # 4. Filtering: criteria are ANDed; reason_code=None disables the
    #    default AC04 reason filter.
    ac04 = filter_entries(STATEMENT)
    print(f"\nfilter_entries default (AC04): {len(ac04)} match(es)")
    booked = filter_entries(STATEMENT, reason_code=None, status="BOOK")
    print(f"status=BOOK, any reason:       {len(booked)} match(es)")
    large = filter_entries(
        STATEMENT,
        reason_code=None,
        min_amount="1000",
        date_from="2026-06-15",
    )
    print(f">= 1000 booked from 06-15:     {len(large)} match(es)")


if __name__ == "__main__":
    main()
