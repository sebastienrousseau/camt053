#!/usr/bin/env python3
"""Example: the shared service facade.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/services_facade.py

The same `camt053.services` functions back the CLI, REST API, MCP server, and
LSP server. This script exercises the reference and validation helpers.
"""

from camt053 import services


def main() -> None:
    print("Supported message types:")
    for row in services.list_message_types():
        print(f"  {row['message_type']}  {row['name']}")

    print("\nA few ISO return reason codes:")
    for row in services.list_return_reasons()[:4]:
        print(f"  {row['code']}  {row['name']}")

    print("\nRequired reversing-entry fields (camt.053.001.14):")
    print("  " + ", ".join(services.get_required_fields("camt.053.001.14")))

    print("\nIdentifier validation:")
    for kind, value in [
        ("iban", "GB29NWBK60161331926819"),
        ("bic", "NWBKGB2LXXX"),
        ("lei", "5493001KJTIIGC8Y1R12"),
    ]:
        result = services.validate_identifier(kind, value)
        print(
            f"  {kind.upper()} {value}: {'valid' if result['valid'] else 'invalid'}"
        )


if __name__ == "__main__":
    main()
