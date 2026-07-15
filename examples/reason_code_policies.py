#!/usr/bin/env python3
"""Example: ISO return reason codes and handling policies.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/reason_code_policies.py

The ``camt053.parse.reason_codes`` catalogue maps every known ISO external
return reason code to a name and a handling action (``return`` / ``retry``
/ ``ignore``). This script lists the catalogue, validates and classifies
codes, and shows the policy override hooks plus the credit/debit flip used
by the reversal builder.
"""

from camt053.constants import reason_action_policy, reverse_credit_debit
from camt053.parse.reason_codes import (
    classify_reason,
    describe_reason,
    is_known_reason,
    list_reason_codes,
    reason_policy,
    validate_reason_code,
)


def main() -> None:
    """Explore the reason-code catalogue and its action policy."""
    codes = list_reason_codes()
    print(f"catalogue: {len(codes)} known reason codes, first three:")
    for row in codes[:3]:
        print(f"  {row['code']}  {row['name']}")

    print(f"\ndescribe_reason('AC04') -> {describe_reason('AC04')}")
    print(f"is_known_reason('AC04') -> {is_known_reason('AC04')}")
    print(f"is_known_reason('ZZ99') -> {is_known_reason('ZZ99')}")

    for code in ("AC04", "zz99"):
        report = validate_reason_code(code)
        print(
            f"validate_reason_code({code!r}) -> "
            f"valid={report['valid']} name={report['name']!r}"
        )

    # Classification: account-level rejections return, transient
    # conditions (e.g. AM04 insufficient funds) retry.
    for code in ("AC04", "AM04", "NARR"):
        result = classify_reason(code)
        print(f"classify_reason({code!r}) -> {result['action']}")

    # Site policy overrides win over the built-in mapping.
    override = classify_reason("AC04", overrides={"AC04": "retry"})
    print(f"with override AC04->retry   -> {override['action']}")

    policy = reason_policy()
    print(
        f"\nreason_policy: default={policy['default']!r}, "
        f"actions={policy['actions']}, "
        f"{len(policy['policy'])} mapped codes"
    )

    # The raw built-in mapping, and the reversal credit/debit flip.
    builtin = reason_action_policy()
    print(f"constants.reason_action_policy: AC04 -> {builtin['AC04']}")
    print(f"reverse_credit_debit('CRDT') -> {reverse_credit_debit('CRDT')}")
    print(f"reverse_credit_debit('DBIT') -> {reverse_credit_debit('DBIT')}")


if __name__ == "__main__":
    main()
