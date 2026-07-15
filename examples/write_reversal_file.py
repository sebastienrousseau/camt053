#!/usr/bin/env python3
"""Example: write a reversal to disk and validate files against the XSD.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/write_reversal_file.py

``write_reversal_xml`` renders reversing-entry records and writes the
validated document to a path (the path itself is security-checked: it must
stay inside the working directory or the system temp directory). The
``validate_via_xsd`` / ``validate_xml_string_via_xsd`` helpers then check
any file or string against a bundled official ISO XSD.
"""

import os
import shutil
import tempfile

from camt053.constants import TEMPLATES_DIR, XSD_DIR
from camt053.services import build_reversal
from camt053.xml import (
    validate_via_xsd,
    validate_xml_string_via_xsd,
    write_reversal_xml,
)
from camt053.xml.template_env import get_template

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
    """Write a reversal file, then re-validate it against the ISO XSD."""
    records = build_reversal(STATEMENT, reason_code="AC04")
    xsd_path = str(XSD_DIR / "camt.053.001.14.xsd")

    # The output path is security-checked: it must stay inside the
    # working directory, so the demo writes to a subdirectory of it.
    tmp = tempfile.mkdtemp(dir=os.getcwd())
    try:
        out_path = os.path.join(tmp, "reversal.xml")
        written = write_reversal_xml(records, out_path)
        size = os.path.getsize(written)
        print(f"wrote {size} bytes to {os.path.basename(written)}")

        # Validate the file on disk against the official ISO 20022 XSD.
        file_ok = validate_via_xsd(written, xsd_path)
        print(f"validate_via_xsd (file):              {file_ok}")

        # The same check works on an in-memory string.
        with open(written, encoding="utf-8") as handle:
            content = handle.read()
        string_ok = validate_xml_string_via_xsd(content, xsd_path)
        print(f"validate_xml_string_via_xsd (string): {string_ok}")
    finally:
        shutil.rmtree(tmp)

    # A payload that is well-formed XML but not schema-valid fails cleanly.
    bad_ok = validate_xml_string_via_xsd("<Document/>", xsd_path)
    print(f"schema-invalid payload:               {bad_ok}")

    # The rendering behind it all: a sandboxed, autoescaped Jinja template
    # bundled per message type.
    template = get_template(
        str(TEMPLATES_DIR / "camt.053.001.14"), "template.xml"
    )
    print(f"bundled template loaded: {template.name}")


if __name__ == "__main__":
    main()
