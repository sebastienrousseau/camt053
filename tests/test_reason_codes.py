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

"""Tests for ISO external return reason code helpers."""

from camt053.constants import reverse_credit_debit
from camt053.parse.reason_codes import (
    describe_reason,
    is_known_reason,
    list_reason_codes,
)


def test_describe_known_reason():
    """A known reason resolves to its human-readable name."""
    assert describe_reason("AC04") == "Closed Account Number"


def test_describe_is_case_insensitive():
    """Reason lookup is case-insensitive."""
    assert describe_reason("ac04") == "Closed Account Number"


def test_describe_unknown_reason():
    """An unknown reason returns a generic label."""
    assert describe_reason("ZZ99") == "Unknown reason code"
    assert describe_reason("") == "Unknown reason code"


def test_is_known_reason():
    """Known/unknown reasons are classified correctly."""
    assert is_known_reason("AC04") is True
    assert is_known_reason("ac06") is True
    assert is_known_reason("nope") is False


def test_list_reason_codes():
    """The reason list is non-empty and shaped as code/name dicts."""
    rows = list_reason_codes()
    assert {"code": "AC04", "name": "Closed Account Number"} in rows
    assert all("code" in r and "name" in r for r in rows)


def test_reverse_credit_debit():
    """Credit/debit indicators flip; unknown values default to DBIT."""
    assert reverse_credit_debit("CRDT") == "DBIT"
    assert reverse_credit_debit("DBIT") == "CRDT"
    assert reverse_credit_debit("crdt") == "DBIT"
    assert reverse_credit_debit("") == "DBIT"
