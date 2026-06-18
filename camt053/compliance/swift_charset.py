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

"""SWIFT character-set cleansing for ISO 20022 free-text fields.

Cross-border payment rails (SWIFT FIN, CBPR+) restrict the free-text fields
that carry party names and remittance / return narrative to the **SWIFT X**
character set::

    a-z A-Z 0-9  / - ? : ( ) . , ' +  and space

Characters outside that set (accented letters, typographic punctuation, other
scripts, control characters) are rejected by the network and cause a payment
to be NAKed. This module cleanses text bound for SWIFT-constrained fields
(``Nm`` / ``AddtlInf`` / party / counterparty names) before rendering:

* accented Latin letters are transliterated to their base form (``é`` -> ``e``,
  ``ß`` -> ``ss``) via Unicode NFKD decomposition;
* a small map of common typographic punctuation is folded to its ASCII
  equivalent (smart quotes -> ``'``, en/em dash -> ``-``);
* anything still outside the SWIFT X set is replaced with a single space;
* runs of whitespace are collapsed and the result is trimmed;
* the value is truncated to an optional maximum length.

Every cleanse returns a :class:`FieldCleansing` report describing exactly what
changed, so callers retain an audit trail. The functions are pure and have no
side effects on their inputs.

Example:
    >>> cleanse_text("Café Société — €100", max_length=20).cleansed
    'Cafe Societe - 100'
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import Any

__all__ = [
    "SWIFT_X_CHARSET",
    "FieldCleansing",
    "cleanse_field",
    "cleanse_records",
    "cleanse_text",
    "is_swift_x",
]

# The SWIFT X character set: letters, digits, and a fixed punctuation subset.
SWIFT_X_CHARSET = frozenset(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "/-?:().,'+ "
)

# Common typographic punctuation folded to its SWIFT X equivalent before the
# generic NFKD / replacement pass (NFKD leaves these unchanged on its own).
_PUNCTUATION_MAP = {
    "‘": "'",  # left single quotation mark
    "’": "'",  # right single quotation mark
    "‚": "'",  # single low-9 quotation mark
    "“": "'",  # left double quotation mark
    "”": "'",  # right double quotation mark
    "„": "'",  # double low-9 quotation mark
    "–": "-",  # en dash
    "—": "-",  # em dash
    "−": "-",  # minus sign
    "«": "'",  # left-pointing double angle quotation mark
    "»": "'",  # right-pointing double angle quotation mark
}

# Characters whose NFKD decomposition does not yield an ASCII base form but
# which have a well-understood SWIFT-safe spelling.
_LIGATURE_MAP = {
    "ß": "ss",
    "æ": "ae",
    "Æ": "AE",
    "œ": "oe",
    "Œ": "OE",
    "ø": "o",
    "Ø": "O",
    "ð": "d",
    "Ð": "D",
    "þ": "th",
    "Þ": "TH",
    "ł": "l",
    "Ł": "L",
    "đ": "d",
    "Đ": "D",
}


def is_swift_x(value: str) -> bool:
    """Return ``True`` if every character of ``value`` is in the SWIFT X set."""
    return all(ch in SWIFT_X_CHARSET for ch in value)


@dataclass
class FieldCleansing:
    """A report of how a single value was cleansed for SWIFT compliance.

    Attributes:
        field: The logical field name (e.g. ``"account_owner_name"``), or
            ``None`` for an ad-hoc :func:`cleanse_text` call.
        original: The value as supplied by the caller.
        cleansed: The SWIFT X-safe value after transliteration / replacement
            and optional truncation.
        replaced: Characters that were transliterated or replaced, in order of
            first appearance (each listed once).
        truncated: ``True`` if the value was shortened to fit ``max_length``.
    """

    original: str
    cleansed: str
    field: str | None = None
    replaced: list[str] = dataclass_field(default_factory=list)
    truncated: bool = False

    @property
    def changed(self) -> bool:
        """Return ``True`` if cleansing altered the original value."""
        return self.cleansed != self.original

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation of the report."""
        return {
            "field": self.field,
            "original": self.original,
            "cleansed": self.cleansed,
            "replaced": list(self.replaced),
            "truncated": self.truncated,
            "changed": self.changed,
        }


def _transliterate(char: str) -> str:
    """Map a single character to its SWIFT-safe spelling (possibly empty).

    Already-safe characters pass through unchanged. Known ligatures use their
    conventional expansion; everything else is decomposed via NFKD and stripped
    of combining marks, keeping only the resulting SWIFT X characters.
    """
    if char in SWIFT_X_CHARSET:
        return char
    if char in _PUNCTUATION_MAP:
        return _PUNCTUATION_MAP[char]
    if char in _LIGATURE_MAP:
        return _LIGATURE_MAP[char]
    decomposed = unicodedata.normalize("NFKD", char)
    kept = "".join(
        c
        for c in decomposed
        if c in SWIFT_X_CHARSET and not unicodedata.combining(c)
    )
    return kept


def cleanse_text(
    value: str | None,
    max_length: int | None = None,
    field_name: str | None = None,
) -> FieldCleansing:
    """Cleanse a single free-text value for the SWIFT X character set.

    Args:
        value: The raw text (``None`` is treated as an empty string).
        max_length: If given, the cleansed value is truncated to at most this
            many characters.
        field_name: Optional logical field name recorded in the report.

    Returns:
        A :class:`FieldCleansing` report; ``report.cleansed`` is the safe value.
    """
    original = value or ""
    replaced: list[str] = []
    pieces: list[str] = []
    for char in original:
        mapped = _transliterate(char)
        if mapped == char:
            pieces.append(char)
            continue
        if char not in replaced:
            replaced.append(char)
        # Anything that does not transliterate to a SWIFT X spelling becomes a
        # single space so word boundaries survive.
        pieces.append(mapped if mapped else " ")

    collapsed = " ".join("".join(pieces).split())

    truncated = False
    if max_length is not None and len(collapsed) > max_length:
        collapsed = collapsed[:max_length].rstrip()
        truncated = True

    return FieldCleansing(
        original=original,
        cleansed=collapsed,
        field=field_name,
        replaced=replaced,
        truncated=truncated,
    )


def cleanse_field(
    record: dict[str, Any],
    field_name: str,
    max_length: int | None = None,
) -> FieldCleansing | None:
    """Cleanse one field of a record in place, returning its report.

    Args:
        record: The flat record whose field is cleansed in place.
        field_name: The key to cleanse.
        max_length: Optional maximum length for the field's value.

    Returns:
        The :class:`FieldCleansing` report, or ``None`` if the field is absent
        or empty (nothing to cleanse).
    """
    raw = record.get(field_name)
    if not raw:
        return None
    report = cleanse_text(raw, max_length=max_length, field_name=field_name)
    record[field_name] = report.cleansed
    return report


# SWIFT-constrained fields in a flat reversing-entry record, mapped to the
# maximum length permitted by the camt.053 schema for that element.
_CONSTRAINED_FIELDS = {
    "account_owner_name": 140,
    "counterparty_name": 140,
    "additional_info": 105,
    "reason_name": 140,
}


def cleanse_records(
    records: list[dict[str, Any]],
) -> list[FieldCleansing]:
    """Cleanse the SWIFT-constrained fields of reversing-entry records.

    Mutates each record in place so its name / narrative fields hold only
    SWIFT X characters within their maximum length, and returns a combined
    report of every field that was changed (unchanged fields are omitted).

    Args:
        records: The flat reversing-entry records to cleanse in place.

    Returns:
        A list of :class:`FieldCleansing` reports for the fields that changed.
    """
    reports: list[FieldCleansing] = []
    for record in records:
        for field_name, max_length in _CONSTRAINED_FIELDS.items():
            report = cleanse_field(record, field_name, max_length=max_length)
            if report is not None and report.changed:
                reports.append(report)
    return reports
