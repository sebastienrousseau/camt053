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

"""Tests for SWIFT character-set cleansing (#19)."""

from camt053 import services
from camt053.compliance import (
    FieldCleansing,
    cleanse_field,
    cleanse_records,
    cleanse_text,
    is_swift_x,
)

# ── is_swift_x ───────────────────────────────────────────────────────


def test_is_swift_x_accepts_full_charset():
    """The full SWIFT X charset is recognised as compliant."""
    assert is_swift_x("Acme Treasury Ltd. (UK), Ref: 12/34-56+78?:'")
    assert is_swift_x("")


def test_is_swift_x_rejects_outside_chars():
    """Characters outside the SWIFT X set are flagged."""
    assert is_swift_x("Café") is False
    assert is_swift_x("a&b") is False


# ── cleanse_text: accented / special characters ──────────────────────


def test_cleanse_accented_letters_transliterated():
    """Accented Latin letters fold to their base form."""
    report = cleanse_text("Café Société Müller")
    assert report.cleansed == "Cafe Societe Muller"
    assert report.changed is True
    assert set(report.replaced) == {"é", "ü"}


def test_cleanse_ligatures_expanded():
    """Known ligatures expand to their conventional spelling."""
    assert cleanse_text("Straße").cleansed == "Strasse"
    assert cleanse_text("Æon Œuvre").cleansed == "AEon OEuvre"
    assert cleanse_text("Smørrebrød").cleansed == "Smorrebrod"


def test_cleanse_typographic_punctuation_folded():
    """Smart quotes and dashes fold to SWIFT-safe ASCII."""
    report = cleanse_text("O’Brien — “ACME”")
    assert report.cleansed == "O'Brien - 'ACME'"
    assert report.changed is True


def test_cleanse_unmappable_char_becomes_space():
    """A character with no SWIFT-safe spelling becomes a single space."""
    report = cleanse_text("A☃B")  # snowman between letters
    assert report.cleansed == "A B"
    assert "☃" in report.replaced


def test_cleanse_collapses_whitespace_and_trims():
    """Runs of whitespace collapse and surrounding space is trimmed."""
    report = cleanse_text("  Acme   \t Corp  ")
    assert report.cleansed == "Acme Corp"


def test_cleanse_safe_text_unchanged():
    """Already-compliant text passes through untouched."""
    report = cleanse_text("Acme Treasury Ltd")
    assert report.cleansed == "Acme Treasury Ltd"
    assert report.changed is False
    assert report.replaced == []
    assert report.truncated is False


def test_cleanse_none_is_empty():
    """A ``None`` value cleanses to an empty string."""
    report = cleanse_text(None)
    assert report.cleansed == ""
    assert report.original == ""


# ── cleanse_text: length truncation ──────────────────────────────────


def test_cleanse_truncates_to_max_length():
    """The cleansed value is truncated to ``max_length``."""
    report = cleanse_text("ABCDEFGHIJ", max_length=4)
    assert report.cleansed == "ABCD"
    assert report.truncated is True


def test_cleanse_truncation_rstrips_trailing_space():
    """Truncation drops a trailing space left at the cut point."""
    report = cleanse_text("ABCD EFGH", max_length=5)
    assert report.cleansed == "ABCD"
    assert report.truncated is True


def test_cleanse_no_truncation_when_within_limit():
    """A value within the limit is not marked truncated."""
    report = cleanse_text("ABC", max_length=10)
    assert report.cleansed == "ABC"
    assert report.truncated is False


# ── FieldCleansing report ────────────────────────────────────────────


def test_field_cleansing_to_dict():
    """The report serialises every audit attribute."""
    report = cleanse_text("Café", field_name="owner")
    data = report.to_dict()
    assert data == {
        "field": "owner",
        "original": "Café",
        "cleansed": "Cafe",
        "replaced": ["é"],
        "truncated": False,
        "changed": True,
    }


def test_field_cleansing_is_dataclass():
    """FieldCleansing exposes its fields as a dataclass."""
    report = FieldCleansing(original="x", cleansed="x")
    assert report.field is None
    assert report.changed is False


# ── cleanse_field ────────────────────────────────────────────────────


def test_cleanse_field_mutates_record():
    """cleanse_field rewrites the field in place and reports the change."""
    record = {"account_owner_name": "Café SA"}
    report = cleanse_field(record, "account_owner_name", max_length=140)
    assert record["account_owner_name"] == "Cafe SA"
    assert report is not None
    assert report.field == "account_owner_name"


def test_cleanse_field_absent_or_empty_returns_none():
    """An absent or empty field yields no report and no mutation."""
    assert cleanse_field({}, "account_owner_name") is None
    record = {"account_owner_name": ""}
    assert cleanse_field(record, "account_owner_name") is None
    assert record["account_owner_name"] == ""


# ── cleanse_records ──────────────────────────────────────────────────


def test_cleanse_records_only_reports_changes():
    """Only fields that actually changed appear in the combined report."""
    records = [
        {
            "account_owner_name": "Müller GmbH",
            "counterparty_name": "Globex SA",  # already safe
            "additional_info": "Réf: paiement annulé",
            "reason_name": "Closed Account Number",  # already safe
        }
    ]
    reports = cleanse_records(records)
    changed_fields = {r.field for r in reports}
    assert changed_fields == {"account_owner_name", "additional_info"}
    assert records[0]["account_owner_name"] == "Muller GmbH"
    assert records[0]["counterparty_name"] == "Globex SA"


def test_cleanse_records_enforces_field_max_length():
    """additional_info is truncated to its 105-char SWIFT limit."""
    long_info = "A" * 200
    records = [{"additional_info": long_info}]
    reports = cleanse_records(records)
    assert len(records[0]["additional_info"]) == 105
    assert reports[0].truncated is True


def test_cleanse_records_missing_fields_skipped():
    """Records lacking the constrained fields produce no reports."""
    records = [{"amount": "1.00"}]
    assert cleanse_records(records) == []


# ── services facade ──────────────────────────────────────────────────


def test_services_cleanse_records_report(reversal_record):
    """services.cleanse_records returns a JSON-friendly change report."""
    reversal_record["account_owner_name"] = "Société Générale"
    result = services.cleanse_records([reversal_record])
    assert result["changed"] == 1
    assert result["fields"][0]["field"] == "account_owner_name"
    assert reversal_record["account_owner_name"] == "Societe Generale"


def test_services_cleanse_records_no_changes(reversal_record):
    """A fully-compliant record reports zero changes."""
    result = services.cleanse_records([reversal_record])
    assert result == {"changed": 0, "fields": []}


# ── reversal still validates after cleansing ─────────────────────────


def _statement_with_accented_names() -> str:
    """A camt.053 statement whose names carry non-SWIFT characters."""
    return (
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">'
        "<BkToCstmrStmt><GrpHdr><MsgId>M</MsgId>"
        "<CreDtTm>2026-06-15T08:00:00</CreDtTm></GrpHdr>"
        "<Stmt><Id>S</Id>"
        "<CreDtTm>2026-06-15T08:00:00</CreDtTm>"
        "<Acct><Id><IBAN>GB29NWBK60161331926819</IBAN></Id>"
        "<Ccy>EUR</Ccy><Ownr><Nm>Société Générale</Nm></Ownr></Acct>"
        "<Bal><Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>"
        '<Amt Ccy="EUR">100.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>'
        "<Dt><Dt>2026-06-15</Dt></Dt></Bal>"
        '<Ntry><NtryRef>N1</NtryRef><Amt Ccy="EUR">100.00</Amt>'
        "<CdtDbtInd>CRDT</CdtDbtInd><Sts><Cd>BOOK</Cd></Sts>"
        "<BookgDt><Dt>2026-06-15</Dt></BookgDt>"
        "<NtryDtls><TxDtls>"
        "<Refs><EndToEndId>E2E</EndToEndId></Refs>"
        "<RtrInf><Rsn><Cd>AC04</Cd></Rsn></RtrInf>"
        "<RltdPties><Dbtr><Nm>Müller &amp; Schörghuber KG</Nm></Dbtr>"
        "</RltdPties>"
        "</TxDtls></NtryDtls></Ntry>"
        "</Stmt></BkToCstmrStmt></Document>"
    )


def test_generate_reversal_with_cleanse_validates():
    """An opt-in cleansed reversal still validates and is SWIFT-safe."""
    xml = _statement_with_accented_names()
    out = services.generate_reversal(xml, reason_code="AC04", cleanse=True)
    assert "Societe Generale" in out
    assert "Muller" in out
    assert "Société" not in out


def test_generate_reversal_without_cleanse_keeps_accents():
    """The default path leaves the source names untouched."""
    xml = _statement_with_accented_names()
    out = services.generate_reversal(xml, reason_code="AC04")
    assert "Société Générale" in out


def test_generate_with_cleanse(reversal_record):
    """services.generate cleanses records in place when opted in."""
    reversal_record["counterparty_name"] = "Café Noir"
    out = services.generate([reversal_record], cleanse=True)
    assert "Cafe Noir" in out
    assert reversal_record["counterparty_name"] == "Cafe Noir"
