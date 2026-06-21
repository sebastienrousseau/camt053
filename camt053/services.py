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

"""High-level service facade for Camt053.

A small, dependency-light layer that exposes the library's core capabilities as
plain functions returning plain data. It is the single shared backend for the
CLI, the REST API, the Model Context Protocol (MCP) server, and the Language
Server Protocol (LSP) server, so every interface behaves identically.

The headline capability is the one-shot reversing-entry workflow: read an
incoming camt.053 statement, find the entries carrying a return reason code
(e.g. AC04 Closed Account), and emit a validated reversing entry.

Example:
    >>> from camt053 import services
    >>> [m["message_type"] for m in services.list_message_types()][:1]
    ['camt.052.001.08']
    >>> services.validate_identifier("bic", "NWBKGB2LXXX")["valid"]
    True
"""

import glob
import json
import logging
import os
from collections.abc import Iterator
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from camt053.compliance.cbpr_readiness import (
    CBPR_CUTOVER_DATE,
    check_cbpr_readiness,
)
from camt053.compliance.swift_charset import (
    cleanse_records as _cleanse_records,
)
from camt053.constants import (
    OUTPUT_FORMAT_CAMT053,
    message_names,
    valid_xml_types,
)
from camt053.exceptions import Camt053Error
from camt053.logging import (
    configure_logging,
    configure_logging_from_env,
    log_event,
)
from camt053.parse.dedupe import (
    DEDUPE_KEY_SEPARATOR,
)
from camt053.parse.dedupe import (
    compute_dedupe_key as _compute_dedupe_key,
)
from camt053.parse.dedupe import (
    compute_dedupe_keys as _compute_dedupe_keys,
)
from camt053.parse.reason_codes import (
    classify_reason as _classify_reason,
)
from camt053.parse.reason_codes import (
    list_reason_codes,
)
from camt053.parse.reason_codes import (
    reason_policy as _reason_policy,
)
from camt053.parse.reason_codes import (
    validate_reason_code as _validate_reason_code,
)
from camt053.parse.statement_parser import (
    iter_statement_entries as _iter_statement_entries,
)
from camt053.parse.statement_parser import parse_document as _parse_document
from camt053.reversal.reversal import (
    build_reversal_records_for_statements,
    stable_reversal_reference,
)
from camt053.validation.bic_validator import validate_bic_safe
from camt053.validation.currency_validator import (
    currency_minor_units,
)
from camt053.validation.currency_validator import (
    validate_currency as _validate_currency,
)
from camt053.validation.iban_validator import validate_iban_safe
from camt053.validation.lei_validator import validate_lei_safe
from camt053.validation.schema_validator import SchemaValidator
from camt053.xml.generate_xml import generate_reversal_xml
from camt053.xml.serialize_statement import (
    serialize_document as _serialize_document,
)
from camt053.xml.validate_statement import (
    validate_statement as _validate_statement,
)

__all__ = [
    "list_message_types",
    "list_return_reasons",
    "validate_reason_code",
    "classify_reason",
    "reason_policy",
    "get_input_schema",
    "get_required_fields",
    "validate_records",
    "validate_identifier",
    "validate_currency",
    "parse_statement",
    "serialize_statement",
    "validate_statement",
    "list_entries",
    "iter_entries",
    "filter_entries",
    "build_reversal",
    "cleanse_records",
    "generate_reversal",
    "generate",
    "generate_batch",
    "configure_logging",
    "configure_logging_from_env",
    "guard_xml",
    "check_cbpr_readiness",
    "CBPR_CUTOVER_DATE",
    "compute_dedupe_key",
    "compute_dedupe_keys",
    "DEDUPE_KEY_SEPARATOR",
    "stable_reversal_reference",
]

from camt053.security.xml_guard import (  # noqa: E402
    DEFAULT_MAX_XML_BYTES,
    guard_xml_payload,
)

_IDENTIFIER_VALIDATORS = {
    "iban": validate_iban_safe,
    "bic": validate_bic_safe,
    "lei": validate_lei_safe,
}

DEFAULT_REASON_CODE = "AC04"


def list_message_types() -> list[dict[str, str]]:
    """Return every supported message type with its human-readable name.

    Returns:
        A list of ``{"message_type": ..., "name": ...}`` dictionaries.
    """
    return [
        {"message_type": mt, "name": message_names[mt]}
        for mt in valid_xml_types
    ]


def list_return_reasons() -> list[dict[str, str]]:
    """Return every known ISO external return reason code with its name.

    Returns:
        A list of ``{"code": ..., "name": ...}`` dictionaries.
    """
    return list_reason_codes()


def validate_reason_code(code: str) -> dict[str, Any]:
    """Validate an ISO external return reason code.

    Args:
        code: An ISO external return reason code (case-insensitive).

    Returns:
        ``{"code": str, "name": str, "valid": bool}``. Unknown codes report
        ``valid=False`` with the generic ``"Unknown reason code"`` name.
    """
    return _validate_reason_code(code)


def classify_reason(
    code: str,
    overrides: dict[str, str] | None = None,
    default: str | None = None,
) -> dict[str, str]:
    """Classify a return reason code into a handling action.

    Maps an ISO external return reason code to ``"return"``, ``"retry"``, or
    ``"ignore"`` using the built-in policy (account-level rejections return,
    transient conditions retry, informational reasons ignore). The lookup is
    case-insensitive; unknown / unmapped codes resolve to ``default``.

    Args:
        code: An ISO external return reason code (case-insensitive).
        overrides: Optional code -> action mapping taking precedence over the
            built-in policy (keys matched case-insensitively).
        default: The action for codes the policy / overrides do not cover
            (defaults to ``"return"``).

    Returns:
        ``{"code": str, "name": str, "action": str}``.
    """
    return _classify_reason(code, overrides=overrides, default=default)


def reason_policy(
    overrides: dict[str, str] | None = None,
    default: str | None = None,
) -> dict[str, Any]:
    """Return the full reason-code action policy.

    Args:
        overrides: Optional code -> action mapping taking precedence over the
            built-in policy (keys matched case-insensitively).
        default: The action for codes the policy / overrides do not cover
            (defaults to ``"return"``).

    Returns:
        ``{"default": str, "actions": [str, ...], "policy": {code: action}}``.
    """
    return _reason_policy(overrides=overrides, default=default)


def get_input_schema(message_type: str) -> dict[str, Any]:
    """Return the JSON Schema for a message type's reversing-entry record.

    Args:
        message_type: A supported ISO 20022 cash-management message type.

    Returns:
        The parsed JSON Schema document.

    Raises:
        ValueError: If the message type is not supported.
    """
    validator = SchemaValidator(message_type)
    return dict(validator.schema)


def get_required_fields(message_type: str) -> list[str]:
    """Return the required reversing-entry field names for a message type.

    Args:
        message_type: A supported ISO 20022 cash-management message type.

    Returns:
        The list of required field names.

    Raises:
        ValueError: If the message type is not supported.
    """
    return SchemaValidator(message_type).get_required_fields()


def validate_records(
    message_type: str, records: list[dict[str, Any]]
) -> dict[str, Any]:
    """Validate flat reversing-entry records against a type's input schema.

    Args:
        message_type: A supported ISO 20022 cash-management message type.
        records: One or more flat reversing-entry records.

    Returns:
        A report dictionary:
        ``{"valid": bool, "total": int, "valid_count": int,
        "errors": [{"row": int, "path": str, "message": str}, ...]}``.

    Raises:
        ValueError: If the message type is not supported.
    """
    validator = SchemaValidator(message_type)
    total, valid_count, row_errors = validator.validate_batch(records)
    errors = [
        {"row": row_idx, "path": err.path, "message": err.message}
        for row_idx, errs in row_errors
        for err in errs
    ]
    return {
        "valid": len(errors) == 0,
        "total": total,
        "valid_count": valid_count,
        "errors": errors,
    }


def validate_identifier(kind: str, value: str) -> dict[str, Any]:
    """Validate a financial identifier (IBAN, BIC, or LEI).

    Args:
        kind: One of ``"iban"``, ``"bic"``, or ``"lei"`` (case-insensitive).
        value: The identifier value to check.

    Returns:
        ``{"kind": str, "value": str, "valid": bool}``.

    Raises:
        ValueError: If ``kind`` is not a supported identifier type.
    """
    key = kind.lower()
    validator = _IDENTIFIER_VALIDATORS.get(key)
    if validator is None:
        supported = ", ".join(sorted(_IDENTIFIER_VALIDATORS))
        raise ValueError(
            f"Unsupported identifier kind: {kind!r}. "
            f"Expected one of: {supported}."
        )
    return {"kind": key, "value": value, "valid": bool(validator(value))}


def validate_currency(code: str) -> dict[str, Any]:
    """Validate an ISO 4217 alphabetic currency code.

    The check is case-insensitive. The returned ``minor_units`` is the number
    of decimal places in the currency's subdivision (e.g. EUR=2, JPY=0), or
    ``None`` when the code is unknown.

    Args:
        code: A three-letter ISO 4217 currency code.

    Returns:
        ``{"code": str, "valid": bool, "minor_units": int | None}``.
    """
    canonical = (code or "").strip().upper()
    return {
        "code": canonical,
        "valid": _validate_currency(canonical),
        "minor_units": currency_minor_units(canonical),
    }


def parse_statement(xml: str) -> dict[str, Any]:
    """Parse an incoming camt.05x statement into plain data.

    Args:
        xml: The raw statement XML as a string.

    Returns:
        The parsed document as a JSON-serialisable dict (group header plus
        statements, each with its account, balances, and entries).

    Raises:
        StatementParseError: If the XML is malformed or unrecognised.
    """
    return _parse_document(xml).to_dict()


def compute_dedupe_key(xml: str) -> str:
    """Return the canonical dedupe key for an incoming statement's first stmt.

    Convenience wrapper that parses the payload and returns the
    ``"{MsgId}:{StmtId}:{ElctrncSeqNb}"`` key. Two payloads that share
    this key represent the same statement (typically a bank replay) and
    should be processed at most once downstream.

    Args:
        xml: The raw camt.05x statement XML as a string.

    Returns:
        The colon-joined dedupe key for the first statement.

    Raises:
        ValueError: If the document carries zero statements.
        StatementParseError: If the XML is malformed or unrecognised.
    """
    return _compute_dedupe_key(_parse_document(xml))


def compute_dedupe_keys(xml: str) -> list[str]:
    """Return one dedupe key per statement bundled in the document.

    Useful for multi-statement documents (e.g. a daily multi-account
    report). The first key matches :func:`compute_dedupe_key`'s output.

    Args:
        xml: The raw camt.05x statement XML as a string.

    Returns:
        A list of dedupe keys in document order; empty when no
        statements are present.

    Raises:
        StatementParseError: If the XML is malformed or unrecognised.
    """
    return _compute_dedupe_keys(_parse_document(xml))


def serialize_statement(xml: str) -> str:
    """Round-trip a statement: parse it, then re-serialise it to camt.053 XML.

    Parses the incoming camt.05x statement into the typed model and renders it
    back to a validated ``camt.053.001.14`` document. The result is
    deterministic and preserves the account, balances, and entries (their
    references, amounts, currencies, credit/debit indicators, and return
    reasons), so ``parse_statement(serialize_statement(xml))`` reproduces the
    same parsed data.

    Args:
        xml: The raw statement XML as a string.

    Returns:
        The re-serialised, XSD-validated camt.053.001.14 document as a string.

    Raises:
        StatementParseError: If the XML is malformed or unrecognised.
        XMLGenerationError: If the document carries no statement or the
            rendered XML does not validate against the bundled XSD.
    """
    return _serialize_document(_parse_document(xml))


def validate_statement(xml: str) -> dict[str, Any]:
    """Validate an incoming statement against its official ISO camt XSD.

    Detects the document's message type from its namespace and validates it
    against the matching official XSD bundled with the package.

    Args:
        xml: The raw statement XML as a string.

    Returns:
        ``{"valid": bool, "message_type": str, "errors": [str, ...]}``.

    Raises:
        StatementParseError: If the XML is malformed / unrecognised, or no
            official XSD is bundled for the detected message type.
    """
    return _validate_statement(xml)


def list_entries(xml: str, *, streaming: bool = False) -> list[dict[str, Any]]:
    """Parse a statement and return every entry across all its statements.

    With ``streaming=False`` (default) the whole tree is parsed at once. With
    ``streaming=True`` the entries are read incrementally via
    :func:`camt053.parse.statement_parser.iter_statement_entries`, which bounds
    peak memory to a single entry; the returned list is identical either way.
    Callers that want to consume entries one at a time without materialising the
    full list should use :func:`iter_entries` instead.

    Args:
        xml: The raw statement XML as a string.
        streaming: If ``True``, use the memory-bounded ``iterparse`` path.

    Returns:
        A list of entry dicts.

    Raises:
        StatementParseError: If the XML is malformed or unrecognised.
    """
    if streaming:
        return [e.to_dict() for e in _iter_statement_entries(xml)]
    return [e.to_dict() for e in _parse_document(xml).all_entries()]


def iter_entries(xml: str) -> Iterator[dict[str, Any]]:
    """Stream a statement's entries as dicts without building the whole tree.

    Memory-bounded, forward-only counterpart to :func:`list_entries`: each entry
    dict is produced the moment its ``<Ntry>`` element closes (via
    :func:`camt053.parse.statement_parser.iter_statement_entries`), so large
    statements can be processed without loading the entire document. For a
    well-formed statement it yields exactly the entries :func:`list_entries`
    returns, in document order.

    Args:
        xml: The raw statement XML as a string.

    Yields:
        Each entry as a JSON-serialisable dict, in document order.

    Raises:
        StatementParseError: If the XML is empty or becomes malformed while
            streaming (after any already-parsed entries have been yielded).
    """
    for entry in _iter_statement_entries(xml):
        yield entry.to_dict()


def _parse_amount(value: str | None, label: str) -> Decimal | None:
    """Parse an amount string into a Decimal, or raise a clear ValueError."""
    if value is None:
        return None
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid {label} amount: {value!r}.") from exc


def _entry_amount(entry: Any) -> Decimal | None:
    """Return an entry's amount as a Decimal, or None if absent / unparsable."""
    if not entry.amount:
        return None
    try:
        return Decimal(entry.amount)
    except InvalidOperation:
        return None


def _check_date(value: str | None, label: str) -> str | None:
    """Validate an ISO date filter bound, returning its date portion."""
    if value is None:
        return None
    text = value.strip()
    try:
        date.fromisoformat(text[:10])
    except ValueError as exc:
        raise ValueError(f"Invalid {label} date: {value!r}.") from exc
    return text[:10]


def filter_entries(
    xml: str,
    reason_code: str | None = DEFAULT_REASON_CODE,
    *,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    min_amount: str | None = None,
    max_amount: str | None = None,
) -> list[dict[str, Any]]:
    """Return statement entries matching every supplied filter (ANDed).

    Called as before, ``filter_entries(xml)`` keeps the default-AC04 reason
    behaviour. Passing ``reason_code=None`` (or an empty string) drops the
    reason filter, so the other criteria can be used on their own.

    Args:
        xml: The raw statement XML as a string.
        reason_code: ISO external return reason to match (default ``"AC04"``);
            ``None`` / empty disables the reason filter.
        status: If given, only entries with this status (e.g. ``"BOOK"``).
        date_from: If given, only entries booked on or after this ISO date.
        date_to: If given, only entries booked on or before this ISO date.
        min_amount: If given, only entries with an amount >= this value.
        max_amount: If given, only entries with an amount <= this value.

    Returns:
        A list of matching entry dicts.

    Raises:
        StatementParseError: If the XML is malformed or unrecognised.
        ValueError: If a date or amount filter value is invalid.
    """
    document = _parse_document(xml)
    wanted = reason_code.upper() if reason_code else None
    wanted_status = status.upper() if status else None
    low = _parse_amount(min_amount, "minimum")
    high = _parse_amount(max_amount, "maximum")
    after = _check_date(date_from, "from")
    before = _check_date(date_to, "to")

    def matches(entry: Any) -> bool:
        """Return True if the entry satisfies every active filter."""
        if wanted is not None:
            codes = {entry.reason_code} | {
                d.reason_code for d in entry.details
            }
            if not any((c or "").upper() == wanted for c in codes):
                return False
        if wanted_status is not None:
            if (entry.status or "").upper() != wanted_status:
                return False
        if after is not None or before is not None:
            booked = (entry.booking_date or "")[:10]
            if not booked:
                return False
            if after is not None and booked < after:
                return False
            if before is not None and booked > before:
                return False
        if low is not None or high is not None:
            amount = _entry_amount(entry)
            if amount is None:
                return False
            if low is not None and amount < low:
                return False
            if high is not None and amount > high:
                return False
        return True

    return [e.to_dict() for e in document.all_entries() if matches(e)]


def build_reversal(
    xml: str, reason_code: str = DEFAULT_REASON_CODE
) -> list[dict[str, Any]]:
    """Build the flat reversing-entry records for a statement's matches.

    Parses the statement, selects every statement's entries with the given
    return reason, and maps them to flat records (without rendering XML).

    Args:
        xml: The raw statement XML as a string.
        reason_code: The ISO external return reason to reverse (default
            ``"AC04"``).

    Returns:
        A list of flat reversing-entry records.

    Raises:
        StatementParseError: If the XML cannot be parsed.
        ReversalGenerationError: If no entry matches the reason code.
    """
    document = _parse_document(xml)
    if not document.statements:
        from camt053.exceptions import StatementParseError

        raise StatementParseError("Document contains no statement element")
    return build_reversal_records_for_statements(
        document.statements, reason_code=reason_code
    )


def cleanse_records(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Cleanse the SWIFT-constrained fields of reversing-entry records.

    Transliterates or strips characters outside the SWIFT X charset and
    enforces the maximum length of every name / narrative field (``Nm`` /
    ``AddtlInf`` / party / counterparty names), mutating the records in place
    so they are safe to render onto SWIFT FIN / CBPR+ rails.

    Args:
        records: The flat reversing-entry records to cleanse in place.

    Returns:
        ``{"changed": int, "fields": [report, ...]}`` where each report is a
        :meth:`~camt053.compliance.swift_charset.FieldCleansing.to_dict` of a
        field whose value was altered (unchanged fields are omitted).
    """
    reports = _cleanse_records(records)
    return {
        "changed": len(reports),
        "fields": [report.to_dict() for report in reports],
    }


def _read_path(path: str) -> str:
    """Read a statement file's text, raising OSError on failure."""
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _resolve_batch_paths(paths: list[str] | str) -> list[str]:
    """Expand directories / globs / file lists into an ordered file list.

    Each input is resolved independently: a directory contributes its sorted
    recursive ``*.xml`` files, a glob contributes its sorted matches, and any
    other value is kept as-is (so a missing path surfaces as a per-file error
    rather than silently vanishing). Duplicates are removed, first-seen order
    preserved.

    Args:
        paths: A single path / glob / directory, or a list mixing them.

    Returns:
        The ordered, de-duplicated list of file paths to process.
    """
    items = [paths] if isinstance(paths, str) else list(paths)
    resolved: list[str] = []
    seen: set[str] = set()
    for item in items:
        if os.path.isdir(item):
            matches = sorted(
                glob.glob(os.path.join(item, "**", "*.xml"), recursive=True)
            )
        else:
            globbed = sorted(glob.glob(item, recursive=True))
            matches = globbed or [item]
        for match in matches:
            if match not in seen:
                seen.add(match)
                resolved.append(match)
    return resolved


def generate_reversal(
    xml: str,
    reason_code: str = DEFAULT_REASON_CODE,
    msg_id: str | None = None,
    creation_date_time: str | None = None,
    cleanse: bool = False,
    output_format: str = OUTPUT_FORMAT_CAMT053,
    version: str | None = None,
) -> str:
    """Read a statement and generate a validated reversing-entry document.

    This is the headline one-shot workflow: parse the incoming camt.053, pick
    the entries with the requested return reason (e.g. AC04 Closed Account),
    and emit a validated reversal document.

    By default the reversal is a camt.053.001.14 reversing-entry statement.
    Callers can select a different bundled camt.053 schema version via
    ``version`` (one of :data:`camt053.constants.REVERSAL_CAMT_VERSIONS`), or
    switch to a pacs.004 PaymentReturn document with
    ``output_format="pacs004"``.

    Args:
        xml: The raw incoming statement XML as a string.
        reason_code: The ISO external return reason to reverse (default
            ``"AC04"``).
        msg_id: Optional reversal group-header message id.
        creation_date_time: Optional ISO 8601 timestamp for the reversal.
        cleanse: Opt-in SWIFT charset cleansing of the reversal's name /
            narrative fields before rendering (default ``False``, leaving the
            existing output byte-for-byte unchanged).
        output_format: ``"camt053"`` (default) emits a camt.053 reversing-entry
            statement; ``"pacs004"`` emits a pacs.004 PaymentReturn document.
        version: For the camt.053 format, the schema version to emit; ``None``
            keeps the default :data:`camt053.constants.REVERSAL_MESSAGE_TYPE`.

    Returns:
        The validated reversal document as a string.

    Raises:
        StatementParseError: If the XML cannot be parsed.
        ReversalGenerationError: If no entry matches, the format / version is
            unknown, or validation fails.
    """
    document = _parse_document(xml)
    if not document.statements:
        from camt053.exceptions import StatementParseError

        raise StatementParseError("Document contains no statement element")
    records = build_reversal_records_for_statements(
        document.statements,
        reason_code=reason_code,
        msg_id=msg_id,
        creation_date_time=creation_date_time,
    )
    if cleanse:
        _cleanse_records(records)
    xml_out = generate_reversal_xml(
        records, output_format=output_format, version=version
    )
    log_event(
        logging.INFO,
        "reversal.generated",
        reason_code=reason_code,
        records=len(records),
    )
    return xml_out


def generate(
    records: list[dict[str, Any]],
    cleanse: bool = False,
    output_format: str = OUTPUT_FORMAT_CAMT053,
    version: str | None = None,
) -> str:
    """Render flat reversing-entry records into a validated reversal document.

    The in-process entry point for callers that already hold reversing-entry
    records (e.g. built elsewhere or loaded from a data file).

    Args:
        records: One or more flat reversing-entry records.
        cleanse: Opt-in SWIFT charset cleansing of the records' name /
            narrative fields before rendering (default ``False``).
        output_format: ``"camt053"`` (default) or ``"pacs004"``.
        version: Optional camt.053 schema version to emit (default keeps
            :data:`camt053.constants.REVERSAL_MESSAGE_TYPE`).

    Returns:
        The validated reversal document as a string.

    Raises:
        ReversalGenerationError: If records are empty, the format / version is
            unknown, or validation fails.
    """
    if cleanse:
        _cleanse_records(records)
    return generate_reversal_xml(
        records, output_format=output_format, version=version
    )


def generate_batch(
    paths: list[str] | str,
    reason_code: str = DEFAULT_REASON_CODE,
    cleanse: bool = False,
    output_format: str = OUTPUT_FORMAT_CAMT053,
    version: str | None = None,
) -> dict[str, Any]:
    """Generate reversals for many statement files in one call.

    Processes a list of file paths, a glob pattern, or a directory (every
    ``*.xml`` file inside it, recursively), reversing each statement
    independently. Each file is isolated: a parse / generation failure on one
    file is captured as an error result and does not abort the batch.

    Args:
        paths: A directory path, a glob pattern, a single file path, or a list
            mixing any of those. Directories are scanned recursively for
            ``*.xml`` files; bare paths that are neither a file, directory, nor
            matching glob are reported as a not-found error.
        reason_code: The ISO external return reason to reverse (default
            ``"AC04"``).
        cleanse: Opt-in SWIFT charset cleansing before rendering.
        output_format: ``"camt053"`` (default) or ``"pacs004"``.
        version: Optional camt.053 schema version to emit.

    Returns:
        ``{"total": int, "succeeded": int, "failed": int,
        "results": [{"path": str, "ok": bool, "xml": str | None,
        "error": str | None}, ...]}``. Results preserve discovery order.
    """
    resolved = _resolve_batch_paths(paths)
    results: list[dict[str, Any]] = []
    succeeded = 0
    for path in resolved:
        try:
            xml = _read_path(path)
            reversal = generate_reversal(
                xml,
                reason_code=reason_code,
                cleanse=cleanse,
                output_format=output_format,
                version=version,
            )
        except (OSError, Camt053Error) as exc:
            results.append(
                {"path": path, "ok": False, "xml": None, "error": str(exc)}
            )
            continue
        succeeded += 1
        results.append(
            {"path": path, "ok": True, "xml": reversal, "error": None}
        )
    return {
        "total": len(resolved),
        "succeeded": succeeded,
        "failed": len(resolved) - succeeded,
        "results": results,
    }


def load_openapi(app: Any | None = None) -> str:
    """Return the REST API OpenAPI document as a JSON string.

    Args:
        app: An optional FastAPI app; defaults to the bundled Camt053 API.

    Returns:
        The OpenAPI schema serialised as JSON.
    """
    if app is None:
        from camt053.api.app import app as default_app

        app = default_app
    return json.dumps(app.openapi())


def guard_xml(xml: str, max_bytes: int = DEFAULT_MAX_XML_BYTES) -> None:
    """Reject an untrusted XML payload that breaches a security limit.

    A thin facade over :func:`camt053.security.xml_guard.guard_xml_payload`,
    enforcing a maximum byte size and refusing inline DTD / entity
    declarations before the payload reaches the parser.

    Args:
        xml: The raw XML payload as a string.
        max_bytes: The maximum accepted UTF-8 size in bytes.

    Raises:
        XmlSecurityError: If the payload is too large or carries a DOCTYPE /
            ENTITY declaration.
    """
    guard_xml_payload(xml, max_bytes=max_bytes)
