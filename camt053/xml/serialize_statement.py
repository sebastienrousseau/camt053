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

"""Re-serialise a parsed statement back to camt.053 XML (round-trip).

Renders a parsed :class:`~camt053.models.ParsedDocument` (or a single
:class:`~camt053.models.Statement`) back into a camt.053.001.14 document via a
Jinja2 template, validated against the bundled ISO 20022 XSD.

The output is **deterministic** (the same parsed model always renders to the
same bytes) and round-trip stable: parsing the serialised XML reproduces the
account, balances, and entries (references, amounts, currencies, credit/debit
indicators, and return reasons) of the source model. Because the camt.053
schema makes ``Amt``, ``CdtDbtInd``, ``Sts``, and ``BkTxCd`` mandatory on every
entry (and at least one ``Bal`` mandatory on every statement), absent optional
values are filled with schema-safe defaults so the document still validates.

Example:
    >>> from camt053.parse import parse_document
    >>> from camt053.xml.serialize_statement import serialize_document
    >>> xml = serialize_document(parse_document(src))        # doctest: +SKIP
    >>> parse_document(xml).all_entries()[0].reason_code      # doctest: +SKIP
    'AC04'
"""

from __future__ import annotations

import os
from typing import Any

from camt053.constants import REVERSAL_MESSAGE_TYPE, TEMPLATES_DIR
from camt053.exceptions import XMLGenerationError
from camt053.models import (
    Balance,
    Entry,
    ParsedDocument,
    Statement,
    TransactionDetails,
)
from camt053.xml.template_env import get_template
from camt053.xml.validate_via_xsd import validate_xml_string_via_xsd

__all__ = ["serialize_document", "serialize_statement"]

# Schema-mandatory fallbacks: the camt.053 XSD makes these elements required,
# so a parsed model missing them is filled with a safe, neutral default rather
# than producing an invalid document.
_DEFAULT_MSG_ID = "CAMT053"
_DEFAULT_CREATION_DATE_TIME = "1970-01-01T00:00:00"
_DEFAULT_STATEMENT_ID = "STMT"
_DEFAULT_AMOUNT = "0"
_DEFAULT_CURRENCY = "EUR"
_DEFAULT_CREDIT_DEBIT = "CRDT"
_DEFAULT_STATUS = "BOOK"
_DEFAULT_BALANCE_TYPE = "CLBD"
_DEFAULT_BALANCE_DATE = "1970-01-01"


def _is_datetime(value: str | None) -> bool:
    """Return ``True`` if a date string carries a time component."""
    return bool(value) and "T" in (value or "")


def _detail_context(detail: TransactionDetails) -> dict[str, Any]:
    """Project a transaction detail onto the template vocabulary."""
    return {
        "instruction_id": detail.instruction_id or "",
        "end_to_end_id": detail.end_to_end_id or "",
        "tx_id": detail.tx_id or "",
        "reason_code": detail.reason_code or "",
        "additional_info": (detail.additional_info or "")[:105],
        "counterparty_name": detail.counterparty_name or "",
        "counterparty_account": detail.counterparty_account or "",
    }


def _entry_context(entry: Entry) -> dict[str, Any]:
    """Project an entry onto the template vocabulary, filling defaults."""
    return {
        "reference": entry.reference or "",
        "amount": entry.amount or _DEFAULT_AMOUNT,
        "currency": entry.currency or _DEFAULT_CURRENCY,
        "credit_debit_indicator": (
            entry.credit_debit_indicator or _DEFAULT_CREDIT_DEBIT
        ),
        "reversal_indicator": entry.reversal_indicator,
        "status": entry.status or _DEFAULT_STATUS,
        "booking_date": entry.booking_date or "",
        "booking_is_datetime": _is_datetime(entry.booking_date),
        "value_date": entry.value_date or "",
        "value_is_datetime": _is_datetime(entry.value_date),
        "account_servicer_ref": entry.account_servicer_ref or "",
        "details": [_detail_context(d) for d in entry.details],
    }


def _balance_context(balance: Balance) -> dict[str, Any]:
    """Project a balance onto the template vocabulary, filling defaults."""
    return {
        "type_code": balance.type_code or _DEFAULT_BALANCE_TYPE,
        "amount": balance.amount or _DEFAULT_AMOUNT,
        "currency": balance.currency or _DEFAULT_CURRENCY,
        "credit_debit_indicator": (
            balance.credit_debit_indicator or _DEFAULT_CREDIT_DEBIT
        ),
        "date": balance.date or _DEFAULT_BALANCE_DATE,
        "is_datetime": _is_datetime(balance.date),
    }


def _synthetic_balance() -> dict[str, Any]:
    """Build a neutral closing balance for a statement that carries none."""
    return _balance_context(Balance())


def _statement_context(statement: Statement) -> dict[str, Any]:
    """Project a statement onto the template vocabulary, filling defaults."""
    account = statement.account
    balances = [_balance_context(b) for b in statement.balances]
    if not balances:
        # The schema requires at least one balance per statement.
        balances = [_synthetic_balance()]
    return {
        "id": statement.id or _DEFAULT_STATEMENT_ID,
        "electronic_seq_nb": statement.electronic_seq_nb or "",
        "creation_date_time": statement.creation_date_time or "",
        "account_id": account.iban or account.other_id or "",
        "account_iban": account.iban or "",
        "account_other_id": account.other_id or "",
        "account_currency": account.currency or "",
        "account_owner_name": account.owner_name or "",
        "account_servicer_bic": account.servicer_bic or "",
        "balances": balances,
        "entries": [_entry_context(e) for e in statement.entries],
    }


def _render_and_validate(document: ParsedDocument) -> str:
    """Render the statement template and validate against the bundled XSD."""
    tdir = TEMPLATES_DIR / REVERSAL_MESSAGE_TYPE
    template_path = str(tdir / "statement.xml")
    xsd_path = str(tdir / f"{REVERSAL_MESSAGE_TYPE}.xsd")

    template = get_template(
        os.path.dirname(template_path), os.path.basename(template_path)
    )
    context = {
        "msg_id": document.msg_id or _DEFAULT_MSG_ID,
        "creation_date_time": (
            document.creation_date_time or _DEFAULT_CREATION_DATE_TIME
        ),
        "statements": [_statement_context(s) for s in document.statements],
    }
    xml_content = template.render(**context)

    if not validate_xml_string_via_xsd(xml_content, xsd_path):
        raise XMLGenerationError(
            f"Serialised statement XML failed validation against {xsd_path}"
        )
    return xml_content


def serialize_document(document: ParsedDocument) -> str:
    """Re-serialise a parsed document back to validated camt.053 XML.

    Args:
        document: A parsed :class:`~camt053.models.ParsedDocument`.

    Returns:
        The validated camt.053.001.14 statement document as a string.

    Raises:
        XMLGenerationError: If the document carries no statement, or the
            rendered XML does not validate against the bundled XSD.
    """
    if not document.statements:
        raise XMLGenerationError(
            "Cannot serialise a document with no statement element"
        )
    return _render_and_validate(document)


def serialize_statement(statement: Statement) -> str:
    """Re-serialise a single parsed statement to validated camt.053 XML.

    Convenience wrapper that wraps ``statement`` in a one-statement document.

    Args:
        statement: A parsed :class:`~camt053.models.Statement`.

    Returns:
        The validated camt.053.001.14 statement document as a string.

    Raises:
        XMLGenerationError: If the rendered XML does not validate.
    """
    document = ParsedDocument(
        message_type=REVERSAL_MESSAGE_TYPE,
        statements=[statement],
    )
    return _render_and_validate(document)
