#!/usr/bin/env python3
"""Example: schema-version detection, classification, and XSD pre-flight.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/schema_version_preflight.py

Before processing an incoming payload, detect which camt.05x revision it
claims (``detect_schema_version``), classify that revision against the
supported set (``classify_schema_version`` / ``validate_schema_version``),
look up the registered per-version profile, and validate the payload
against its official ISO XSD (``services.validate_statement``).
"""

from camt053.profiles import get_profile, list_profiles, profile_for_xml
from camt053.schema_version import (
    UnsupportedSchemaError,
    classify_schema_version,
    detect_schema_version,
    validate_schema_version,
)
from camt053.services import validate_statement

VALID_STATEMENT = """<?xml version="1.0" encoding="UTF-8"?>
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
        <ValDt><Dt>2026-06-14</Dt></ValDt>
        <BkTxCd><Domn><Cd>PMNT</Cd>
          <Fmly><Cd>RCDT</Cd><SubFmlyCd>RRTN</SubFmlyCd></Fmly></Domn>
        </BkTxCd>
        <NtryDtls><TxDtls>
          <RtrInf><Rsn><Cd>AC04</Cd></Rsn></RtrInf>
        </TxDtls></NtryDtls>
      </Ntry>
    </Stmt>
  </BkToCstmrStmt>
</Document>"""

UNKNOWN_REVISION = VALID_STATEMENT.replace(".001.14", ".001.99")


def main() -> None:
    """Pre-flight two payloads: a current revision and an unknown one."""
    # 1. Detect + classify the schema revision from the namespace.
    version = detect_schema_version(VALID_STATEMENT)
    print(f"detected version:  {version}")
    print(f"classification:    {classify_schema_version(version)}")

    report = validate_schema_version(VALID_STATEMENT)
    print(f"pre-flight report: {report}")

    # 2. Strict mode refuses unknown revisions outright.
    try:
        validate_schema_version(UNKNOWN_REVISION, strict=True)
    except UnsupportedSchemaError as exc:
        print(f"strict mode refused .99: {exc.classification}")

    # 3. The per-version profile registry.
    names = sorted(type(p).__name__ for p in list_profiles())
    print(f"\nregistered profiles: {names}")
    profile = get_profile("camt.053.001.14")
    print(f"get_profile('camt.053.001.14') -> {type(profile).__name__}")
    by_payload = profile_for_xml(VALID_STATEMENT)
    print(f"profile_for_xml(payload)       -> {type(by_payload).__name__}")

    # 4. Full XSD validation against the bundled official schema.
    xsd_report = validate_statement(VALID_STATEMENT)
    print(
        f"\nXSD validation: valid={xsd_report['valid']} "
        f"({xsd_report['message_type']}, "
        f"{len(xsd_report['errors'])} errors)"
    )


if __name__ == "__main__":
    main()
