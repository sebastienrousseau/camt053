#!/usr/bin/env python3
"""Example: validate financial identifiers (IBAN, BIC, LEI).

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/validate_identifiers.py

The camt053 validators implement ISO 13616 (IBAN mod-97), ISO 9362 (BIC), and
ISO 17442 (LEI) checks -- the same logic that backs the LSP diagnostics.
"""

from camt053.validation import (
    validate_bic_safe,
    validate_iban_safe,
    validate_lei_safe,
)

CASES = [
    ("IBAN", validate_iban_safe, "GB29NWBK60161331926819", True),
    ("IBAN", validate_iban_safe, "GB00NWBK60161331926819", False),
    ("BIC", validate_bic_safe, "NWBKGB2LXXX", True),
    ("BIC", validate_bic_safe, "NOTABIC", False),
    ("LEI", validate_lei_safe, "5493001KJTIIGC8Y1R12", True),
    ("LEI", validate_lei_safe, "5493001KJTIIGC8Y1R99", False),
]


def main() -> None:
    for kind, validator, value, expected in CASES:
        actual = validator(value)
        status = "OK " if actual == expected else "!! "
        print(f"{status}{kind} {value}: {'valid' if actual else 'invalid'}")


if __name__ == "__main__":
    main()
