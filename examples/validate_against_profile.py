#!/usr/bin/env python3
"""Example: per-schema-version profile validation.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/validate_against_profile.py

Shows the v0.0.7 profile-dispatch architecture: the same payload
runs through three different profiles (.02 deprecated, .08 CBPR+
current, .13 T2S MR2026 strict) and the findings differ in
severity per version.
"""

from camt053.services import validate_against_profile

UNSTRUCTURED_v08 = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08">
  <BkToCstmrStmt><Stmt>
    <PstlAdr><AdrLine>1 Main St, Anytown, USA</AdrLine></PstlAdr>
  </Stmt></BkToCstmrStmt>
</Document>"""

UNSTRUCTURED_v13 = UNSTRUCTURED_v08.replace(".08", ".13")

DEPRECATED_v02 = UNSTRUCTURED_v08.replace(".08", ".02")


def _report(label: str, xml: str) -> None:
    """Print a one-line summary of the profile report."""
    r = validate_against_profile(xml)
    print(f"== {label}")
    print(
        f"   profile: {r['profile']}  ready: {r['ready']}  "
        f"findings: {len(r['findings'])}"
    )
    for f in r["findings"][:3]:
        print(f"     [{f['severity']}] {f['code']}: {f['message'][:80]}...")


def main() -> None:
    _report(
        "unstructured address on .08 (warning, still ready)", UNSTRUCTURED_v08
    )
    _report("unstructured address on .13 (error, NOT ready)", UNSTRUCTURED_v13)
    _report("any payload on .02 (deprecated warning)", DEPRECATED_v02)


if __name__ == "__main__":
    main()
