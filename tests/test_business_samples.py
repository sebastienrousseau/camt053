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

"""Parser fidelity tests against the official ISO 20022 business samples.

These exercise the namespace-agnostic parser on genuine ISO sample messages
(variant .001.04), proving the library reads real-world statements -- not just
its own generated output.
"""

import os

import pytest

from camt053.parse import parse_document, parse_statement

GOLD = os.path.join(os.path.dirname(__file__), "gold_master")


def _load(name: str) -> str:
    with open(os.path.join(GOLD, name), encoding="utf-8") as handle:
        return handle.read()


def test_business_sample_statement_v04():
    """The official camt.053.001.04 sample parses to its true model."""
    doc = parse_document(_load("business_sample_camt.053.001.04.xml"))
    assert doc.message_type == "camt.053.001.04"  # detected from namespace
    assert doc.msg_id == "AAAASESS-FP-STAT001"
    stmt = doc.statements[0]
    assert stmt.account.other_id == "50000000054910000003"
    assert [b.type_code for b in stmt.balances] == ["OPBD", "CLBD"]
    assert len(stmt.entries) == 3
    assert {e.credit_debit_indicator for e in stmt.entries} == {"CRDT", "DBIT"}
    assert all(e.status == "BOOK" for e in stmt.entries)


@pytest.mark.parametrize(
    "name,expected_type",
    [
        ("business_sample_camt.052.001.04.xml", "camt.052.001.04"),
        ("business_sample_camt.053.001.04.xml", "camt.053.001.04"),
        ("business_sample_camt.054.001.04.xml", "camt.054.001.04"),
    ],
)
def test_business_samples_parse(name, expected_type):
    """All three official v04 samples parse and report their true type."""
    doc = parse_document(_load(name))
    assert doc.message_type == expected_type
    assert doc.msg_id
    assert doc.statements


def test_business_sample_has_no_returns():
    """A normal statement carries no return reasons (nothing to reverse)."""
    stmt = parse_statement(_load("business_sample_camt.053.001.04.xml"))
    assert stmt.entries_with_reason("AC04") == []
    assert all(not e.is_returnable() for e in stmt.entries)
