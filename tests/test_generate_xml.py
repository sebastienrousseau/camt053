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

"""Tests for rendering and validating reversing-entry XML."""

import os

import pytest

from camt053.exceptions import ReversalGenerationError
from camt053.parse import parse_statement
from camt053.xml.generate_xml import (
    generate_reversal_for_statement,
    generate_reversal_xml,
    write_reversal_xml,
)
from camt053.xml.validate_via_xsd import validate_xml_string_via_xsd


def test_generate_reversal_xml_validates(reversal_record):
    """A complete record renders to XSD-valid camt.053 XML."""
    xml = generate_reversal_xml([reversal_record])
    assert xml.lstrip().startswith("<?xml")
    assert "urn:iso:std:iso:20022:tech:xsd:camt.053.001.14" in xml
    assert "<RvslInd>true</RvslInd>" in xml
    assert "<CdtDbtInd>DBIT</CdtDbtInd>" in xml
    assert "<Cd>AC04</Cd>" in xml


def test_generate_for_statement(statement_xml):
    """The statement-level helper builds and renders in one call."""
    stmt = parse_statement(statement_xml)
    xml = generate_reversal_for_statement(stmt, "AC04")
    assert "RVSL-NTRY-0001" in xml
    assert "Globex SA" in xml


def test_minimal_record_validates():
    """A minimal record (only required-ish fields) still validates."""
    record = {
        "statement_msg_id": "M",
        "creation_date_time": "2026-06-15T08:00:00",
        "statement_id": "S",
        "account_id": "GB29NWBK60161331926819",
        "account_currency": "EUR",
        "bal_type_code": "CLBD",
        "bal_amount": "0.00",
        "bal_currency": "EUR",
        "bal_credit_debit": "CRDT",
        "bal_date": "2026-06-15",
        "amount": "1.00",
        "currency": "EUR",
        "credit_debit": "DBIT",
        "reversal_indicator": "true",
        "status": "BOOK",
        "reason_code": "AC04",
    }
    xml = generate_reversal_xml([record])
    assert validate_xml_string_via_xsd(
        xml,
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "camt053",
            "templates",
            "camt.053.001.14",
            "camt.053.001.14.xsd",
        ),
    )


def test_proprietary_account_id_validates():
    """A record with a proprietary (non-IBAN) account id validates."""
    record = {
        "statement_msg_id": "M",
        "creation_date_time": "2026-06-15T08:00:00",
        "statement_id": "S",
        "account_id_other": "ACC-XYZ-1",
        "account_currency": "EUR",
        "bal_type_code": "CLBD",
        "bal_amount": "0.00",
        "bal_currency": "EUR",
        "bal_credit_debit": "CRDT",
        "bal_date": "2026-06-15",
        "amount": "1.00",
        "currency": "EUR",
        "credit_debit": "DBIT",
        "reversal_indicator": "true",
        "status": "BOOK",
        "reason_code": "AC04",
    }
    xml = generate_reversal_xml([record])
    assert "<Othr><Id>ACC-XYZ-1</Id></Othr>" in xml


def test_empty_records_raises():
    """An empty record list raises ReversalGenerationError."""
    with pytest.raises(ReversalGenerationError, match="empty"):
        generate_reversal_xml([])


def test_invalid_currency_fails_validation(reversal_record):
    """A record that renders non-conforming XML raises on validation."""
    bad = dict(reversal_record)
    bad["currency"] = "EU"  # not a 3-letter ISO 4217 code
    with pytest.raises(ReversalGenerationError, match="failed validation"):
        generate_reversal_xml([bad])


def test_write_to_tmp_outside_cwd_rejected(
    tmp_path, monkeypatch, reversal_record
):
    """Writing to an allowed temp path outside the cwd is still rejected."""
    import tempfile

    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    target = os.path.join(tempfile.gettempdir(), "camt053_reversal_out.xml")
    with pytest.raises(ValueError, match="outside working directory"):
        write_reversal_xml([reversal_record], target)


def test_write_reversal_xml(tmp_path, monkeypatch, reversal_record):
    """The reversal can be written to a file in the working directory."""
    monkeypatch.chdir(tmp_path)
    out = write_reversal_xml([reversal_record], "reversal.xml")
    assert os.path.isfile(out)
    assert "RvslInd" in open(out, encoding="utf-8").read()


def test_write_reversal_outside_cwd_raises(
    tmp_path, monkeypatch, reversal_record
):
    """Writing outside the working directory is rejected."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        write_reversal_xml([reversal_record], "/etc/reversal.xml")
