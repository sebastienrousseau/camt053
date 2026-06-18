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

"""Validate an incoming statement against the official ISO camt XSD.

Detects an incoming document's message type from its parsed namespace (reusing
the version-detection logic in :mod:`camt053.parse.statement_parser`), maps it
to the matching official XSD bundled under ``camt053/xsd/``, and validates the
document with :mod:`xmlschema`. XML is parsed with :mod:`defusedxml` so
untrusted bank files cannot trigger XXE / billion-laughs attacks.
"""

from __future__ import annotations

from io import StringIO
from typing import Any

from defusedxml.ElementTree import ParseError
from defusedxml.ElementTree import parse as defused_parse

from camt053.constants import XSD_DIR
from camt053.exceptions import StatementParseError
from camt053.parse.statement_parser import parse_document
from camt053.xml.validate_via_xsd import _get_cached_schema

__all__ = ["validate_statement"]


def _xsd_path_for(message_type: str) -> str:
    """Return the bundled XSD path for a message type, or raise if absent.

    Args:
        message_type: A detected ISO 20022 message type (e.g.
            ``"camt.053.001.04"``).

    Returns:
        The absolute path to the matching bundled XSD file.

    Raises:
        StatementParseError: If no XSD is bundled for the message type.
    """
    xsd_path = XSD_DIR / f"{message_type}.xsd"
    if not xsd_path.is_file():
        raise StatementParseError(
            f"No bundled XSD for message type {message_type!r}; cannot "
            f"validate this document against an official ISO camt schema."
        )
    return str(xsd_path)


def validate_statement(xml: str) -> dict[str, Any]:
    """Validate an incoming statement against its official ISO camt XSD.

    Args:
        xml: The raw statement XML as a string.

    Returns:
        A report dictionary:
        ``{"valid": bool, "message_type": str, "errors": [str, ...]}``.

    Raises:
        StatementParseError: If the XML is malformed / unrecognised, or no
            official XSD is bundled for the detected message type.
    """
    message_type = parse_document(xml).message_type
    xsd_path = _xsd_path_for(message_type)
    schema = _get_cached_schema(xsd_path)

    try:
        tree = defused_parse(StringIO(xml))
    except ParseError as exc:  # pragma: no cover - parse_document caught it
        raise StatementParseError(f"Malformed statement XML: {exc}") from exc

    errors = [
        error.reason or error.message or str(error)
        for error in schema.iter_errors(tree)
    ]
    return {
        "valid": not errors,
        "message_type": message_type,
        "errors": errors,
    }
