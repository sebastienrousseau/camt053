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

"""Tests for building reversing-entry records."""

import pytest

from camt053.exceptions import ReversalGenerationError
from camt053.models import Account, Entry, Statement, TransactionDetails
from camt053.parse import parse_statement
from camt053.reversal.reversal import (
    build_reversal_record,
    build_reversal_records,
)


def test_build_records_for_reason(statement_xml):
    """Only the entries with the requested reason are reversed."""
    stmt = parse_statement(statement_xml)
    records = build_reversal_records(stmt, "AC04")
    assert len(records) == 1
    record = records[0]
    assert record["credit_debit"] == "DBIT"  # flipped from CRDT
    assert record["reversal_indicator"] == "true"
    assert record["original_ref"] == "NTRY-0001"
    assert record["entry_ref"] == "RVSL-NTRY-0001"
    assert record["reason_code"] == "AC04"
    assert "Closed Account Number" in record["additional_info"]
    assert record["counterparty_name"] == "Globex SA"


def test_build_records_default_all_returnable(statement_xml):
    """Without a reason, every returnable entry is reversed."""
    stmt = parse_statement(statement_xml)
    records = build_reversal_records(stmt)
    assert len(records) == 2  # AC04 + AC06, not the plain debit


def test_build_records_no_match_raises(statement_xml):
    """No matching entry raises ReversalGenerationError."""
    stmt = parse_statement(statement_xml)
    with pytest.raises(ReversalGenerationError, match="MD07"):
        build_reversal_records(stmt, "MD07")


def test_build_records_no_returnable_raises():
    """A statement with no returnable entries raises."""
    stmt = Statement(entries=[Entry(reference="X")])
    with pytest.raises(ReversalGenerationError, match="any return reason"):
        build_reversal_records(stmt)


def test_msg_id_and_creation_overrides(statement_xml):
    """Caller-supplied message id and timestamp are honoured."""
    stmt = parse_statement(statement_xml)
    records = build_reversal_records(
        stmt, "AC04", msg_id="MY-MSG", creation_date_time="2026-01-01T00:00:00"
    )
    assert records[0]["statement_msg_id"] == "MY-MSG"
    assert records[0]["creation_date_time"] == "2026-01-01T00:00:00"


def test_build_single_record_reverses_debit():
    """Reversing a debit entry produces a credit reversing entry."""
    entry = Entry(
        reference="E1",
        amount="10.00",
        currency="USD",
        credit_debit_indicator="DBIT",
        details=[TransactionDetails(reason_code="AC04", end_to_end_id="E2E")],
    )
    stmt = Statement(id="S", account=Account(iban="GB29", currency="USD"))
    record = build_reversal_record(entry, stmt, "MSG", "DT", "STMT-ID")
    assert record["credit_debit"] == "CRDT"
    assert record["currency"] == "USD"
    assert record["end_to_end_id"] == "E2E"


def test_long_reference_is_truncated():
    """Entry references are truncated to the 35-char ISO limit."""
    long_ref = "X" * 40
    entry = Entry(reference=long_ref, credit_debit_indicator="CRDT")
    stmt = Statement()
    record = build_reversal_record(entry, stmt, "MSG", "DT", "STMT-ID")
    assert len(record["entry_ref"]) == 35
    assert len(record["original_ref"]) == 35
