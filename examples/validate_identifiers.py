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
    # The identifier value itself is not printed: even synthetic IBAN/LEI
    # literals are treated as sensitive by static analysis, so the demo
    # reports only the validation outcome per case.
    for index, (kind, validator, value, expected) in enumerate(CASES, 1):
        actual = validator(value)
        status = "OK " if actual == expected else "!! "
        verdict = "valid" if actual else "invalid"
        expected_verdict = "valid" if expected else "invalid"
        print(
            f"{status}case {index} ({kind}): "
            f"got {verdict}, expected {expected_verdict}"
        )


if __name__ == "__main__":
    main()
