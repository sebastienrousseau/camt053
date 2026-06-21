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

"""Envelope for lenient (partial-batch) statement parsing.

Real-world camt.053 statements occasionally carry corrupt singletons:
one bad ``<Ntry>`` element in a 10,000-entry overnight batch. The strict
:func:`camt053.parse.statement_parser.parse_document` raises on the first
failure (the historic behaviour, preserved); the lenient
:func:`parse_document_lenient` wraps each per-entry parse in a
try/except and returns a :class:`ParseReport` envelope so consumers can
process the surviving entries without abandoning the batch.

The lenient path **never** silently drops data: every skipped entry
appears in :attr:`ParseReport.diagnostics` with a stable code, the
entry's position in the source statement (``stmt_index`` /
``entry_index``), and the originating exception message. Consumers
choose what to do with it; the library only guarantees that they have
the information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from camt053.models import ParsedDocument

__all__ = ["EntryDiagnostic", "ParseReport"]


@dataclass
class EntryDiagnostic:
    """One per-entry failure captured during lenient parsing.

    Attributes:
        stmt_index: Zero-based index of the statement within the document.
        entry_index: Zero-based index of the entry within that statement,
            as encountered in source order (not as it survives in the
            ``ParsedDocument``).
        code: Stable diagnostic code; currently always
            ``"ENTRY_PARSE_FAILED"`` but reserved as a discriminated
            union for future codes.
        message: The originating exception's ``str(exc)`` payload.
    """

    stmt_index: int
    entry_index: int
    code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "stmt_index": self.stmt_index,
            "entry_index": self.entry_index,
            "code": self.code,
            "message": self.message,
        }


@dataclass
class ParseReport:
    """The result of a lenient statement parse.

    Attributes:
        document: The :class:`~camt053.models.ParsedDocument` containing
            every successfully parsed entry. Corrupt entries are absent
            from this view; ``len(document.all_entries())`` therefore
            equals the count of *surviving* entries (not the count seen
            in source order).
        corrupt_entry_count: How many entries were skipped because of a
            parse failure. Identical to ``len(diagnostics)``.
        diagnostics: One :class:`EntryDiagnostic` per skipped entry, in
            source order.
    """

    document: ParsedDocument
    corrupt_entry_count: int = 0
    diagnostics: list[EntryDiagnostic] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "document": self.document.to_dict(),
            "corrupt_entry_count": self.corrupt_entry_count,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }
