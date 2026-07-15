#!/usr/bin/env python3
"""Example: the security guards for untrusted XML, paths, and log fields.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/security_guards.py

Three defence layers from ``camt053.security``: ``guard_xml_payload``
rejects hostile XML (DOCTYPE / ENTITY declarations, oversized payloads)
before it reaches any parser; ``validate_path`` blocks path traversal and
confines file access to allowed base directories; ``sanitize_for_log``
strips control characters so untrusted input cannot forge log lines.
"""

from camt053.security import (
    XmlSecurityError,
    guard_xml_payload,
    sanitize_for_log,
    validate_path,
)
from camt053.security.path_validator import PathValidationError
from camt053.services import guard_xml

BENIGN = '<?xml version="1.0"?><Document/>'
XXE_ATTACK = (
    '<?xml version="1.0"?>'
    '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
    "<Document>&xxe;</Document>"
)


def main() -> None:
    """Demonstrate each guard accepting good input and refusing bad."""
    # 1. XML payload guard: DOCTYPE / ENTITY declarations are refused.
    guard_xml_payload(BENIGN)
    print("guard_xml_payload: benign payload accepted")
    try:
        guard_xml_payload(XXE_ATTACK)
    except XmlSecurityError as exc:
        print(f"guard_xml_payload: XXE payload refused ({exc})")

    # Oversized payloads are refused before parsing ever starts.
    try:
        guard_xml("<Document>" + "A" * 100 + "</Document>", max_bytes=50)
    except XmlSecurityError as exc:
        print(f"services.guard_xml: oversized payload refused ({exc})")

    # 2. Path guard: traversal sequences never reach the filesystem.
    safe = validate_path("output/reversal.xml")
    print(f"\nvalidate_path: confined to an allowed base -> ...{safe[-20:]}")
    try:
        validate_path("../../etc/passwd")
    except PathValidationError as exc:
        print(f"validate_path: traversal refused ({exc})")

    # 3. Log sanitiser: control characters cannot forge log lines.
    hostile = "job-42\ninjected: FAKE ADMIN LOG LINE\r\x1b[31m"
    print(f"\nsanitize_for_log: {sanitize_for_log(hostile)!r}")
    print(f"truncation: {sanitize_for_log('x' * 200, max_length=20)!r}")


if __name__ == "__main__":
    main()
