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

"""Tests for the IBAN, BIC, and LEI validators."""

import pytest

from camt053.exceptions import (
    InvalidBICError,
    InvalidIBANError,
    InvalidLEIError,
)
from camt053.validation import (
    validate_bic,
    validate_bic_format,
    validate_bic_safe,
    validate_iban,
    validate_iban_checksum,
    validate_iban_format,
    validate_iban_safe,
    validate_lei,
    validate_lei_format,
    validate_lei_safe,
)
from camt053.validation.lei_validator import validate_lei_checksum


# ── IBAN ────────────────────────────────────────────────────────────
def test_valid_iban():
    """A well-formed IBAN with a valid checksum passes."""
    assert validate_iban_safe("DE89370400440532013000") is True
    assert validate_iban_safe("GB29NWBK60161331926819") is True


def test_iban_bad_checksum():
    """An IBAN with a broken checksum fails."""
    assert validate_iban_safe("DE00370400440532013000") is False


def test_iban_empty_and_short():
    """Empty and too-short IBANs fail."""
    assert validate_iban_safe("") is False
    assert validate_iban_safe("DE12") is False


def test_iban_strict_raises():
    """Strict mode raises InvalidIBANError on a bad IBAN."""
    with pytest.raises(InvalidIBANError):
        validate_iban("DE00370400440532013000", field="account_id")


def test_iban_strict_format_raises():
    """Strict mode raises at the format step for a malformed IBAN."""
    with pytest.raises(InvalidIBANError):
        validate_iban("SHORT", field="account_id")


def test_iban_checksum_invalid_char():
    """A non-alphanumeric character is reported by the checksum step."""
    ok, error = validate_iban_checksum("DE89$70400440532013000")
    assert ok is False
    assert "Invalid character" in error


def test_iban_format_detail_messages():
    """Format errors describe each malformed component."""
    ok, error = validate_iban_format("1234567890123456")
    assert ok is False
    assert "country code" in error


def test_iban_format_checkdigit_and_bban():
    """Bad check digits and non-alphanumeric BBAN are both reported."""
    ok, error = validate_iban_format("DEXX370400440532013000")
    assert ok is False
    assert "check digits" in error
    ok, error = validate_iban_format("DE89*70400440532013000")
    assert ok is False
    assert "alphanumeric" in error


def test_iban_format_wrong_country_length():
    """A country-specific length mismatch is reported."""
    ok, error = validate_iban_format("DE8937040044053201300")  # one short
    assert ok is False
    assert "length for DE" in error


def test_iban_non_strict_returns_tuple():
    """Non-strict mode returns a (bool, message) tuple, never raising."""
    ok, error = validate_iban("DE00370400440532013000", strict=False)
    assert ok is False
    assert error


# ── BIC ─────────────────────────────────────────────────────────────
def test_valid_bic():
    """8- and 11-character BICs pass."""
    assert validate_bic_safe("DEUTDEFF") is True
    assert validate_bic_safe("NWBKGB2LXXX") is True


def test_bic_bad_length_and_country():
    """A bad length or unknown country code fails."""
    assert validate_bic_safe("DEUTDE") is False
    assert validate_bic_safe("DEUTZZFF") is False


def test_bic_strict_raises():
    """Strict mode raises InvalidBICError."""
    with pytest.raises(InvalidBICError):
        validate_bic("NOPE", field="account_servicer_bic")


def test_bic_empty_and_format_details():
    """Empty and structurally malformed BICs report detail messages."""
    assert validate_bic_format("")[0] is False
    ok, error = validate_bic_format("1234DEFF")  # bank code not alpha
    assert ok is False
    assert "bank code" in error


def test_bic_format_country_location_branch():
    """A digit country code is reported as invalid."""
    ok, error = validate_bic_format("DEUT12FF")  # country code digits
    assert ok is False
    assert "country code" in error


def test_bic_format_branch_code():
    """An 11-char BIC with a non-alphanumeric branch code is rejected."""
    ok, error = validate_bic_format("DEUTDEFF*XX")
    assert ok is False
    assert "branch code" in error


def test_bic_format_location_code():
    """An 8-char BIC with a non-alphanumeric location code is rejected."""
    ok, error = validate_bic_format("DEUTDE*F")
    assert ok is False
    assert "location code" in error


def test_bic_non_strict_returns_tuple():
    """Non-strict mode returns a tuple."""
    ok, error = validate_bic("NOPE", strict=False)
    assert ok is False
    assert error


# ── LEI ─────────────────────────────────────────────────────────────
def test_valid_lei():
    """A valid LEI passes."""
    assert validate_lei_safe("5493001KJTIIGC8Y1R12") is True


def test_lei_bad():
    """A malformed or bad-checksum LEI fails."""
    assert validate_lei_safe("SHORT") is False
    assert validate_lei_safe("5493001KJTIIGC8Y1R99") is False


def test_lei_strict_raises():
    """Strict mode raises InvalidLEIError on a bad checksum."""
    with pytest.raises(InvalidLEIError):
        validate_lei("5493001KJTIIGC8Y1R99", field="org_id_lei")


def test_lei_strict_format_raises():
    """Strict mode raises at the format step for a malformed LEI."""
    with pytest.raises(InvalidLEIError):
        validate_lei("SHORT", field="org_id_lei")


def test_lei_format_details():
    """LEI format errors describe length and check-digit issues."""
    assert validate_lei_format("")[0] is False
    ok, error = validate_lei_format("5493001KJTIIGC8Y1RAB")  # non-digit check
    assert ok is False
    assert "check digits" in error


def test_lei_format_non_alnum_identifier():
    """A non-alphanumeric character in the identifier body is rejected."""
    ok, error = validate_lei_format("5493001KJTIIGC8Y1*12")
    assert ok is False
    assert "alphanumeric" in error


def test_lei_safe_valid():
    """The safe wrapper returns True for a valid LEI."""
    assert validate_lei_safe("5493001KJTIIGC8Y1R12") is True


def test_lei_checksum_invalid_char():
    """A non-alphanumeric character is reported by the LEI checksum step."""
    ok, error = validate_lei_checksum("5493001KJTIIGC8Y1R1$")
    assert ok is False
    assert "Invalid character" in error


def test_lei_non_strict_returns_tuple():
    """Non-strict mode returns a tuple for a bad-format LEI."""
    ok, error = validate_lei("SHORT", strict=False)
    assert ok is False
    assert error
