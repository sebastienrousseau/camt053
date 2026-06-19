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

"""Optional structured JSON logging with PII redaction for Camt053.

Banking statements carry highly sensitive data (IBANs, BICs, account ids,
party names, amounts). This module provides an **opt-in** logging layer that

* emits one structured JSON record per log line (``timestamp``, ``level``,
  ``event``, plus any structured context), and
* **redacts** sensitive fields before they ever reach a handler, so a log
  aggregator never sees a full IBAN or counterparty name.

It is *off by default*: importing :mod:`camt053` does not configure logging,
add handlers, or change the root logger, so existing behaviour and any host
application's logging configuration are left untouched. Callers opt in either

* programmatically, via :func:`configure_logging`, or
* via the ``CAMT053_LOG_FORMAT`` environment variable (``"json"`` or
  ``"text"``) read by :func:`configure_logging_from_env`.

The library logs through a single named logger (``"camt053"``) obtained with
:func:`get_logger`; until a handler is attached, Python's "last resort" handler
keeps the library quiet at ``WARNING`` and below, matching library best
practice.

Example:
    >>> from camt053 import logging as camt_logging
    >>> camt_logging.redact_iban("GB29NWBK60161331926819")
    '****************6819'
    >>> camt_logging.redact_context({"iban": "GB29NWBK60161331926819"})
    {'iban': '****************6819'}
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

__all__ = [
    "LOGGER_NAME",
    "SENSITIVE_KEYS",
    "JsonFormatter",
    "get_logger",
    "configure_logging",
    "configure_logging_from_env",
    "redact_iban",
    "redact_bic",
    "redact_name",
    "redact_value",
    "redact_context",
    "log_event",
]

#: The single named logger the library logs through.
LOGGER_NAME = "camt053"

#: Context keys whose values are treated as sensitive and redacted. Matching
#: is case-insensitive and substring-based (e.g. ``account_owner_name`` matches
#: ``name``), so callers do not have to enumerate every variant.
SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "iban",
        "bic",
        "bicfi",
        "account",
        "acct",
        "name",
        "owner",
        "party",
        "counterparty",
        "debtor",
        "creditor",
        "amount",
        "amt",
    }
)

#: The fixed mask used for fields that are redacted in full.
_FULL_MASK = "***"


def redact_iban(value: str) -> str:
    """Mask an IBAN, keeping only its last four characters.

    Args:
        value: The IBAN (or IBAN-like account string) to mask.

    Returns:
        The value with every character but the trailing four replaced by
        ``*``. Values of four characters or fewer are masked in full so no
        usable fragment leaks.
    """
    text = str(value)
    if len(text) <= 4:
        return _FULL_MASK
    return "*" * (len(text) - 4) + text[-4:]


def redact_bic(value: str) -> str:
    """Mask a BIC, keeping only its four-character institution prefix.

    A BIC's leading four characters are the (public) institution code; the
    country, location, and branch portions are masked.

    Args:
        value: The BIC / BICFI to mask.

    Returns:
        The first four characters followed by ``*`` padding. Values of four
        characters or fewer are masked in full.
    """
    text = str(value)
    if len(text) <= 4:
        return _FULL_MASK
    return text[:4] + "*" * (len(text) - 4)


def redact_name(value: str) -> str:
    """Mask a party / owner name, keeping only its first initial.

    Args:
        value: The name to mask.

    Returns:
        The first character followed by ``***``, or ``***`` when the name is
        empty.
    """
    text = str(value)
    if not text:
        return _FULL_MASK
    return text[0] + _FULL_MASK


def redact_value(key: str, value: Any) -> Any:
    """Redact a single context value according to its key.

    The redaction strategy is chosen from the key name: IBAN / account keys
    keep their last four characters, BIC keys keep their institution prefix,
    and name / party / amount keys are masked. Non-sensitive keys are returned
    unchanged, and nested mappings are redacted recursively.

    Args:
        key: The context key (matched case-insensitively, by substring).
        value: The value associated with ``key``.

    Returns:
        The redacted value, or the original value when the key is not
        sensitive.
    """
    if isinstance(value, Mapping):
        return redact_context(value)
    lowered = key.lower()
    if "iban" in lowered or "account" in lowered or "acct" in lowered:
        return redact_iban(value) if value is not None else value
    if "bic" in lowered:
        return redact_bic(value) if value is not None else value
    if any(token in lowered for token in ("name", "owner", "party")):
        return redact_name(value) if value is not None else value
    if "amount" in lowered or lowered == "amt" or lowered.endswith("_amt"):
        return _FULL_MASK if value is not None else value
    if lowered in SENSITIVE_KEYS:
        return _FULL_MASK if value is not None else value
    return value


def redact_context(context: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of ``context`` with every sensitive value redacted.

    Args:
        context: A mapping of structured log context.

    Returns:
        A new ``dict`` in which sensitive values have been masked; nested
        mappings are redacted recursively. The input is never mutated.
    """
    return {key: redact_value(key, value) for key, value in context.items()}


class JsonFormatter(logging.Formatter):
    """A :class:`logging.Formatter` that emits one JSON object per record.

    Each record renders to a JSON object with a UTC ISO-8601 ``timestamp``,
    the ``level`` name, the ``logger`` name, the ``event`` (the log message),
    and any structured context attached via the ``extra={"context": {...}}``
    convention. Context values are redacted with :func:`redact_context` before
    serialisation, so sensitive fields never reach the output.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Render ``record`` as a compact JSON string."""
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        context = getattr(record, "context", None)
        if isinstance(context, Mapping):
            payload["context"] = redact_context(context)
        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, sort_keys=True)


def get_logger() -> logging.Logger:
    """Return the library's named logger.

    Returns:
        The ``"camt053"`` :class:`logging.Logger`. The library never attaches
        handlers to it implicitly, so it stays silent until a host application
        (or :func:`configure_logging`) configures it.
    """
    return logging.getLogger(LOGGER_NAME)


def configure_logging(
    *,
    level: int = logging.INFO,
    json_format: bool = True,
    stream: Any | None = None,
) -> logging.Logger:
    """Opt in to Camt053 logging on the library's named logger.

    Attaches a single :class:`logging.StreamHandler` to the ``"camt053"``
    logger, replacing any handler a previous call installed (so repeated calls
    are idempotent and never duplicate output). Propagation to the root logger
    is disabled so the library's records do not leak into an unconfigured root.

    Args:
        level: The logging level to set on the logger (default ``INFO``).
        json_format: When ``True`` (default) emit structured JSON via
            :class:`JsonFormatter`; when ``False`` emit a human-readable line.
        stream: The stream to write to (defaults to ``sys.stderr`` via
            :class:`logging.StreamHandler`).

    Returns:
        The configured ``"camt053"`` logger.
    """
    logger = get_logger()
    for existing in list(logger.handlers):
        if getattr(existing, "_camt053_managed", False):
            logger.removeHandler(existing)
    handler: logging.Handler = logging.StreamHandler(stream)
    handler._camt053_managed = True  # type: ignore[attr-defined]
    if json_format:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s"
            )
        )
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def configure_logging_from_env() -> logging.Logger | None:
    """Configure logging from the ``CAMT053_LOG_FORMAT`` environment variable.

    Reads ``CAMT053_LOG_FORMAT`` (``"json"`` or ``"text"``, case-insensitive)
    and, when set to a recognised value, calls :func:`configure_logging`
    accordingly. The level is taken from ``CAMT053_LOG_LEVEL`` (a standard
    level name, default ``INFO``). When the variable is unset or empty,
    logging is left untouched and ``None`` is returned, preserving the
    off-by-default behaviour.

    Returns:
        The configured logger, or ``None`` when no recognised format was
        requested.
    """
    fmt = os.environ.get("CAMT053_LOG_FORMAT", "").strip().lower()
    if not fmt:
        return None
    if fmt not in ("json", "text"):
        return None
    level_name = os.environ.get("CAMT053_LOG_LEVEL", "INFO").strip().upper()
    level = logging.getLevelName(level_name)
    if not isinstance(level, int):
        level = logging.INFO
    return configure_logging(level=level, json_format=fmt == "json")


def log_event(
    level: int,
    event: str,
    /,
    **context: Any,
) -> None:
    """Log a structured event on the library logger with redacted context.

    A thin convenience wrapper that records ``event`` at ``level`` and attaches
    ``context`` under the ``"context"`` key so :class:`JsonFormatter` (and any
    redaction) applies. Because the library logger has no handler by default,
    this is a cheap no-op until a caller opts in via :func:`configure_logging`.

    Args:
        level: A standard :mod:`logging` level (e.g. ``logging.INFO``).
        event: The event name / message.
        **context: Structured context fields (redacted on output).
    """
    logger = get_logger()
    if not logger.isEnabledFor(level):
        return
    logger.log(level, event, extra={"context": context})
