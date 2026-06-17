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

import json
from typing import Any

from camt053.constants import message_names, valid_xml_types
from camt053.parse.reason_codes import list_reason_codes
from camt053.parse.statement_parser import parse_document as _parse_document
from camt053.reversal.reversal import build_reversal_records
from camt053.validation.bic_validator import validate_bic_safe
from camt053.validation.iban_validator import validate_iban_safe
from camt053.validation.lei_validator import validate_lei_safe
from camt053.validation.schema_validator import SchemaValidator
from camt053.xml.generate_xml import (
    generate_reversal_for_statement,
    generate_reversal_xml,
)

__all__ = [
    "list_message_types",
    "list_return_reasons",
    "get_input_schema",
    "get_required_fields",
    "validate_records",
    "validate_identifier",
    "parse_statement",
    "list_entries",
    "filter_entries",
    "build_reversal",
    "generate_reversal",
    "generate",
]

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


def list_entries(xml: str) -> list[dict[str, Any]]:
    """Parse a statement and return every entry across all its statements.

    Args:
        xml: The raw statement XML as a string.

    Returns:
        A list of entry dicts.

    Raises:
        StatementParseError: If the XML is malformed or unrecognised.
    """
    return [e.to_dict() for e in _parse_document(xml).all_entries()]


def filter_entries(
    xml: str, reason_code: str = DEFAULT_REASON_CODE
) -> list[dict[str, Any]]:
    """Return the statement entries carrying a given return reason code.

    Args:
        xml: The raw statement XML as a string.
        reason_code: The ISO external return reason to match (default
            ``"AC04"`` Closed Account).

    Returns:
        A list of matching entry dicts.

    Raises:
        StatementParseError: If the XML is malformed or unrecognised.
    """
    document = _parse_document(xml)
    wanted = reason_code.upper()

    def matches(entry: Any) -> bool:
        codes = {entry.reason_code} | {d.reason_code for d in entry.details}
        return any((c or "").upper() == wanted for c in codes)

    return [e.to_dict() for e in document.all_entries() if matches(e)]


def build_reversal(
    xml: str, reason_code: str = DEFAULT_REASON_CODE
) -> list[dict[str, Any]]:
    """Build the flat reversing-entry records for a statement's matches.

    Parses the statement, selects the first statement's entries with the given
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
    return build_reversal_records(
        document.statements[0], reason_code=reason_code
    )


def generate_reversal(
    xml: str,
    reason_code: str = DEFAULT_REASON_CODE,
    msg_id: str | None = None,
    creation_date_time: str | None = None,
) -> str:
    """Read a statement and generate a validated reversing-entry document.

    This is the headline one-shot workflow: parse the incoming camt.053, pick
    the entries with the requested return reason (e.g. AC04 Closed Account),
    and emit a validated camt.053.001.08 reversal statement.

    Args:
        xml: The raw incoming statement XML as a string.
        reason_code: The ISO external return reason to reverse (default
            ``"AC04"``).
        msg_id: Optional reversal group-header message id.
        creation_date_time: Optional ISO 8601 timestamp for the reversal.

    Returns:
        The validated camt.053.001.08 reversal document as a string.

    Raises:
        StatementParseError: If the XML cannot be parsed.
        ReversalGenerationError: If no entry matches or validation fails.
    """
    document = _parse_document(xml)
    if not document.statements:
        from camt053.exceptions import StatementParseError

        raise StatementParseError("Document contains no statement element")
    return generate_reversal_for_statement(
        document.statements[0],
        reason_code=reason_code,
        msg_id=msg_id,
        creation_date_time=creation_date_time,
    )


def generate(records: list[dict[str, Any]]) -> str:
    """Render flat reversing-entry records into validated camt.053 XML.

    The in-process entry point for callers that already hold reversing-entry
    records (e.g. built elsewhere or loaded from a data file).

    Args:
        records: One or more flat reversing-entry records.

    Returns:
        The validated camt.053.001.08 reversal document as a string.

    Raises:
        ReversalGenerationError: If records are empty or validation fails.
    """
    return generate_reversal_xml(records)


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
