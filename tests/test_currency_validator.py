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

"""Tests for the ISO 4217 currency validator."""

from camt053.validation import currency_minor_units, validate_currency


def test_validate_currency_known():
    """Recognised codes validate (case-insensitively) (#22)."""
    assert validate_currency("EUR") is True
    assert validate_currency("usd") is True
    assert validate_currency(" jpy ") is True


def test_validate_currency_unknown():
    """Unrecognised or empty codes do not validate (#22)."""
    assert validate_currency("ZZZ") is False
    assert validate_currency("") is False
    assert validate_currency("EU") is False


def test_currency_minor_units():
    """Minor-unit lookup matches ISO 4217 (#22)."""
    assert currency_minor_units("EUR") == 2
    assert currency_minor_units("JPY") == 0
    assert currency_minor_units("BHD") == 3
    assert currency_minor_units("kwd") == 3


def test_currency_minor_units_unknown_is_none():
    """An unknown currency has no minor-unit value (#22)."""
    assert currency_minor_units("ZZZ") is None
    assert currency_minor_units("") is None
