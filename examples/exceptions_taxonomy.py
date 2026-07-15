#!/usr/bin/env python3
"""Example: the typed exception taxonomy and strict validators.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/exceptions_taxonomy.py

Every camt053 failure raises a typed exception rooted at ``Camt053Error``,
so callers can catch precisely (a parse failure) or broadly (anything the
library raised). The strict validator variants raise instead of returning
``False``: ``validate_iban`` raises ``InvalidIBANError`` where
``validate_iban_safe`` returns a bool.
"""

from camt053 import parse_statement
from camt053.exceptions import (
    Camt053Error,
    InvalidBICError,
    InvalidIBANError,
    InvalidLEIError,
    ReversalGenerationError,
    StatementParseError,
)
from camt053.services import generate_reversal
from camt053.validation import (
    validate_bic,
    validate_bic_format,
    validate_iban,
    validate_iban_checksum,
    validate_iban_format,
    validate_lei,
    validate_lei_checksum,
    validate_lei_format,
)

NO_MATCH_STATEMENT = """<?xml version="1.0" encoding="UTF-8"?>
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
      </Ntry>
    </Stmt>
  </BkToCstmrStmt>
</Document>"""


def main() -> None:
    """Trigger and catch each of the main typed exceptions."""
    # 1. Parse failures raise StatementParseError.
    try:
        parse_statement("<not-a-statement/>")
    except StatementParseError as exc:
        print(f"StatementParseError:     {exc}")

    # 2. Nothing to reverse raises ReversalGenerationError.
    try:
        generate_reversal(NO_MATCH_STATEMENT, reason_code="AC04")
    except ReversalGenerationError as exc:
        print(f"ReversalGenerationError: {exc}")

    # 3. Strict identifier validators raise typed errors.
    print(
        f"\nvalidate_iban (good) -> {validate_iban('GB29NWBK60161331926819')}"
    )
    for label, func, value, exc_type in (
        ("IBAN", validate_iban, "GB00NWBK60161331926819", InvalidIBANError),
        ("BIC", validate_bic, "NOTABIC", InvalidBICError),
        ("LEI", validate_lei, "5493001KJTIIGC8Y1R99", InvalidLEIError),
    ):
        try:
            func(value)
        except exc_type as exc:
            print(f"Invalid{label}Error: {exc}")

    # 4. Format vs checksum: the two halves of strict validation.
    print(
        f"\niban format ok:   {validate_iban_format('GB29NWBK60161331926819')}"
    )
    print(
        f"iban checksum ok: {validate_iban_checksum('GB29NWBK60161331926819')}"
    )
    print(f"bic format ok:    {validate_bic_format('NWBKGB2LXXX')}")
    print(f"lei format ok:    {validate_lei_format('5493001KJTIIGC8Y1R12')}")
    print(f"lei checksum ok:  {validate_lei_checksum('5493001KJTIIGC8Y1R12')}")

    # 5. Everything above shares one catchable root.
    try:
        parse_statement("")
    except Camt053Error as exc:
        print(f"\ncaught via Camt053Error root: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
