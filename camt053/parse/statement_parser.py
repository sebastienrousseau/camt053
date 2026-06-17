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

"""Parser for incoming ISO 20022 cash-management statements.

Reads a camt.053 Bank-to-Customer Statement (or the closely related camt.052
Account Report / camt.054 Debit-Credit Notification) into the typed model in
:mod:`camt053.models`. Parsing is **namespace-agnostic**: real-world statements
arrive in many ISO versions, so elements are matched by local name rather than
by a fixed namespace URI. XML is parsed with :mod:`defusedxml` to neutralise
XXE / billion-laughs attacks on untrusted bank files.

Example:
    >>> from camt053.parse.statement_parser import parse_document
    >>> doc = parse_document(xml_string)           # doctest: +SKIP
    >>> [e.reason_code for e in doc.all_entries()]  # doctest: +SKIP
    ['AC04']
"""

from __future__ import annotations

import re
from io import StringIO
from xml.etree.ElementTree import Element  # nosec B405

from defusedxml.ElementTree import ParseError
from defusedxml.ElementTree import parse as defused_parse

from camt053.constants import (
    STATEMENT_CONTAINERS,
    STATEMENT_ELEMENTS,
    valid_xml_types,
)
from camt053.exceptions import StatementParseError
from camt053.models import (
    Account,
    Balance,
    Entry,
    ParsedDocument,
    Statement,
    TransactionDetails,
)

__all__ = ["parse_document", "parse_statement"]

# Map every container's local name back to its message type.
_CONTAINER_TO_TYPE = {v: k for k, v in STATEMENT_CONTAINERS.items()}


_VERSION_RE = re.compile(r"(camt\.0\d{2}\.001\.\d{2})")


def _local(tag: str) -> str:
    """Strip an XML namespace from a tag, returning the local name."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _namespace(tag: str) -> str:
    """Return the namespace URI of a tag (empty string if unqualified)."""
    return tag[1:].split("}", 1)[0] if tag.startswith("{") else ""


def _find(parent: Element, name: str) -> Element | None:
    """Return the first direct child of ``parent`` with local name ``name``."""
    for child in parent:
        if _local(child.tag) == name:
            return child
    return None


def _find_all(parent: Element, name: str) -> list[Element]:
    """Return all direct children of ``parent`` with local name ``name``."""
    return [child for child in parent if _local(child.tag) == name]


def _text(parent: Element | None, name: str) -> str | None:
    """Return the stripped text of ``parent``'s first ``name`` child."""
    if parent is None:
        return None
    child = _find(parent, name)
    if child is None or child.text is None:
        return None
    text = child.text.strip()
    return text or None


def _deep_text(parent: Element | None, *names: str) -> str | None:
    """Walk a chain of child names and return the leaf's text.

    ``_deep_text(ntry, "Amt")`` reads ``Ntry/Amt``;
    ``_deep_text(stmt, "Acct", "Id", "IBAN")`` reads ``Acct/Id/IBAN``.
    """
    node = parent
    for name in names[:-1]:
        node = _find(node, name) if node is not None else None
    return _text(node, names[-1])


def _message_type_for(container_name: str, namespace: str) -> str:
    """Resolve the message type for a parsed document.

    Prefers the exact ``camt.0xx.001.yy`` version embedded in the document's
    namespace URI (so a camt.053.001.04 statement is reported as such); falls
    back to mapping the container's local name to a supported type.
    """
    match = _VERSION_RE.search(namespace)
    if match:
        return match.group(1)
    return _CONTAINER_TO_TYPE.get(container_name, valid_xml_types[1])


def _parse_account(stmt: Element) -> Account:
    """Build an :class:`Account` from a statement's ``Acct`` element."""
    acct = _find(stmt, "Acct")
    if acct is None:
        return Account()
    acct_id = _find(acct, "Id")
    iban = _text(acct_id, "IBAN") if acct_id is not None else None
    other = None
    if acct_id is not None and iban is None:
        other = _deep_text(acct_id, "Othr", "Id")
    return Account(
        iban=iban,
        other_id=other,
        currency=_text(acct, "Ccy"),
        owner_name=_deep_text(acct, "Ownr", "Nm"),
        servicer_bic=_deep_text(acct, "Svcr", "FinInstnId", "BICFI"),
    )


def _parse_balances(stmt: Element) -> list[Balance]:
    """Build the list of :class:`Balance` objects from ``Bal`` elements."""
    balances: list[Balance] = []
    for bal in _find_all(stmt, "Bal"):
        amt = _find(bal, "Amt")
        balances.append(
            Balance(
                type_code=_deep_text(bal, "Tp", "CdOrPrtry", "Cd"),
                amount=(
                    amt.text.strip() if amt is not None and amt.text else None
                ),
                currency=amt.get("Ccy") if amt is not None else None,
                credit_debit_indicator=_text(bal, "CdtDbtInd"),
                date=_deep_text(bal, "Dt", "Dt")
                or _deep_text(bal, "Dt", "DtTm"),
            )
        )
    return balances


def _parse_transaction_details(ntry: Element) -> list[TransactionDetails]:
    """Build per-transaction details from ``NtryDtls/TxDtls`` elements."""
    details: list[TransactionDetails] = []
    for ntry_dtls in _find_all(ntry, "NtryDtls"):
        for tx in _find_all(ntry_dtls, "TxDtls"):
            refs = _find(tx, "Refs")
            rtr = _find(tx, "RtrInf")
            related = _find(tx, "RltdPties")
            counterparty_name = None
            counterparty_account = None
            if related is not None:
                for party in ("Dbtr", "Cdtr"):
                    # ISO 20022 .001.14 wraps the party in <Pty>; older /
                    # simplified statements place <Nm> directly under the role.
                    name = _deep_text(related, party, "Pty", "Nm") or (
                        _deep_text(related, party, "Nm")
                    )
                    if name:
                        counterparty_name = name
                        break
                for acct in ("DbtrAcct", "CdtrAcct"):
                    iban = _deep_text(related, acct, "Id", "IBAN")
                    if iban:
                        counterparty_account = iban
                        break
            details.append(
                TransactionDetails(
                    end_to_end_id=_text(refs, "EndToEndId"),
                    tx_id=_text(refs, "TxId"),
                    instruction_id=_text(refs, "InstrId"),
                    reason_code=_deep_text(rtr, "Rsn", "Cd"),
                    additional_info=_text(rtr, "AddtlInf"),
                    counterparty_name=counterparty_name,
                    counterparty_account=counterparty_account,
                )
            )
    return details


def _parse_status(ntry: Element) -> str | None:
    """Read an entry status, tolerating both ``<Sts><Cd>`` and ``<Sts>``."""
    sts = _find(ntry, "Sts")
    if sts is None:
        return None
    coded = _text(sts, "Cd")
    if coded:
        return coded
    return sts.text.strip() if sts.text and sts.text.strip() else None


def _parse_entry(ntry: Element) -> Entry:
    """Build an :class:`Entry` from a single ``Ntry`` element."""
    amt = _find(ntry, "Amt")
    details = _parse_transaction_details(ntry)
    reason = next((d.reason_code for d in details if d.reason_code), None)
    rvsl = (_text(ntry, "RvslInd") or "").lower() == "true"
    return Entry(
        reference=_text(ntry, "NtryRef"),
        amount=amt.text.strip() if amt is not None and amt.text else None,
        currency=amt.get("Ccy") if amt is not None else None,
        credit_debit_indicator=_text(ntry, "CdtDbtInd"),
        status=_parse_status(ntry),
        booking_date=_deep_text(ntry, "BookgDt", "Dt")
        or _deep_text(ntry, "BookgDt", "DtTm"),
        value_date=_deep_text(ntry, "ValDt", "Dt")
        or _deep_text(ntry, "ValDt", "DtTm"),
        account_servicer_ref=_text(ntry, "AcctSvcrRef"),
        reversal_indicator=rvsl,
        reason_code=reason,
        details=details,
    )


def _parse_statement(stmt: Element) -> Statement:
    """Build a :class:`Statement` from a ``Stmt`` / ``Rpt`` / ``Ntfctn``."""
    return Statement(
        id=_text(stmt, "Id"),
        electronic_seq_nb=_text(stmt, "ElctrncSeqNb"),
        creation_date_time=_text(stmt, "CreDtTm"),
        account=_parse_account(stmt),
        balances=_parse_balances(stmt),
        entries=[_parse_entry(n) for n in _find_all(stmt, "Ntry")],
    )


def parse_document(xml: str) -> ParsedDocument:
    """Parse a camt.05x statement document into the typed model.

    Args:
        xml: The raw statement XML as a string.

    Returns:
        A :class:`~camt053.models.ParsedDocument`.

    Raises:
        StatementParseError: If the XML is malformed or its root is not a
            recognised camt.052 / camt.053 / camt.054 document.
    """
    if not xml or not xml.strip():
        raise StatementParseError("Statement XML is empty")
    try:
        tree = defused_parse(StringIO(xml))
    except ParseError as exc:
        match = re.search(r"line (\d+)", str(exc))
        line = int(match.group(1)) if match else None
        raise StatementParseError(
            f"Malformed statement XML: {exc}", line=line
        ) from exc

    root = tree.getroot()
    if root is None:  # pragma: no cover - getroot only returns None pre-parse
        raise StatementParseError("Statement XML has no root element")
    if _local(root.tag) != "Document":
        raise StatementParseError(
            f"Expected a <Document> root element, got <{_local(root.tag)}>"
        )

    container = next(iter(root), None)
    if container is None:
        raise StatementParseError("Document has no message container element")

    container_name = _local(container.tag)
    if container_name not in STATEMENT_CONTAINERS.values():
        raise StatementParseError(
            f"Unrecognised cash-management message container: "
            f"<{container_name}>. Expected one of: "
            f"{', '.join(sorted(STATEMENT_CONTAINERS.values()))}."
        )

    grp_hdr = _find(container, "GrpHdr")
    statements = [
        _parse_statement(stmt)
        for stmt in container
        if _local(stmt.tag) in STATEMENT_ELEMENTS
    ]

    return ParsedDocument(
        message_type=_message_type_for(container_name, _namespace(root.tag)),
        msg_id=_text(grp_hdr, "MsgId"),
        creation_date_time=_text(grp_hdr, "CreDtTm"),
        statements=statements,
    )


def parse_statement(xml: str) -> Statement:
    """Parse a document and return its first statement.

    Convenience for the common single-statement case.

    Args:
        xml: The raw statement XML as a string.

    Returns:
        The first :class:`~camt053.models.Statement` in the document.

    Raises:
        StatementParseError: If the XML cannot be parsed or contains no
            statement element.
    """
    document = parse_document(xml)
    if not document.statements:
        raise StatementParseError("Document contains no statement element")
    return document.statements[0]
