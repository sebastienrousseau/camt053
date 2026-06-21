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

"""Build reversing entries from parsed statement entries.

Given a parsed :class:`~camt053.models.Statement` and a target return reason
code (e.g. ``AC04`` Closed Account), this module produces the flat records that
drive the camt.053 reversal template. A reversing entry mirrors the original
booked entry with its credit/debit indicator flipped, ``RvslInd`` set, and the
return reason carried in ``RtrInf``.

The rendering of those records into validated XML lives in
:mod:`camt053.xml.generate_xml`; this module is responsible only for the
business mapping, so it stays pure and trivially testable.

Example:
    >>> from camt053.parse import parse_statement
    >>> from camt053.reversal.reversal import build_reversal_records
    >>> stmt = parse_statement(xml)                       # doctest: +SKIP
    >>> records = build_reversal_records(stmt, "AC04")    # doctest: +SKIP
    >>> records[0]["credit_debit"]                        # doctest: +SKIP
    'DBIT'
"""

from __future__ import annotations

import hashlib
from typing import Any

from camt053.constants import reverse_credit_debit
from camt053.exceptions import ReversalGenerationError
from camt053.models import Entry, Statement
from camt053.parse.reason_codes import describe_reason

__all__ = [
    "build_reversal_record",
    "build_reversal_records",
    "build_reversal_records_for_statements",
    "stable_reversal_reference",
]


# Maximum length of an ISO 20022 ID (the EntryReference field
# ``Max35Text``). Truncating below this bound is an XSD violation;
# above is wasted space.
_REVERSAL_ID_MAX_LENGTH = 35

# Constant suffix folded into the sha256 input so the same original
# reference produces a *reversal-specific* digest. Documented as
# load-bearing for byte-identical output across releases.
_REVERSAL_HASH_SALT = "REV"


def stable_reversal_reference(
    original_reference: str,
    *,
    max_length: int = _REVERSAL_ID_MAX_LENGTH,
) -> str:
    """Return a stable, idempotent reversal reference for an original entry.

    Deterministic: the same input always produces byte-identical output.
    The default scheme is a human-readable ``RVSL-{original}`` prefix
    (preserved across releases for navigability in audit logs); when the
    prefixed form would exceed ``max_length`` it falls back to a
    ``RVSL-{sha256(original|REV)}`` truncated digest, ensuring
    collision-resistant IDs even for very long or adversarial originals.

    Either way the contract is: same input → identical output, bit for
    bit. Pinned by the property tests; do not change the prefix or the
    salt without bumping the major version.

    Args:
        original_reference: The original booked entry's reference (e.g.
            ``NTRY-0001``). An empty string is permitted and yields the
            bare ``"RVSL-"`` prefix.
        max_length: ISO 20022 ID maximum length. Defaults to 35.

    Returns:
        The reversal reference, never longer than ``max_length``.
    """
    candidate = f"RVSL-{original_reference}"
    if len(candidate) <= max_length:
        return candidate
    digest = hashlib.sha256(
        f"{original_reference}|{_REVERSAL_HASH_SALT}".encode()
    ).hexdigest()
    return f"RVSL-{digest}"[:max_length]


def _entry_reason(entry: Entry) -> str | None:
    """Return the first return reason code carried by an entry."""
    if entry.reason_code:
        return entry.reason_code
    return next((d.reason_code for d in entry.details if d.reason_code), None)


def _select_entries(
    statement: Statement, reason_code: str | None
) -> list[Entry]:
    """Return the booked entries of a statement selected for reversal.

    If ``reason_code`` is given, only entries carrying that return reason are
    selected; otherwise every entry carrying any return reason is.
    """
    if reason_code:
        return statement.entries_with_reason(reason_code)
    return [e for e in statement.entries if e.is_returnable()]


def _no_match_error(reason_code: str | None) -> ReversalGenerationError:
    """Build the "nothing to reverse" error for a selection criteria."""
    target = (
        f"return reason {reason_code.upper()}"
        if reason_code
        else "any return reason"
    )
    return ReversalGenerationError(
        f"No statement entries match {target}; nothing to reverse."
    )


def build_reversal_record(
    entry: Entry,
    statement: Statement,
    msg_id: str,
    creation_date_time: str,
    statement_id: str,
) -> dict[str, Any]:
    """Build a single flat reversing-entry record from a booked entry.

    Args:
        entry: The original booked entry being reversed.
        statement: The statement the entry belongs to (for account context).
        msg_id: Group-header message identification for the reversal.
        creation_date_time: ISO 8601 creation timestamp for the reversal.
        statement_id: Statement identification for the reversal.

    Returns:
        A flat record dict matching the camt.053 reversal template vocabulary.
    """
    detail = entry.details[0] if entry.details else None
    reason = _entry_reason(entry)
    account = statement.account
    reversed_ind = reverse_credit_debit(entry.credit_debit_indicator or "CRDT")
    # The camt.053 schema requires at least one balance; carry the source
    # statement's first balance, or synthesise a closing booked balance.
    source_balance = statement.balances[0] if statement.balances else None
    bal_currency = (
        (source_balance.currency if source_balance else None)
        or account.currency
        or entry.currency
        or "EUR"
    )
    bal_date = (
        (source_balance.date if source_balance else None)
        or entry.booking_date
        or creation_date_time
        or "1970-01-01"
    )[:10]
    return {
        "statement_msg_id": msg_id,
        "creation_date_time": creation_date_time,
        "statement_id": statement_id,
        "electronic_seq_nb": statement.electronic_seq_nb or "",
        "bal_type_code": (source_balance.type_code if source_balance else None)
        or "CLBD",
        "bal_amount": (source_balance.amount if source_balance else None)
        or "0.00",
        "bal_currency": bal_currency,
        "bal_credit_debit": (
            source_balance.credit_debit_indicator if source_balance else None
        )
        or "CRDT",
        "bal_date": bal_date,
        "account_id": account.iban or "",
        "account_id_other": account.other_id or "",
        "account_currency": account.currency or entry.currency or "",
        "account_owner_name": account.owner_name or "",
        "account_servicer_bic": account.servicer_bic or "",
        "entry_ref": (
            stable_reversal_reference(entry.reference)
            if entry.reference
            else ""
        ),
        "original_ref": (entry.reference or "")[:35],
        "amount": entry.amount or "",
        "currency": entry.currency or account.currency or "",
        "credit_debit": reversed_ind,
        "reversal_indicator": "true",
        "status": "BOOK",
        "booking_date": entry.booking_date or "",
        "value_date": entry.value_date or "",
        "end_to_end_id": detail.end_to_end_id if detail else "",
        "tx_id": detail.tx_id if detail else "",
        "reason_code": reason or "",
        "reason_name": describe_reason(reason) if reason else "",
        "additional_info": (
            (
                f"Reversal of {entry.reference or 'entry'}: "
                f"{describe_reason(reason)}"
                if reason
                else f"Reversal of {entry.reference or 'entry'}"
            )[:105]
        ),
        "counterparty_name": detail.counterparty_name if detail else "",
        "counterparty_account": detail.counterparty_account if detail else "",
    }


def build_reversal_records(
    statement: Statement,
    reason_code: str | None = None,
    msg_id: str | None = None,
    creation_date_time: str | None = None,
) -> list[dict[str, Any]]:
    """Build flat reversing-entry records for a statement.

    Selects the booked entries to reverse, then maps each to a flat record.

    Args:
        statement: The parsed statement to reverse entries from.
        reason_code: If given, only entries carrying this return reason are
            reversed; otherwise every entry that carries any return reason is.
        msg_id: Group-header message id for the reversal (defaults to a value
            derived from the statement id).
        creation_date_time: ISO 8601 timestamp for the reversal (defaults to
            the statement's own creation time).

    Returns:
        A list of flat reversing-entry records, one per reversed entry.

    Raises:
        ReversalGenerationError: If no entry matches the selection criteria.
    """
    entries = _select_entries(statement, reason_code)
    if not entries:
        raise _no_match_error(reason_code)

    base_id = statement.id or "STMT"
    resolved_msg_id = (msg_id or f"RVSL-{base_id}")[:35]
    resolved_dt = creation_date_time or statement.creation_date_time or ""
    resolved_stmt_id = f"RVSL-{base_id}"[:35]

    return [
        build_reversal_record(
            entry,
            statement,
            resolved_msg_id,
            resolved_dt,
            resolved_stmt_id,
        )
        for entry in entries
    ]


def build_reversal_records_for_statements(
    statements: list[Statement],
    reason_code: str | None = None,
    msg_id: str | None = None,
    creation_date_time: str | None = None,
) -> list[dict[str, Any]]:
    """Build flat reversing-entry records across every statement.

    Scans all statements in a document, reverses the matching entries in
    each, and aggregates the records into a single reversal. The statement
    header context (message / statement id, balances, account) is taken from
    the first statement that carries a match, so a match in a later statement
    is no longer missed.

    Args:
        statements: The parsed statements to reverse entries from.
        reason_code: If given, only entries carrying this return reason are
            reversed; otherwise every entry that carries any return reason is.
        msg_id: Group-header message id for the reversal (defaults to a value
            derived from the matching statement's id).
        creation_date_time: ISO 8601 timestamp for the reversal (defaults to
            the matching statement's own creation time).

    Returns:
        A list of flat reversing-entry records, one per reversed entry.

    Raises:
        ReversalGenerationError: If no statement has any matching entry.
    """
    matches = [
        (statement, entries)
        for statement in statements
        if (entries := _select_entries(statement, reason_code))
    ]
    if not matches:
        raise _no_match_error(reason_code)

    header_statement = matches[0][0]
    base_id = header_statement.id or "STMT"
    resolved_msg_id = (msg_id or f"RVSL-{base_id}")[:35]
    resolved_dt = (
        creation_date_time or header_statement.creation_date_time or ""
    )
    resolved_stmt_id = f"RVSL-{base_id}"[:35]

    return [
        build_reversal_record(
            entry,
            statement,
            resolved_msg_id,
            resolved_dt,
            resolved_stmt_id,
        )
        for statement, entries in matches
        for entry in entries
    ]
