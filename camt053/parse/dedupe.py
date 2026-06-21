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

"""Exactly-once dedupe keys for camt.05x statements.

Banks routinely re-deliver the same statement (overnight retries, recovery
after a failed batch, gateway hiccups). Without a stable dedupe key,
downstream consumers may post the same entries twice. This module exposes
a small, deterministic helper that computes the canonical dedupe key
from a parsed statement.

The key is the colon-joined tuple ``(GrpHdr/MsgId, Stmt/Id,
Stmt/ElctrncSeqNb)``. Missing components are encoded as the empty string
so the key shape is stable, but a key with missing components has weaker
collision guarantees and SHOULD be combined with an upstream check.
"""

from __future__ import annotations

from camt053.models import ParsedDocument

__all__ = [
    "DEDUPE_KEY_SEPARATOR",
    "compute_dedupe_key",
    "compute_dedupe_keys",
]


#: The character that joins MsgId / StmtId / ElctrncSeqNb in the
#: canonical dedupe key. Colon is chosen because it is invalid in
#: ISO 20022 ID fields, so the key can be split unambiguously back into
#: its three components.
DEDUPE_KEY_SEPARATOR = ":"


def compute_dedupe_key(document: ParsedDocument) -> str:
    """Return the canonical dedupe key for the document's first statement.

    The dedupe key uniquely identifies a statement instance per the ISO
    20022 conventions: two payloads that share a key represent the same
    statement (typically a bank replay).

    Args:
        document: A :class:`~camt053.models.ParsedDocument` (the return
            shape of
            :func:`camt053.parse.statement_parser.parse_document`).

    Returns:
        The colon-joined ``"{MsgId}:{StmtId}:{ElctrncSeqNb}"`` string.
        Missing components are encoded as the empty string.

    Raises:
        ValueError: If the document carries zero statements (the dedupe
            key only makes sense at the statement level).
    """
    if not document.statements:
        raise ValueError(
            "Cannot compute dedupe key: document carries zero statements."
        )
    statement = document.statements[0]
    return DEDUPE_KEY_SEPARATOR.join(
        [
            document.msg_id or "",
            statement.id or "",
            statement.electronic_seq_nb or "",
        ]
    )


def compute_dedupe_keys(document: ParsedDocument) -> list[str]:
    """Return one dedupe key per statement in the document, in order.

    Useful for documents that bundle multiple statements (e.g. a daily
    multi-account report); the first key is identical to the value
    returned by :func:`compute_dedupe_key`.

    Args:
        document: A :class:`~camt053.models.ParsedDocument`.

    Returns:
        A list with one key per statement, in document order. Empty
        when the document carries zero statements.
    """
    return [
        DEDUPE_KEY_SEPARATOR.join(
            [
                document.msg_id or "",
                statement.id or "",
                statement.electronic_seq_nb or "",
            ]
        )
        for statement in document.statements
    ]
