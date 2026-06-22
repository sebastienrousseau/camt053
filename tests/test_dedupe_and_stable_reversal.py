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

"""Tests for B2 (stable reversal references) and B3 (dedupe keys)."""

from __future__ import annotations

import hashlib

import pytest

from camt053 import services
from camt053.models import ParsedDocument, Statement
from camt053.parse.dedupe import (
    DEDUPE_KEY_SEPARATOR,
    compute_dedupe_key,
    compute_dedupe_keys,
)
from camt053.reversal.reversal import stable_reversal_reference

# ─── B2: stable_reversal_reference ──────────────────────────────────────────


def test_stable_reversal_reference_short_input_uses_readable_prefix():
    """A short original reference yields a human-readable ``RVSL-`` form."""
    assert stable_reversal_reference("NTRY-0001") == "RVSL-NTRY-0001"


def test_stable_reversal_reference_is_deterministic():
    """Calling twice with the same input yields byte-identical output."""
    first = stable_reversal_reference("NTRY-0001")
    second = stable_reversal_reference("NTRY-0001")
    assert first == second
    assert first is not second or True  # equality, not identity


def test_stable_reversal_reference_different_inputs_differ():
    """Different inputs yield distinct outputs."""
    assert stable_reversal_reference("NTRY-0001") != stable_reversal_reference(
        "NTRY-0002"
    )


def test_stable_reversal_reference_empty_input_yields_bare_prefix():
    """An empty original reference yields the bare ``RVSL-`` prefix."""
    assert stable_reversal_reference("") == "RVSL-"


def test_stable_reversal_reference_at_boundary_uses_prefix_form():
    """An input that fits exactly at max_length uses the readable form."""
    # "RVSL-" is 5 chars; the prefixed form caps at max_length=35,
    # so a 30-char original is the largest that fits.
    boundary = "X" * 30
    result = stable_reversal_reference(boundary)
    assert result == f"RVSL-{boundary}"
    assert len(result) == 35


def test_stable_reversal_reference_overflows_to_sha256_digest():
    """A long original reference falls back to the sha256 digest form."""
    long_ref = "X" * 100
    result = stable_reversal_reference(long_ref)
    assert result.startswith("RVSL-")
    assert len(result) == 35
    # The digest portion is reproducible.
    expected_digest = hashlib.sha256(f"{long_ref}|REV".encode()).hexdigest()
    assert result[len("RVSL-") :] == expected_digest[: 35 - len("RVSL-")]


def test_stable_reversal_reference_custom_max_length():
    """``max_length`` can be tightened (e.g. for legacy systems)."""
    result = stable_reversal_reference("NTRY-0001", max_length=10)
    # "RVSL-NTRY-0001" is 14 chars > 10, so falls back to digest.
    assert len(result) == 10
    assert result.startswith("RVSL-")


def test_stable_reversal_reference_re_exported_via_services():
    """``services.stable_reversal_reference`` is the same function."""
    assert services.stable_reversal_reference(
        "NTRY-0001"
    ) == stable_reversal_reference("NTRY-0001")


# ─── B3: compute_dedupe_key + compute_dedupe_keys ──────────────────────────


def _document_with(
    msg_id: str | None,
    stmt_id: str | None,
    seq_nb: str | None,
) -> ParsedDocument:
    """Build a single-statement document with the given dedupe components."""
    return ParsedDocument(
        message_type="camt.053.001.08",
        msg_id=msg_id,
        statements=[Statement(id=stmt_id, electronic_seq_nb=seq_nb)],
    )


def test_compute_dedupe_key_canonical_form():
    """Three present components join with colons in the canonical order."""
    doc = _document_with("MSG-1", "STMT-42", "7")
    assert compute_dedupe_key(doc) == "MSG-1:STMT-42:7"


def test_compute_dedupe_key_missing_components_encode_as_empty():
    """Missing components become empty fields, key shape stays stable."""
    doc = _document_with(None, None, None)
    assert compute_dedupe_key(doc) == "::"


def test_compute_dedupe_key_partial_components():
    """Partial components still produce a parseable, length-3 key."""
    doc = _document_with("MSG-1", None, "7")
    assert compute_dedupe_key(doc) == "MSG-1::7"


def test_compute_dedupe_key_separator_is_colon():
    """The separator is a colon (invalid in ISO 20022 IDs)."""
    assert DEDUPE_KEY_SEPARATOR == ":"


def test_compute_dedupe_key_zero_statements_raises():
    """A document with zero statements cannot be dedupe-keyed."""
    doc = ParsedDocument(message_type="camt.053.001.08", msg_id="M")
    with pytest.raises(ValueError, match="zero statements"):
        compute_dedupe_key(doc)


def test_compute_dedupe_keys_returns_one_per_statement():
    """Multi-statement documents yield one key per statement, in order."""
    doc = ParsedDocument(
        message_type="camt.053.001.08",
        msg_id="MSG-1",
        statements=[
            Statement(id="STMT-A", electronic_seq_nb="1"),
            Statement(id="STMT-B", electronic_seq_nb="2"),
            Statement(id="STMT-C", electronic_seq_nb="3"),
        ],
    )
    assert compute_dedupe_keys(doc) == [
        "MSG-1:STMT-A:1",
        "MSG-1:STMT-B:2",
        "MSG-1:STMT-C:3",
    ]


def test_compute_dedupe_keys_empty_document_yields_empty_list():
    """A zero-statement document yields an empty list (not an error)."""
    doc = ParsedDocument(message_type="camt.053.001.08", msg_id="M")
    assert compute_dedupe_keys(doc) == []


def test_compute_dedupe_keys_first_matches_compute_dedupe_key():
    """The first key in the multi-list matches the single-key helper."""
    doc = _document_with("MSG-1", "STMT-A", "1")
    assert compute_dedupe_keys(doc)[0] == compute_dedupe_key(doc)


# ─── B3: services.compute_dedupe_key{,s}(xml) — public XML-string API ──────

_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08">'
    "<BkToCstmrStmt>"
    "<GrpHdr><MsgId>SVC-MSG-1</MsgId>"
    "<CreDtTm>2026-06-21T10:00:00</CreDtTm></GrpHdr>"
    "<Stmt><Id>SVC-STMT-1</Id>"
    "<ElctrncSeqNb>9</ElctrncSeqNb>"
    "<Acct><Id><IBAN>DE89370400440532013000</IBAN></Id></Acct>"
    "</Stmt>"
    "</BkToCstmrStmt></Document>"
)


def test_services_compute_dedupe_key_accepts_xml_string():
    """The services wrapper accepts an XML string and parses it first."""
    assert services.compute_dedupe_key(_XML) == "SVC-MSG-1:SVC-STMT-1:9"


def test_services_compute_dedupe_keys_accepts_xml_string():
    """The multi-key wrapper also accepts an XML string."""
    assert services.compute_dedupe_keys(_XML) == ["SVC-MSG-1:SVC-STMT-1:9"]
