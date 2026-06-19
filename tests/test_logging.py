# Copyright (C) 2023-2026 Sebastien Rousseau.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the optional structured JSON logging with PII redaction."""

import io
import json
import logging

import pytest

from camt053 import logging as camt_logging
from camt053 import services


@pytest.fixture(autouse=True)
def _reset_logger():
    """Detach any managed handlers from the camt053 logger around each test."""
    logger = camt_logging.get_logger()
    yield
    for handler in list(logger.handlers):
        if getattr(handler, "_camt053_managed", False):
            logger.removeHandler(handler)
    logger.setLevel(logging.NOTSET)
    logger.propagate = True


def test_redact_iban_keeps_last_four():
    """An IBAN is masked except for its trailing four characters."""
    masked = camt_logging.redact_iban("GB29NWBK60161331926819")
    assert masked.endswith("6819")
    assert masked == "*" * (22 - 4) + "6819"


def test_redact_iban_short_value_fully_masked():
    """A short IBAN-like value is masked in full."""
    assert camt_logging.redact_iban("AB12") == "***"


def test_redact_bic_keeps_prefix():
    """A BIC keeps its four-character institution prefix."""
    assert camt_logging.redact_bic("NWBKGB2LXXX") == "NWBK" + "*" * 7


def test_redact_bic_short_value_fully_masked():
    """A short BIC is masked in full."""
    assert camt_logging.redact_bic("NWBK") == "***"


def test_redact_name_keeps_initial():
    """A name is reduced to its first initial."""
    assert camt_logging.redact_name("Acme Treasury Ltd") == "A***"


def test_redact_name_empty_fully_masked():
    """An empty name yields the full mask."""
    assert camt_logging.redact_name("") == "***"


def test_redact_context_masks_sensitive_keys():
    """Sensitive keys are redacted; ordinary keys pass through."""
    ctx = {
        "account_iban": "GB29NWBK60161331926819",
        "servicer_bic": "NWBKGB2LXXX",
        "owner_name": "Acme Treasury Ltd",
        "amount": "1500.00",
        "reason_code": "AC04",
        "count": 3,
    }
    out = camt_logging.redact_context(ctx)
    assert out["account_iban"].endswith("6819")
    assert out["servicer_bic"].startswith("NWBK")
    assert out["owner_name"] == "A***"
    assert out["amount"] == "***"
    assert out["reason_code"] == "AC04"
    assert out["count"] == 3


def test_redact_context_nested_mapping():
    """Nested mappings are redacted recursively."""
    out = camt_logging.redact_context(
        {"acct": {"iban": "GB29NWBK60161331926819"}}
    )
    assert out["acct"]["iban"].endswith("6819")


def test_redact_value_none_passes_through():
    """A None value for a sensitive key is left as None."""
    assert camt_logging.redact_value("iban", None) is None
    assert camt_logging.redact_value("bic", None) is None
    assert camt_logging.redact_value("owner_name", None) is None
    assert camt_logging.redact_value("amount", None) is None


def test_redact_value_amt_suffix_and_sentinel():
    """Amount-style keys and bare sensitive keys are masked."""
    assert camt_logging.redact_value("bal_amt", "10.00") == "***"
    assert camt_logging.redact_value("amt", "10.00") == "***"
    assert camt_logging.redact_value("party", "Globex SA") == "G***"


def test_redact_value_non_sensitive_passes_through():
    """A non-sensitive key returns its value unchanged."""
    assert camt_logging.redact_value("status", "BOOK") == "BOOK"


def test_redact_value_sentinel_only_key():
    """A SENSITIVE_KEYS key not caught by earlier rules is masked."""
    # "debtor"/"creditor" match no substring rule but are sensitive keys.
    assert camt_logging.redact_value("debtor", "Globex") == "***"
    assert camt_logging.redact_value("creditor", None) is None


def test_configure_logging_preserves_foreign_handlers():
    """A pre-existing non-managed handler is left in place."""
    logger = camt_logging.get_logger()
    foreign = logging.StreamHandler(io.StringIO())
    logger.addHandler(foreign)
    try:
        camt_logging.configure_logging(json_format=True, stream=io.StringIO())
        assert foreign in logger.handlers
    finally:
        logger.removeHandler(foreign)


def test_json_formatter_emits_structured_record():
    """The JSON formatter renders timestamp, level, event, and context."""
    stream = io.StringIO()
    camt_logging.configure_logging(json_format=True, stream=stream)
    camt_logging.log_event(
        logging.INFO,
        "statement.parsed",
        iban="GB29NWBK60161331926819",
    )
    record = json.loads(stream.getvalue())
    assert record["level"] == "INFO"
    assert record["event"] == "statement.parsed"
    assert record["logger"] == "camt053"
    assert "timestamp" in record
    assert record["context"]["iban"].endswith("6819")


def test_json_formatter_includes_exception():
    """An exc_info record carries a formatted error field."""
    stream = io.StringIO()
    logger = camt_logging.configure_logging(json_format=True, stream=stream)
    try:
        raise ValueError("boom")
    except ValueError:
        logger.error("failed", exc_info=True)
    record = json.loads(stream.getvalue())
    assert "ValueError: boom" in record["error"]


def test_json_formatter_without_context():
    """A record with no context omits the context key."""
    stream = io.StringIO()
    logger = camt_logging.configure_logging(json_format=True, stream=stream)
    logger.info("plain event")
    record = json.loads(stream.getvalue())
    assert "context" not in record


def test_text_format_is_human_readable():
    """The text formatter emits a plain line, not JSON."""
    stream = io.StringIO()
    camt_logging.configure_logging(json_format=False, stream=stream)
    camt_logging.log_event(logging.INFO, "hello")
    out = stream.getvalue()
    assert "hello" in out
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)


def test_configure_logging_is_idempotent():
    """Repeated configuration does not duplicate handlers / output."""
    stream = io.StringIO()
    camt_logging.configure_logging(json_format=True, stream=stream)
    camt_logging.configure_logging(json_format=True, stream=stream)
    logger = camt_logging.get_logger()
    managed = [
        h for h in logger.handlers if getattr(h, "_camt053_managed", False)
    ]
    assert len(managed) == 1


def test_off_by_default_no_output():
    """Without configuration, log_event produces no output."""
    logger = camt_logging.get_logger()
    # No managed handler, and not enabled below WARNING by default.
    assert not any(
        getattr(h, "_camt053_managed", False) for h in logger.handlers
    )
    # Should not raise and should be a cheap no-op.
    camt_logging.log_event(logging.DEBUG, "noisy", iban="X")


def test_configure_from_env_json(monkeypatch):
    """CAMT053_LOG_FORMAT=json configures JSON logging."""
    monkeypatch.setenv("CAMT053_LOG_FORMAT", "JSON")
    monkeypatch.setenv("CAMT053_LOG_LEVEL", "DEBUG")
    logger = camt_logging.configure_logging_from_env()
    assert logger is not None
    assert logger.level == logging.DEBUG


def test_configure_from_env_text(monkeypatch):
    """CAMT053_LOG_FORMAT=text configures human-readable logging."""
    monkeypatch.setenv("CAMT053_LOG_FORMAT", "text")
    logger = camt_logging.configure_logging_from_env()
    assert logger is not None


def test_configure_from_env_unset_is_noop(monkeypatch):
    """An unset CAMT053_LOG_FORMAT leaves logging untouched."""
    monkeypatch.delenv("CAMT053_LOG_FORMAT", raising=False)
    assert camt_logging.configure_logging_from_env() is None


def test_configure_from_env_unknown_format_is_noop(monkeypatch):
    """An unrecognised format value is ignored."""
    monkeypatch.setenv("CAMT053_LOG_FORMAT", "yaml")
    assert camt_logging.configure_logging_from_env() is None


def test_configure_from_env_bad_level_defaults_info(monkeypatch):
    """An invalid level name falls back to INFO."""
    monkeypatch.setenv("CAMT053_LOG_FORMAT", "json")
    monkeypatch.setenv("CAMT053_LOG_LEVEL", "NOTALEVEL")
    logger = camt_logging.configure_logging_from_env()
    assert logger is not None
    assert logger.level == logging.INFO


def test_services_reexports_logging():
    """The services facade re-exports the logging configuration helpers."""
    assert services.configure_logging is camt_logging.configure_logging
    assert (
        services.configure_logging_from_env
        is camt_logging.configure_logging_from_env
    )


def test_parse_emits_redacted_log(statement_xml):
    """Parsing through services emits a structured, redacted parse event."""
    stream = io.StringIO()
    camt_logging.configure_logging(json_format=True, stream=stream)
    services.parse_statement(statement_xml)
    lines = [json.loads(line) for line in stream.getvalue().splitlines()]
    events = {line["event"] for line in lines}
    assert "statement.parsed" in events
