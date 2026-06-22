#!/usr/bin/env python3
"""Example: exactly-once dedupe primitives (v0.0.6 B3).

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/compute_dedupe_keys.py

Two helpers from ``camt053.parse.dedupe``:

* ``compute_dedupe_key(xml)`` - the canonical
  (GrpHdr/MsgId, Stmt/Id, Stmt/ElctrncSeqNb) tuple, hashed.
  Same statement -> same key.
* ``compute_dedupe_keys(xml)`` - one key per statement (a single
  payload can carry multiple statements).

Use the key as a primary key in your "already processed" table or a
Redis SET membership check.
"""

from camt053.services import compute_dedupe_key, compute_dedupe_keys

STATEMENT = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">
  <BkToCstmrStmt>
    <GrpHdr><MsgId>STMT-MSG-2026-06-15</MsgId><CreDtTm>2026-06-15T08:00:00</CreDtTm></GrpHdr>
    <Stmt>
      <Id>STMT-0001</Id>
      <ElctrncSeqNb>1</ElctrncSeqNb>
      <CreDtTm>2026-06-15T08:00:00</CreDtTm>
      <Acct><Id><IBAN>GB29NWBK60161331926819</IBAN></Id><Ccy>EUR</Ccy></Acct>
      <Bal><Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp><Amt Ccy="EUR">10000.00</Amt><CdtDbtInd>CRDT</CdtDbtInd><Dt><Dt>2026-06-15</Dt></Dt></Bal>
    </Stmt>
  </BkToCstmrStmt>
</Document>"""


def main() -> None:
    key = compute_dedupe_key(STATEMENT)
    print(f"single-statement dedupe key : {key}")

    # Re-deriving the same key from the same input yields the same hash.
    again = compute_dedupe_key(STATEMENT)
    assert key == again
    print(f"deterministic               : {key == again}")

    keys = compute_dedupe_keys(STATEMENT)
    print(f"per-statement keys (1 here) : {keys}")


if __name__ == "__main__":
    main()
