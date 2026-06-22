#!/usr/bin/env python3
"""Example: Nov 14-16 2026 CBPR+ cliff pre-flight (v0.0.6).

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/check_cbpr_readiness.py

Runs ``check_cbpr_readiness`` against two payloads: one that will
pass CBPR+ post-cutover (structured address) and one that will
fail (unstructured-only address). Pre-flight your bank-statement
pipeline against this before 14 Nov 2026.
"""

from camt053.compliance import check_cbpr_readiness

CBPR_READY = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.13">
  <BkToCstmrStmt><Stmt>
    <Acct>
      <Id><IBAN>GB29NWBK60161331926819</IBAN></Id>
      <Ownr>
        <Nm>Acme Treasury Ltd</Nm>
        <PstlAdr><StrtNm>1 Main St</StrtNm><TwnNm>London</TwnNm><Ctry>GB</Ctry></PstlAdr>
      </Ownr>
    </Acct>
  </Stmt></BkToCstmrStmt>
</Document>"""

CBPR_REJECT = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.13">
  <BkToCstmrStmt><Stmt>
    <Acct>
      <Id><IBAN>GB29NWBK60161331926819</IBAN></Id>
      <Ownr>
        <Nm>Acme Treasury Ltd</Nm>
        <PstlAdr><AdrLine>1 Main St, London, GB</AdrLine></PstlAdr>
      </Ownr>
    </Acct>
  </Stmt></BkToCstmrStmt>
</Document>"""


def _report(label: str, xml: str) -> None:
    r = check_cbpr_readiness(xml)
    print(f"== {label}")
    print(f"   cbpr_ready: {r['cbpr_ready']}")
    print(f"   schema    : {r['schema_version']}")
    print(f"   cutover   : {r['cutover_date']}")
    print(f"   issues    : {len(r['issues'])}")
    for issue in r["issues"][:3]:
        print(f"     - {issue}")


def main() -> None:
    _report("structured address (CBPR+ ready)", CBPR_READY)
    print()
    _report("unstructured-only address (rejected post-cutover)", CBPR_REJECT)


if __name__ == "__main__":
    main()
