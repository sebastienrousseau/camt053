#!/usr/bin/env python3
"""Example: SWIFT X charset cleansing for names and narratives.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/swift_charset_cleansing.py

SWIFT FIN / CBPR+ rails only accept the SWIFT X character set. The
``camt053.compliance.swift_charset`` helpers detect non-conforming text
(``is_swift_x``), transliterate or strip it (``cleanse_text`` /
``cleanse_field``), and cleanse whole reversing-entry record batches
(``cleanse_records``), reporting every altered field.
"""

from camt053.compliance import (
    cleanse_field,
    cleanse_records,
    cleanse_text,
    is_swift_x,
)
from camt053.services import cleanse_records as cleanse_records_service


def main() -> None:
    """Cleanse accented / oversized fields down to the SWIFT X charset."""
    # 1. Detection.
    print(f"is_swift_x('ACME LTD')        -> {is_swift_x('ACME LTD')}")
    print(
        f"is_swift_x('Société Générale') -> {is_swift_x('Société Générale')}"
    )

    # 2. Single value: transliterate accents, enforce a maximum length.
    report = cleanse_text("Société Générale", max_length=35, field_name="Nm")
    print(
        f"\ncleanse_text: {report.original!r} -> {report.cleansed!r} "
        f"(changed={report.changed})"
    )
    print(f"as dict: {report.to_dict()}")

    # 3. Single record field, mutated in place.
    record = {"account_owner_name": "Büro Möller & Söhne"}
    field_report = cleanse_field(record, "account_owner_name", max_length=35)
    assert field_report is not None
    print(f"\ncleanse_field: record now {record}")

    # 4. A whole batch of reversing-entry records.
    records = [
        {"account_owner_name": "Ærøskøbing Havn", "additional_info": "OK"},
        {"account_owner_name": "PLAIN NAME LTD"},
    ]
    reports = cleanse_records(records)
    print(f"cleanse_records: {len(reports)} field(s) altered")

    # 5. The services facade wraps the same cleansing with a summary dict.
    records = [{"account_owner_name": "Zürich Straße 1"}]
    summary = cleanse_records_service(records)
    print(f"services.cleanse_records: changed={summary['changed']}")
    for field in summary["fields"]:
        print(
            f"  {field['field']}: {field['original']!r} -> {field['cleansed']!r}"
        )


if __name__ == "__main__":
    main()
