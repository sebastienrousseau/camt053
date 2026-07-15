#!/usr/bin/env python3
"""Example: ISO 4217 currency validation and minor-unit lookup.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/validate_currencies.py

Amount handling needs two facts per currency: is the code a real ISO 4217
currency, and how many decimal places does it carry? EUR has 2 minor
units, JPY has 0, BHD has 3. ``camt053.validation`` answers both, and the
services facade folds them into a single JSON-ready report.
"""

from camt053.services import validate_currency as validate_currency_service
from camt053.validation import currency_minor_units, validate_currency

CASES = ["EUR", "JPY", "BHD", "eur", "XXX", "NOPE"]


def main() -> None:
    """Check a spread of currency codes, valid and not."""
    print("validation primitives:")
    for code in CASES:
        valid = validate_currency(code.upper())
        units = currency_minor_units(code.upper())
        print(f"  {code:<5} valid={str(valid):<5} minor_units={units}")

    print("\nservices facade (case-insensitive, one dict per code):")
    for code in ("eur", "JPY", "NOPE"):
        print(f"  {validate_currency_service(code)}")


if __name__ == "__main__":
    main()
