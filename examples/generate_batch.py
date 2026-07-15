#!/usr/bin/env python3
"""Example: batch-reverse a directory of statement files.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/generate_batch.py

``services.generate_batch`` processes a directory (recursively), a glob,
or an explicit file list, reversing each statement independently. Each
file is isolated: a parse or generation failure on one file is captured
as a per-file error result and never aborts the rest of the batch.
"""

import os
import tempfile

from camt053.services import generate_batch

STATEMENT = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">
  <BkToCstmrStmt>
    <GrpHdr><MsgId>STMT-MSG-{n}</MsgId><CreDtTm>2026-06-15T08:00:00</CreDtTm></GrpHdr>
    <Stmt>
      <Id>STMT-{n}</Id>
      <CreDtTm>2026-06-15T08:00:00</CreDtTm>
      <Acct><Id><IBAN>GB29NWBK60161331926819</IBAN></Id><Ccy>EUR</Ccy></Acct>
      <Bal><Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>
        <Amt Ccy="EUR">10000.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
        <Dt><Dt>2026-06-15</Dt></Dt></Bal>
      <Ntry>
        <NtryRef>NTRY-{n}</NtryRef>
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
    """Reverse a directory of statements, tolerating one broken file."""
    with tempfile.TemporaryDirectory() as tmp:
        # Two good statements plus one file that is not valid XML.
        for n in ("0001", "0002"):
            path = os.path.join(tmp, f"statement-{n}.xml")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(STATEMENT.replace("{n}", n))
        broken = os.path.join(tmp, "statement-broken.xml")
        with open(broken, "w", encoding="utf-8") as handle:
            handle.write("this is not XML")

        summary = generate_batch(tmp, reason_code="AC04")

        print(
            f"total={summary['total']} "
            f"succeeded={summary['succeeded']} "
            f"failed={summary['failed']}"
        )
        for result in summary["results"]:
            name = os.path.basename(result["path"])
            if result["ok"]:
                print(f"  ok    {name} ({len(result['xml'])} bytes of XML)")
            else:
                print(f"  fail  {name}: {result['error'][:60]}")


if __name__ == "__main__":
    main()
