#!/usr/bin/env python3
"""Example: the camt053 command-line interface, end to end.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/cli_workflows.py

Drives the installed ``camt053`` CLI (via ``python -m camt053``) through
its main commands: reference lookups (``message-types``, ``reasons``,
``classify``), identifier validation (``validate-id``), statement
inspection (``parse``, ``entries``, ``validate``), and the headline
``reverse`` command writing a validated reversing entry to disk.
"""

import os
import subprocess  # nosec B404
import sys
import tempfile

# The CLI prints Unicode glyphs (Rich check marks). On Windows a piped or
# legacy console defaults to cp1252, which cannot encode them, so force
# UTF-8 for this script's own output and for the CLI subprocesses below.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UTF8_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}

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


def run_cli(*args: str) -> str:
    """Run one camt053 CLI command and return its stdout (must exit 0)."""
    result = subprocess.run(  # nosec B603
        [sys.executable, "-m", "camt053", *args],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
        env=UTF8_ENV,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"camt053 {' '.join(args)} failed ({result.returncode}):\n"
            f"{result.stderr}"
        )
    return result.stdout


def main() -> None:
    """Exercise the main CLI commands against a temp statement file."""
    print("$ camt053 --version")
    print(run_cli("--version").strip())

    print("\n$ camt053 message-types (first lines)")
    print("\n".join(run_cli("message-types").splitlines()[:5]))

    print("\n$ camt053 classify -r AC04")
    print(run_cli("classify", "-r", "AC04").strip())

    print("\n$ camt053 validate-id -k iban -v GB29NWBK60161331926819")
    print(
        run_cli(
            "validate-id", "-k", "iban", "-v", "GB29NWBK60161331926819"
        ).strip()
    )

    with tempfile.TemporaryDirectory() as tmp:
        stmt_path = os.path.join(tmp, "statement.xml")
        with open(stmt_path, "w", encoding="utf-8") as handle:
            handle.write(STATEMENT)

        print("\n$ camt053 entries -i statement.xml -r AC04")
        print(run_cli("entries", "-i", stmt_path, "-r", "AC04").strip())

        out_path = os.path.join(tmp, "reversal.xml")
        print("\n$ camt053 reverse -i statement.xml -r AC04 -o reversal.xml")
        print(
            run_cli(
                "reverse", "-i", stmt_path, "-r", "AC04", "-o", out_path
            ).strip()
        )

        print("\n$ camt053 validate -i reversal.xml")
        print(run_cli("validate", "-i", out_path).strip())


if __name__ == "__main__":
    main()
