"""The Python camt053 module."""

__version__ = "0.0.1"

from camt053.exceptions import (
    ReversalGenerationError,
    StatementParseError,
)
from camt053.models import Entry, ParsedDocument, Statement
from camt053.parse.statement_parser import parse_document, parse_statement
from camt053.xml.generate_xml import (
    generate_reversal_for_statement,
    generate_reversal_xml,
)
from camt053.xml.serialize_statement import (
    serialize_document,
    serialize_statement,
)

__all__ = [
    "parse_document",
    "parse_statement",
    "serialize_document",
    "serialize_statement",
    "generate_reversal_xml",
    "generate_reversal_for_statement",
    "Entry",
    "Statement",
    "ParsedDocument",
    "StatementParseError",
    "ReversalGenerationError",
    "__version__",
]
