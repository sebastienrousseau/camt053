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

"""Tests for the typed statement model."""

from camt053.models import (
    Account,
    Balance,
    Entry,
    ParsedDocument,
    Statement,
    TransactionDetails,
)


def test_account_identifier_prefers_iban():
    """``identifier`` returns the IBAN when present, else the other id."""
    assert Account(iban="GB29", other_id="X").identifier() == "GB29"
    assert Account(other_id="X").identifier() == "X"
    assert Account().identifier() is None


def test_entry_is_returnable_via_entry_reason():
    """An entry-level reason makes the entry returnable."""
    assert Entry(reason_code="AC04").is_returnable() is True


def test_entry_is_returnable_via_detail():
    """A reason carried only on a detail still marks the entry returnable."""
    entry = Entry(details=[TransactionDetails(reason_code="AC06")])
    assert entry.is_returnable() is True


def test_entry_not_returnable():
    """An entry with no reason anywhere is not returnable."""
    assert Entry(reference="X").is_returnable() is False


def test_statement_entries_with_reason_matches_details():
    """``entries_with_reason`` considers both entry and detail reasons."""
    e1 = Entry(reference="A", details=[TransactionDetails(reason_code="AC04")])
    e2 = Entry(reference="B", reason_code="AC06")
    stmt = Statement(entries=[e1, e2])
    assert stmt.entries_with_reason("AC04") == [e1]
    assert stmt.entries_with_reason("ac06") == [e2]
    assert stmt.entries_with_reason("MD07") == []


def test_to_dict_serialisation():
    """Every model exposes a JSON-friendly ``to_dict``."""
    detail = TransactionDetails(end_to_end_id="E2E", reason_code="AC04")
    entry = Entry(reference="A", amount="1.00", details=[detail])
    balance = Balance(type_code="CLBD", amount="5.00")
    account = Account(iban="GB29")
    stmt = Statement(
        id="S1", account=account, balances=[balance], entries=[entry]
    )
    doc = ParsedDocument(message_type="camt.053.001.14", statements=[stmt])

    data = doc.to_dict()
    assert data["statements"][0]["account"]["iban"] == "GB29"
    assert data["statements"][0]["balances"][0]["type_code"] == "CLBD"
    assert (
        data["statements"][0]["entries"][0]["details"][0]["reason_code"]
        == "AC04"
    )
    assert doc.all_entries() == [entry]
