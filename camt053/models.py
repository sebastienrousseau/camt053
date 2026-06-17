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

"""Typed data model for ISO 20022 cash-management statements.

These light, dependency-free dataclasses are what
:func:`camt053.parse.statement_parser.parse_document` returns and what the
reversal builder consumes. Every model exposes :meth:`to_dict` so that the
service facade (and the CLI, REST API, MCP, and LSP layers built on it) can
return plain JSON-serialisable data.

Example:
    >>> from camt053.models import Entry
    >>> e = Entry(reference="NTRY-1", amount="100.00", currency="EUR",
    ...           credit_debit_indicator="CRDT", reason_code="AC04")
    >>> e.is_returnable()
    True
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "Account",
    "Balance",
    "TransactionDetails",
    "Entry",
    "Statement",
    "ParsedDocument",
]


@dataclass
class Account:
    """The account a statement or report relates to."""

    iban: str | None = None
    other_id: str | None = None
    currency: str | None = None
    owner_name: str | None = None
    servicer_bic: str | None = None

    def identifier(self) -> str | None:
        """Return the IBAN if present, else the proprietary identifier."""
        return self.iban or self.other_id

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "iban": self.iban,
            "other_id": self.other_id,
            "currency": self.currency,
            "owner_name": self.owner_name,
            "servicer_bic": self.servicer_bic,
        }


@dataclass
class Balance:
    """A single balance reported on the statement."""

    type_code: str | None = None
    amount: str | None = None
    currency: str | None = None
    credit_debit_indicator: str | None = None
    date: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "type_code": self.type_code,
            "amount": self.amount,
            "currency": self.currency,
            "credit_debit_indicator": self.credit_debit_indicator,
            "date": self.date,
        }


@dataclass
class TransactionDetails:
    """Per-transaction detail carried inside a statement entry."""

    end_to_end_id: str | None = None
    tx_id: str | None = None
    instruction_id: str | None = None
    reason_code: str | None = None
    additional_info: str | None = None
    counterparty_name: str | None = None
    counterparty_account: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "end_to_end_id": self.end_to_end_id,
            "tx_id": self.tx_id,
            "instruction_id": self.instruction_id,
            "reason_code": self.reason_code,
            "additional_info": self.additional_info,
            "counterparty_name": self.counterparty_name,
            "counterparty_account": self.counterparty_account,
        }


@dataclass
class Entry:
    """A booked entry (``Ntry``) on a statement.

    ``reason_code`` is a convenience: it surfaces the first return reason found
    among the entry's transaction details, so callers can filter entries
    without descending into :attr:`details`.
    """

    reference: str | None = None
    amount: str | None = None
    currency: str | None = None
    credit_debit_indicator: str | None = None
    status: str | None = None
    booking_date: str | None = None
    value_date: str | None = None
    account_servicer_ref: str | None = None
    reversal_indicator: bool = False
    reason_code: str | None = None
    details: list[TransactionDetails] = field(default_factory=list)

    def is_returnable(self) -> bool:
        """Return ``True`` if this entry carries any return reason code."""
        if self.reason_code:
            return True
        return any(d.reason_code for d in self.details)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "reference": self.reference,
            "amount": self.amount,
            "currency": self.currency,
            "credit_debit_indicator": self.credit_debit_indicator,
            "status": self.status,
            "booking_date": self.booking_date,
            "value_date": self.value_date,
            "account_servicer_ref": self.account_servicer_ref,
            "reversal_indicator": self.reversal_indicator,
            "reason_code": self.reason_code,
            "details": [d.to_dict() for d in self.details],
        }


@dataclass
class Statement:
    """A single statement / report / notification within a document."""

    id: str | None = None
    electronic_seq_nb: str | None = None
    creation_date_time: str | None = None
    account: Account = field(default_factory=Account)
    balances: list[Balance] = field(default_factory=list)
    entries: list[Entry] = field(default_factory=list)

    def entries_with_reason(self, reason_code: str) -> list[Entry]:
        """Return entries whose return reason matches ``reason_code``.

        The match is case-insensitive and considers both the entry-level
        convenience reason and every transaction detail.

        Args:
            reason_code: An ISO external return reason code (e.g. ``"AC04"``).
        """
        wanted = reason_code.upper()

        def matches(entry: Entry) -> bool:
            codes = {entry.reason_code} | {
                d.reason_code for d in entry.details
            }
            return any((c or "").upper() == wanted for c in codes)

        return [entry for entry in self.entries if matches(entry)]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "id": self.id,
            "electronic_seq_nb": self.electronic_seq_nb,
            "creation_date_time": self.creation_date_time,
            "account": self.account.to_dict(),
            "balances": [b.to_dict() for b in self.balances],
            "entries": [e.to_dict() for e in self.entries],
        }


@dataclass
class ParsedDocument:
    """A parsed camt.05x document: its group header and statements."""

    message_type: str
    msg_id: str | None = None
    creation_date_time: str | None = None
    statements: list[Statement] = field(default_factory=list)

    def all_entries(self) -> list[Entry]:
        """Return every entry across all statements in the document."""
        return [entry for stmt in self.statements for entry in stmt.entries]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "message_type": self.message_type,
            "msg_id": self.msg_id,
            "creation_date_time": self.creation_date_time,
            "statements": [s.to_dict() for s in self.statements],
        }
