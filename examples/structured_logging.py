#!/usr/bin/env python3
"""Example: structured JSON logging with automatic PII redaction.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/structured_logging.py

``camt053.logging`` emits machine-parseable JSON log lines and redacts
financial identifiers before they ever hit the log stream: IBANs keep the
country code and last four characters, BICs keep the bank code, names are
masked entirely. Configuration works programmatically or via the
``CAMT053_LOG_FORMAT`` / ``CAMT053_LOG_LEVEL`` environment variables.
"""

import io
import logging
import os

from camt053.logging import (
    configure_logging,
    configure_logging_from_env,
    get_logger,
    log_event,
    redact_bic,
    redact_context,
    redact_iban,
    redact_name,
    redact_value,
)


def main() -> None:
    """Emit redacted JSON log events to an in-memory stream."""
    # 1. The redaction helpers, standalone.
    print(f"redact_iban -> {redact_iban('GB29NWBK60161331926819')}")
    print(f"redact_bic  -> {redact_bic('NWBKGB2LXXX')}")
    print(f"redact_name -> {redact_name('Acme Treasury Ltd')}")
    print(
        f"redact_value('iban', ...) -> {redact_value('iban', 'GB29NWBK60161331926819')}"
    )
    context = {"iban": "GB29NWBK60161331926819", "records": 3}
    print(f"redact_context -> {redact_context(context)}")

    # 2. JSON logging to a stream (a file / stdout in production).
    stream = io.StringIO()
    logger = configure_logging(
        level=logging.INFO, json_format=True, stream=stream
    )
    assert logger is get_logger()

    log_event(
        logging.INFO,
        "reversal.generated",
        reason_code="AC04",
        iban="GB29NWBK60161331926819",
        records=1,
    )
    print(
        f"\nJSON log line (IBAN auto-redacted):\n{stream.getvalue().strip()}"
    )

    # 3. Environment-driven configuration (12-factor style).
    os.environ["CAMT053_LOG_FORMAT"] = "text"
    os.environ["CAMT053_LOG_LEVEL"] = "WARNING"
    env_logger = configure_logging_from_env()
    assert env_logger is not None
    print(f"\nconfigured from env: level={env_logger.level} (WARNING=30)")
    del os.environ["CAMT053_LOG_FORMAT"], os.environ["CAMT053_LOG_LEVEL"]


if __name__ == "__main__":
    main()
