#!/usr/bin/env python3
"""Example: one-shot reversal generation in every output format.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/generate_reversal_documents.py

``services.generate_reversal`` is the headline one-shot workflow (parse ->
select -> reverse -> validate). This script exercises its output knobs:
the default camt.053.001.14 statement, the camt.053.001.08 back-level
schema, and the pacs.004.001.11 PaymentReturn format. It also renders
pre-built records directly with ``services.generate`` and the low-level
``generate_reversal_xml``.
"""

from camt053 import generate_reversal_for_statement, parse_document
from camt053.services import build_reversal, generate, generate_reversal
from camt053.xml import generate_reversal_xml

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


def _namespace(xml: str) -> str:
    """Return the emitted document's xmlns for a one-line summary."""
    start = xml.index('xmlns="') + len('xmlns="')
    return xml[start : xml.index('"', start)]


def main() -> None:
    """Generate reversal documents in each supported format / version."""
    # 1. Default: a validated camt.053.001.14 reversing-entry statement.
    default_xml = generate_reversal(STATEMENT, reason_code="AC04")
    print(f"default        -> {_namespace(default_xml)}")

    # 2. Back-level camt.053 schema version.
    v08_xml = generate_reversal(
        STATEMENT, reason_code="AC04", version="camt.053.001.08"
    )
    print(f"version=.08    -> {_namespace(v08_xml)}")

    # 3. pacs.004 PaymentReturn instead of a camt.053 statement.
    pacs_xml = generate_reversal(
        STATEMENT, reason_code="AC04", output_format="pacs004"
    )
    print(f"pacs004        -> {_namespace(pacs_xml)}")

    # 4. Render pre-built records directly (records built elsewhere).
    records = build_reversal(STATEMENT, reason_code="AC04")
    rendered = generate(records, cleanse=True)
    print(f"from records   -> {_namespace(rendered)}")

    # 5. The low-level renderer behind all of the above.
    low_level = generate_reversal_xml(records)
    print(f"low-level      -> {_namespace(low_level)}")

    # 6. Reverse a single parsed Statement object.
    statement = parse_document(STATEMENT).statements[0]
    per_statement = generate_reversal_for_statement(
        statement, reason_code="AC04"
    )
    print(f"per statement  -> {_namespace(per_statement)}")


if __name__ == "__main__":
    main()
