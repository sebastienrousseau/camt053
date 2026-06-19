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

Resilient recovery
------------------
Real-world statements are frequently malformed-but-recoverable, so the parser
degrades gracefully rather than failing on every imperfection:

* **Missing optional elements** (owner name, currency, balances, booking date,
  return reason, ...) are read as ``None`` / empty, never an error. Only the
  document envelope (a ``<Document>`` root wrapping a recognised message
  container) is mandatory.
* **Unknown or extra elements** are ignored: children are matched by local
  name, so vendor extensions and unexpected siblings are skipped silently.
* **Unexpected namespaces and prefixes** are tolerated: every tag is reduced
  to its local name, so a prefixed root (``<camt:Document>``), a missing
  namespace, or a non-ISO namespace URI all parse the same way.

These limits are **deliberate**. The following are *not* recoverable and raise
:class:`~camt053.exceptions.StatementParseError` with precise context:

* Non-well-formed XML (unclosed / mismatched tags, bad entities) — the error
  carries the 1-based source ``line`` (and column, where the parser reports
  one) so the offending byte can be located.
* Empty input, a non-``<Document>`` root, a ``<Document>`` with no container
  child, or a container whose local name is not a recognised camt.05x message.

Streaming vs. whole-tree parsing
--------------------------------
:func:`parse_document` builds the **whole** statement tree in memory and returns
a fully populated :class:`~camt053.models.ParsedDocument`. That is convenient
(random access to every statement, balance, and entry; round-trip
re-serialisation) but its peak memory grows with the size of the file, so a
statement carrying hundreds of thousands of entries can be costly.

:func:`iter_statement_entries` is an incremental, **memory-bounded** alternative
built on :func:`defusedxml.ElementTree.iterparse`. It yields each
:class:`~camt053.models.Entry` as soon as its ``<Ntry>`` subtree closes and then
*clears* that subtree (and its already-consumed siblings), so peak memory is
bounded by the size of a single entry rather than the whole document. The
trade-offs are:

* It exposes **only entries**, not the group header / account / balances, and
  offers no random access — it is a forward-only iterator.
* It still parses with :mod:`defusedxml` (DTDs and external/general entities
  rejected), so it keeps the same XXE / billion-laughs protection.
* On a syntax error mid-stream it raises the same
  :class:`~camt053.exceptions.StatementParseError` as the whole-tree path,
  after yielding the entries seen before the error.

For the same well-formed input it yields exactly the entries
:meth:`~camt053.models.ParsedDocument.all_entries` would return, in document
order.

Example:
    >>> from camt053.parse.statement_parser import parse_document
    >>> doc = parse_document(xml_string)           # doctest: +SKIP
    >>> [e.reason_code for e in doc.all_entries()]  # doctest: +SKIP
    ['AC04']
    >>> from camt053.parse.statement_parser import iter_statement_entries
    >>> for entry in iter_statement_entries(xml_string):  # doctest: +SKIP
    ...     print(entry.reference)
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from io import StringIO
from xml.etree.ElementTree import Element  # nosec B405

from defusedxml.ElementTree import ParseError
from defusedxml.ElementTree import iterparse as defused_iterparse
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

__all__ = [
    "parse_document",
    "parse_statement",
    "iter_statement_entries",
]

# Map every container's local name back to its message type.
_CONTAINER_TO_TYPE = {v: k for k, v in STATEMENT_CONTAINERS.items()}


_VERSION_RE = re.compile(r"(camt\.0\d{2}\.001\.\d{2})")

# defusedxml re-raises the stdlib expat error, whose message ends with a
# ``: line L, column C`` suffix. We surface the line on the raised
# StatementParseError and fold the column into the message for precision.
_LINE_RE = re.compile(r"line (\d+)")
_COLUMN_RE = re.compile(r"column (\d+)")


def _malformed_error(exc: ParseError) -> StatementParseError:
    """Build a precise :class:`StatementParseError` for non-well-formed XML.

    Extracts the 1-based source line (and, when expat reports one, the column)
    from the underlying parse error so callers can locate the offending byte.
    A parser that omits position information still yields a clear error with
    ``line=None`` rather than crashing.
    """
    text = str(exc)
    line_match = _LINE_RE.search(text)
    col_match = _COLUMN_RE.search(text)
    line = int(line_match.group(1)) if line_match else None
    if line is None:
        where = "an unknown position"
    elif col_match:
        where = f"line {line}, column {col_match.group(1)}"
    else:
        where = f"line {line}"
    return StatementParseError(
        f"Malformed statement XML at {where}: {exc}", line=line
    )


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
        raise _malformed_error(exc) from exc

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


def iter_statement_entries(xml: str) -> Iterator[Entry]:
    """Stream a statement's entries without building the whole tree.

    Incremental, memory-bounded counterpart to :func:`parse_document`. Uses
    :func:`defusedxml.ElementTree.iterparse` to walk the document, yielding each
    :class:`~camt053.models.Entry` the moment its ``<Ntry>`` element closes and
    then clearing that subtree, so peak memory stays bounded by a single entry
    rather than the entire file. For a well-formed document it yields exactly
    the entries :meth:`~camt053.models.ParsedDocument.all_entries` returns, in
    document order. See the module docstring for the streaming trade-offs.

    Args:
        xml: The raw statement XML as a string.

    Yields:
        Each :class:`~camt053.models.Entry`, in document order.

    Raises:
        StatementParseError: If the XML is empty or becomes malformed while
            streaming (after any already-parsed entries have been yielded).
    """
    if not xml or not xml.strip():
        raise StatementParseError("Statement XML is empty")
    # forbid_dtd/entities default to the XXE-safe behaviour of defusedxml.
    context = defused_iterparse(StringIO(xml), events=("end",))
    try:
        for _event, elem in context:
            if _local(elem.tag) == "Ntry":
                yield _parse_entry(elem)
                # Release the consumed entry subtree to bound memory.
                elem.clear()
    except ParseError as exc:
        raise _malformed_error(exc) from exc
