#!/usr/bin/env python3
"""Example: JSON Schema validation of flat reversing-entry records.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/validate_records_schema.py

Every supported message type ships a JSON Schema describing its flat
reversing-entry record. ``SchemaValidator`` validates single records,
rows, and whole batches against it, and exposes per-field introspection
(required fields, field schema, field description). The services facade
wraps the same machinery for CI-style batch reports.
"""

from camt053.services import (
    get_input_schema,
    get_required_fields,
    validate_records,
)
from camt053.validation import SchemaValidator

MESSAGE_TYPE = "camt.053.001.14"

GOOD_RECORD = {
    "statement_msg_id": "RVSL-STMT-0001",
    "creation_date_time": "2026-06-15T08:00:00",
    "statement_id": "RVSL-STMT-0001",
    "account_id": "GB29NWBK60161331926819",
    "entry_ref": "RVSL-NTRY-0001",
    "amount": "1500.00",
    "currency": "EUR",
    "credit_debit": "DBIT",
    "reason_code": "AC04",
}

BAD_RECORD = dict(GOOD_RECORD, credit_debit="SIDEWAYS", amount="")


def main() -> None:
    """Introspect the schema, then validate good and bad records."""
    validator = SchemaValidator(MESSAGE_TYPE)

    # 1. Introspection: what does a record need to look like?
    required = validator.get_required_fields()
    print(f"required fields: {required}")
    field_schema = validator.get_field_schema("credit_debit")
    print(f"credit_debit schema: {field_schema}")
    description = validator.get_field_description("credit_debit")
    print(f"credit_debit description: {description}")

    # 2. Validate one record / one row.
    errors = validator.validate_data(GOOD_RECORD)
    print(f"\ngood record: {len(errors)} error(s)")
    ok, row_errors = validator.validate_row(BAD_RECORD)
    print(f"bad record:  ok={ok}")
    for err in row_errors:
        print(f"  {err.path}: {err.message}")

    # 3. Validate a batch.
    total, valid_count, per_row = validator.validate_batch(
        [GOOD_RECORD, BAD_RECORD]
    )
    print(f"batch: {valid_count}/{total} valid")

    # 4. The services facade: same checks, JSON-ready report.
    report = validate_records(MESSAGE_TYPE, [GOOD_RECORD, BAD_RECORD])
    print(
        f"services.validate_records: valid={report['valid']} "
        f"({report['valid_count']}/{report['total']}, "
        f"{len(report['errors'])} error(s))"
    )

    # 5. The raw JSON Schema and required fields, via the facade.
    schema = get_input_schema(MESSAGE_TYPE)
    print(
        f"\ninput schema: {len(schema.get('properties', {}))} properties, "
        f"required={get_required_fields(MESSAGE_TYPE)}"
    )


if __name__ == "__main__":
    main()
