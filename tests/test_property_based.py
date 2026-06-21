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

"""Property-based (Hypothesis) tests for parser robustness and reversal
invariants (#25).

These complement the example-based suite by generating a broad space of
plausible and structurally-odd-but-well-formed inputs and asserting the
invariants that must hold for *any* such input:

* The parser never crashes on well-formed XML; it either returns a model or
  raises the library's own :class:`StatementParseError`.
* A reversing entry always flips ``CdtDbtInd``, sets the reversal indicator,
  and preserves the original amount and currency.
* The credit/debit reversal is an involution (applying it twice is identity)
  for the canonical indicators.
* Parsing a serialised statement round-trips the entries that survive
  serialisation.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from camt053.constants import reverse_credit_debit
from camt053.exceptions import StatementParseError
from camt053.models import Account, Entry, Statement, TransactionDetails
from camt053.parse.statement_parser import parse_document, parse_statement
from camt053.reversal.reversal import build_reversal_record
from camt053.xml.serialize_statement import serialize_statement

# ── Reusable strategies ───────────────────────────────────────────────

# ISO 20022 credit/debit indicators.
indicators = st.sampled_from(["CRDT", "DBIT"])

# Return reason codes (a subset is enough to exercise the mapping).
reason_codes = st.sampled_from(
    ["AC04", "AC06", "AC01", "MD07", "AM04", "NARR"]
)

# Amounts that the camt.053 schema accepts: up to 18 total digits with at
# most 5 fractional digits, rendered as a fixed-point decimal string.
amounts = st.decimals(
    min_value=0,
    max_value=10**12,
    places=2,
    allow_nan=False,
    allow_infinity=False,
).map(lambda d: f"{d:.2f}")

# ISO 4217-ish currency codes (three upper-case letters).
currencies = st.text(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=3, max_size=3
)

# Free-text fields that may carry XML-significant characters; kept printable
# and free of control characters so the resulting XML is well-formed.
free_text = st.text(
    alphabet=st.characters(
        min_codepoint=0x20,
        max_codepoint=0x7E,
    ),
    min_size=0,
    max_size=40,
)

# References constrained to the characters that survive a serialise round-trip
# without entity-escaping ambiguity; length deliberately spans the 35-char
# ISO truncation boundary.
references = st.text(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-",
    min_size=1,
    max_size=50,
)


@st.composite
def ibans(draw: st.DrawFn) -> str:
    """Generate values matching the ISO IBAN pattern the XSD enforces:
    two letters, two digits, then 1-30 alphanumerics.
    """
    country = draw(
        st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=2, max_size=2)
    )
    check = draw(st.text(alphabet="0123456789", min_size=2, max_size=2))
    bban = draw(
        st.text(
            alphabet=(
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
            ),
            min_size=1,
            max_size=30,
        )
    )
    return f"{country}{check}{bban}"


@st.composite
def entries(draw: st.DrawFn) -> Entry:
    """Generate a plausible booked :class:`Entry`."""
    has_reason = draw(st.booleans())
    reason = draw(reason_codes) if has_reason else None
    detail = TransactionDetails(
        end_to_end_id=draw(st.none() | references),
        tx_id=draw(st.none() | references),
        reason_code=reason,
        counterparty_name=draw(st.none() | free_text),
        counterparty_account=draw(st.none() | references),
    )
    return Entry(
        reference=draw(references),
        amount=draw(amounts),
        currency=draw(currencies),
        credit_debit_indicator=draw(indicators),
        status="BOOK",
        reason_code=reason,
        details=[detail],
    )


@st.composite
def statements(draw: st.DrawFn) -> Statement:
    """Generate a :class:`Statement` with one or more booked entries."""
    return Statement(
        id=draw(references),
        creation_date_time="2026-06-15T08:00:00",
        account=Account(
            iban=draw(st.none() | references),
            currency=draw(currencies),
            owner_name=draw(st.none() | free_text),
        ),
        entries=draw(st.lists(entries(), min_size=1, max_size=5)),
    )


# Identifiers the XSD caps at 35 characters (Max35Text), used where a value is
# serialised verbatim and must satisfy the schema length facet.
bounded_references = st.text(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-",
    min_size=1,
    max_size=35,
)


@st.composite
def schema_valid_entries(draw: st.DrawFn) -> Entry:
    """Generate an :class:`Entry` that survives an XSD-validated round-trip.

    Versus :func:`entries`, the constrained fields are the ones the XSD
    pattern/length-restricts: identifiers are capped at the 35-char Max35Text
    limit and the counterparty account must be a valid IBAN.
    """
    has_reason = draw(st.booleans())
    reason = draw(reason_codes) if has_reason else None
    detail = TransactionDetails(
        end_to_end_id=draw(st.none() | bounded_references),
        tx_id=draw(st.none() | bounded_references),
        reason_code=reason,
        counterparty_name=draw(st.none() | free_text),
        counterparty_account=draw(st.none() | ibans()),
    )
    return Entry(
        reference=draw(bounded_references),
        amount=draw(amounts),
        currency=draw(currencies),
        credit_debit_indicator=draw(indicators),
        status="BOOK",
        reason_code=reason,
        details=[detail],
    )


@st.composite
def schema_valid_statements(draw: st.DrawFn) -> Statement:
    """Generate a :class:`Statement` whose every field is XSD-valid."""
    return Statement(
        id=draw(bounded_references),
        creation_date_time="2026-06-15T08:00:00",
        account=Account(
            iban=draw(st.none() | ibans()),
            currency=draw(currencies),
            owner_name=draw(st.none() | free_text),
        ),
        entries=draw(st.lists(schema_valid_entries(), min_size=1, max_size=5)),
    )


# ── Reversal invariants ───────────────────────────────────────────────


@given(entry=entries(), stmt=statements())
def test_reversal_flips_indicator_and_preserves_amount(
    entry: Entry, stmt: Statement
) -> None:
    """A reversing record flips the indicator and preserves amount/currency."""
    record = build_reversal_record(
        entry, stmt, "MSG", "2026-06-15T08:00:00", "STMT-ID"
    )

    assert record["credit_debit"] == reverse_credit_debit(
        entry.credit_debit_indicator or "CRDT"
    )
    assert record["credit_debit"] != entry.credit_debit_indicator
    assert record["reversal_indicator"] == "true"
    # Amount is carried verbatim; currency falls back to the account currency
    # only when the entry has none (here entries always carry one).
    assert record["amount"] == entry.amount
    assert record["currency"] == entry.currency


@given(indicator=indicators)
def test_reverse_credit_debit_is_involution(indicator: str) -> None:
    """Reversing a canonical indicator twice is the identity."""
    assert reverse_credit_debit(reverse_credit_debit(indicator)) == indicator


@given(reference=references)
def test_reversal_reference_respects_iso_length_limit(
    reference: str,
) -> None:
    """Entry references in a reversal never exceed the 35-char ISO limit."""
    entry = Entry(reference=reference, credit_debit_indicator="CRDT")
    record = build_reversal_record(entry, Statement(), "MSG", "DT", "STMT-ID")
    assert len(record["entry_ref"]) <= 35
    assert len(record["original_ref"]) <= 35


# ── Parser robustness ─────────────────────────────────────────────────


def _wrap_statement(inner: str) -> str:
    """Wrap entry markup in a minimal well-formed camt.053 document."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">'
        "<BkToCstmrStmt>"
        "<GrpHdr><MsgId>M</MsgId>"
        "<CreDtTm>2026-06-15T08:00:00</CreDtTm></GrpHdr>"
        "<Stmt><Id>S</Id>"
        "<Acct><Id><IBAN>GB29NWBK60161331926819</IBAN></Id></Acct>"
        f"{inner}"
        "</Stmt></BkToCstmrStmt></Document>"
    )


@settings(suppress_health_check=[HealthCheck.too_slow])
@given(
    amount=amounts,
    currency=currencies,
    indicator=indicators,
    reason=st.none() | reason_codes,
    info=free_text,
)
def test_parser_never_crashes_on_wellformed_entry(
    amount: str,
    currency: str,
    indicator: str,
    reason: str | None,
    info: str,
) -> None:
    """Structurally-odd-but-well-formed entries parse without raising."""
    rtr = (
        f"<RtrInf><Rsn><Cd>{reason}</Cd></Rsn>"
        f"<AddtlInf>{escape(info)}</AddtlInf></RtrInf>"
        if reason
        else ""
    )
    ntry = (
        "<Ntry>"
        f'<Amt Ccy="{currency}">{amount}</Amt>'
        f"<CdtDbtInd>{indicator}</CdtDbtInd>"
        f"<NtryDtls><TxDtls>{rtr}</TxDtls></NtryDtls>"
        "</Ntry>"
    )
    stmt = parse_statement(_wrap_statement(ntry))
    assert len(stmt.entries) == 1
    entry = stmt.entries[0]
    assert entry.amount == amount
    assert entry.currency == currency
    assert entry.credit_debit_indicator == indicator
    assert entry.is_returnable() is (reason is not None)


@given(blob=st.text(max_size=200))
def test_parser_only_raises_its_own_error_on_arbitrary_text(
    blob: str,
) -> None:
    """Arbitrary text input only ever raises :class:`StatementParseError`."""
    try:
        parse_document(blob)
    except StatementParseError:
        # Expected for malformed/arbitrary text. Any other exception type
        # would propagate out of this block and fail the test.
        pass


# ── Round-trip stability ──────────────────────────────────────────────


@pytest.mark.slow
@settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(stmt=schema_valid_statements())
def test_serialise_parse_roundtrip_preserves_entries(
    stmt: Statement,
) -> None:
    """Serialising then re-parsing a statement preserves its entries."""
    xml = serialize_statement(stmt)
    reparsed = parse_statement(xml)

    assert len(reparsed.entries) == len(stmt.entries)
    for original, roundtripped in zip(
        stmt.entries, reparsed.entries, strict=False
    ):
        assert roundtripped.amount == original.amount
        assert roundtripped.currency == original.currency
        assert (
            roundtripped.credit_debit_indicator
            == original.credit_debit_indicator
        )
        assert roundtripped.reason_code == original.reason_code


# ── B2 + B3 idempotency invariants (added for v0.0.6) ─────────────────


# Original-reference strings that the reversal helper should handle.
# Allow the empty string, ISO 20022 printable ASCII, and arbitrary
# Unicode up to 200 characters so the digest-fallback path is exercised
# by inputs that overflow the 35-char ID limit.
_reversal_originals = st.text(max_size=200)


@given(original=_reversal_originals)
def test_stable_reversal_reference_is_deterministic(original: str) -> None:
    """For ANY original reference, two calls produce byte-identical output."""
    from camt053.reversal.reversal import stable_reversal_reference

    first = stable_reversal_reference(original)
    second = stable_reversal_reference(original)
    assert first == second


@given(original=_reversal_originals)
def test_stable_reversal_reference_never_exceeds_max_length(
    original: str,
) -> None:
    """For ANY original, the output is bounded by ISO 20022 Max35Text."""
    from camt053.reversal.reversal import stable_reversal_reference

    assert len(stable_reversal_reference(original)) <= 35


@given(
    original=_reversal_originals,
    custom_max=st.integers(min_value=6, max_value=80),
)
def test_stable_reversal_reference_respects_custom_max_length(
    original: str, custom_max: int
) -> None:
    """For ANY original + max_length combination, the bound holds."""
    from camt053.reversal.reversal import stable_reversal_reference

    assert (
        len(stable_reversal_reference(original, max_length=custom_max))
        <= custom_max
    )


@given(original=_reversal_originals)
def test_stable_reversal_reference_always_starts_with_rvsl_prefix(
    original: str,
) -> None:
    """The ``RVSL-`` prefix is preserved on both the readable and digest paths."""
    from camt053.reversal.reversal import stable_reversal_reference

    assert stable_reversal_reference(original).startswith("RVSL-")


# ── dedupe key determinism ────────────────────────────────────────────


def _build_doc_xml(msg_id: str, stmt_id: str, seq_nb: str) -> str:
    """Render a minimal camt.053 document with the given dedupe components."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08">'
        "<BkToCstmrStmt>"
        f"<GrpHdr><MsgId>{escape(msg_id)}</MsgId>"
        f"<CreDtTm>2026-06-21T10:00:00</CreDtTm></GrpHdr>"
        f"<Stmt><Id>{escape(stmt_id)}</Id>"
        f"<ElctrncSeqNb>{escape(seq_nb)}</ElctrncSeqNb>"
        f"<Acct><Id><IBAN>DE89370400440532013000</IBAN></Id></Acct>"
        "</Stmt>"
        "</BkToCstmrStmt></Document>"
    )


# Components that won't break the embedding (no <, >, &, ", ', newline,
# control chars). Real ISO 20022 IDs are stricter still; this is the
# permissive superset that exercises the dedupe logic.
_id_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N"), whitelist_characters="-_"
    ),
    min_size=1,
    max_size=35,
)


@given(msg_id=_id_text, stmt_id=_id_text, seq_nb=_id_text)
def test_compute_dedupe_key_deterministic_via_services(
    msg_id: str, stmt_id: str, seq_nb: str
) -> None:
    """For ANY (msg_id, stmt_id, seq_nb), services.compute_dedupe_key is idempotent."""
    from camt053 import services

    xml = _build_doc_xml(msg_id, stmt_id, seq_nb)
    first = services.compute_dedupe_key(xml)
    second = services.compute_dedupe_key(xml)
    assert first == second
    assert first == f"{msg_id}:{stmt_id}:{seq_nb}"


@given(msg_id=_id_text, stmt_id=_id_text, seq_nb=_id_text)
def test_compute_dedupe_key_distinguishes_different_inputs(
    msg_id: str, stmt_id: str, seq_nb: str
) -> None:
    """Two documents with the same components share a key; otherwise distinct."""
    from camt053 import services

    xml_a = _build_doc_xml(msg_id, stmt_id, seq_nb)
    xml_b = _build_doc_xml(msg_id, stmt_id, seq_nb + "-X")
    assert services.compute_dedupe_key(xml_a) != services.compute_dedupe_key(
        xml_b
    )
