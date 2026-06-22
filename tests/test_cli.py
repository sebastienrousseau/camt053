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

"""Tests for the command-line interface."""

import json
import os

from click.testing import CliRunner

from camt053.cli.cli import main

GOLD = os.path.join(os.path.dirname(__file__), "gold_master")

_INVALID_DOC = (
    '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.04">'
    "<BkToCstmrStmt><GrpHdr></GrpHdr><Stmt></Stmt></BkToCstmrStmt>"
    "</Document>"
)


def _write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content)
    return str(path)


def test_message_types_command():
    """The message-types command lists supported types."""
    result = CliRunner().invoke(main, ["message-types"])
    assert result.exit_code == 0
    assert "camt.053.001.14" in result.output


def test_reasons_command():
    """The reasons command lists reason codes with their action (#24)."""
    result = CliRunner().invoke(main, ["reasons"])
    assert result.exit_code == 0
    assert "AC04" in result.output
    assert "Action" in result.output
    assert "return" in result.output


def test_classify_command():
    """The classify command reports a reason code's action (#24)."""
    result = CliRunner().invoke(main, ["classify", "-r", "AM04"])
    assert result.exit_code == 0
    assert "AM04" in result.output
    assert "retry" in result.output


def test_entries_command(tmp_path, statement_xml):
    """The entries command lists statement entries."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(main, ["entries", "-i", path])
    assert result.exit_code == 0
    assert "NTRY-0001" in result.output
    assert "3 entries" in result.output


def test_entries_command_filtered(tmp_path, statement_xml):
    """The entries command filters by reason code."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(main, ["entries", "-i", path, "-r", "AC04"])
    assert result.exit_code == 0
    assert "1 entry" in result.output


def test_validate_command_valid(tmp_path):
    """The validate command exits 0 for a schema-valid statement."""
    with open(
        os.path.join(GOLD, "business_sample_camt.053.001.04.xml"),
        encoding="utf-8",
    ) as handle:
        xml = handle.read()
    path = _write(tmp_path, "stmt.xml", xml)
    result = CliRunner().invoke(main, ["validate", "-i", path])
    assert result.exit_code == 0
    assert "Valid camt.053.001.04" in result.output


def test_validate_command_invalid(tmp_path):
    """The validate command exits 1 and lists errors for an invalid doc."""
    path = _write(tmp_path, "bad.xml", _INVALID_DOC)
    result = CliRunner().invoke(main, ["validate", "-i", path])
    assert result.exit_code == 1
    assert "Invalid camt.053.001.04" in result.output


def test_validate_command_bad_file():
    """The validate command exits non-zero on a missing file."""
    result = CliRunner().invoke(main, ["validate", "-i", "/no/such/file.xml"])
    assert result.exit_code == 1
    assert "Validation failed" in result.output


def test_entries_command_filtered_by_amount(tmp_path, statement_xml):
    """The entries command filters by amount bounds (#21)."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(main, ["entries", "-i", path, "--min", "1000"])
    assert result.exit_code == 0
    assert "1 entry" in result.output
    assert "NTRY-0001" in result.output


def test_entries_command_filtered_by_status_and_date(tmp_path, statement_xml):
    """The entries command filters by status and date range (#21)."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(
        main,
        [
            "entries",
            "-i",
            path,
            "--status",
            "BOOK",
            "--from",
            "2026-06-15",
            "--to",
            "2026-06-15",
        ],
    )
    assert result.exit_code == 0
    assert "2 entries" in result.output


def test_entries_command_bad_filter_value(tmp_path, statement_xml):
    """The entries command exits non-zero on a bad filter value (#21)."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(main, ["entries", "-i", path, "--min", "abc"])
    assert result.exit_code == 1
    assert "Failed" in result.output


def test_entries_export_csv_stdout(tmp_path, statement_xml):
    """Exporting CSV to stdout emits a header and one row per entry (#23)."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(
        main, ["entries", "-i", path, "--export", "csv"]
    )
    assert result.exit_code == 0
    lines = [line for line in result.output.splitlines() if line]
    assert lines[0].startswith(
        "reference,amount,currency,credit_debit_indicator,status"
    )
    assert len(lines) == 4  # header + 3 entries
    assert "NTRY-0001,1500.00,EUR,CRDT,BOOK" in result.output


def test_entries_export_json_stdout(tmp_path, statement_xml):
    """Exporting JSON to stdout emits the list of entry dicts (#23)."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(
        main, ["entries", "-i", path, "--export", "json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 3
    assert data[0]["reference"] == "NTRY-0001"


def test_entries_export_csv_to_file(tmp_path, statement_xml):
    """Exporting CSV to a file writes it and reports success (#23)."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    out = str(tmp_path / "entries.csv")
    result = CliRunner().invoke(
        main, ["entries", "-i", path, "--export", "csv", "-o", out]
    )
    assert result.exit_code == 0
    assert "Exported 3 entries to" in result.output
    content = open(out, encoding="utf-8").read()
    assert content.startswith("reference,amount,currency")
    assert "NTRY-0002" in content


def test_entries_export_json_to_file(tmp_path, statement_xml):
    """Exporting JSON to a file writes the list of entry dicts (#23)."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    out = str(tmp_path / "entries.json")
    result = CliRunner().invoke(
        main, ["entries", "-i", path, "--export", "json", "-o", out]
    )
    assert result.exit_code == 0
    data = json.loads(open(out, encoding="utf-8").read())
    assert len(data) == 3


def test_entries_export_empty(tmp_path, statement_xml):
    """An empty result exports a header-only CSV and an empty JSON list (#23)."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    csv_result = CliRunner().invoke(
        main, ["entries", "-i", path, "-r", "MD07", "--export", "csv"]
    )
    assert csv_result.exit_code == 0
    csv_lines = [line for line in csv_result.output.splitlines() if line]
    assert len(csv_lines) == 1  # header only
    json_result = CliRunner().invoke(
        main, ["entries", "-i", path, "-r", "MD07", "--export", "json"]
    )
    assert json_result.exit_code == 0
    assert json.loads(json_result.output) == []


def test_entries_export_single_entry_message(tmp_path, statement_xml):
    """The success message uses the singular for a single exported entry (#23)."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    out = str(tmp_path / "one.csv")
    result = CliRunner().invoke(
        main,
        ["entries", "-i", path, "-r", "AC04", "--export", "csv", "-o", out],
    )
    assert result.exit_code == 0
    assert "Exported 1 entry to" in result.output


def test_entries_format_table_default(tmp_path, statement_xml):
    """``--format table`` keeps the Rich table view (#9)."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(
        main, ["entries", "-i", path, "--format", "table"]
    )
    assert result.exit_code == 0
    assert "3 entries" in result.output


def test_entries_format_json(tmp_path, statement_xml):
    """``--format json`` emits the entries as a JSON array (#9)."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(
        main, ["entries", "-i", path, "--format", "json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 3
    assert data[0]["reference"] == "NTRY-0001"


def test_entries_format_json_filtered(tmp_path, statement_xml):
    """``--format json`` honours the entry filters (#9)."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(
        main, ["entries", "-i", path, "-r", "AC04", "--format", "json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1


def test_entries_format_json_bad_file():
    """``--format json`` reports a missing file and exits non-zero (#9)."""
    result = CliRunner().invoke(
        main, ["entries", "-i", "/no/such/file.xml", "--format", "json"]
    )
    assert result.exit_code == 1
    assert "Failed" in result.output


def test_parse_command(tmp_path, statement_xml):
    """The parse command prints JSON."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(main, ["parse", "-i", path])
    assert result.exit_code == 0
    assert "STMT-MSG-0001" in result.output


def test_parse_command_format_alias(tmp_path, statement_xml):
    """The parse command accepts ``--format json`` as a no-op alias (#9)."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(
        main, ["parse", "-i", path, "--format", "json"]
    )
    assert result.exit_code == 0
    assert "STMT-MSG-0001" in result.output


def test_parse_command_bad_file():
    """A missing input file exits non-zero."""
    result = CliRunner().invoke(main, ["parse", "-i", "/no/such/file.xml"])
    assert result.exit_code == 1
    assert "Parse failed" in result.output


def test_entries_command_bad_file():
    """The entries command exits non-zero on a missing file."""
    result = CliRunner().invoke(main, ["entries", "-i", "/no/such/file.xml"])
    assert result.exit_code == 1
    assert "Failed" in result.output


def test_version_flag():
    """The --version flag reports the version."""
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.0.6" in result.output


def test_reverse_command_to_stdout(tmp_path, statement_xml):
    """The reverse command prints the reversal to stdout by default."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(main, ["reverse", "-i", path, "-r", "AC04"])
    assert result.exit_code == 0
    assert "<RvslInd>true</RvslInd>" in result.output


def test_reverse_command_to_file(tmp_path, statement_xml):
    """The reverse command writes the reversal to a file."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    out = str(tmp_path / "out.xml")
    result = CliRunner().invoke(main, ["reverse", "-i", path, "-o", out])
    assert result.exit_code == 0
    assert "written to" in result.output
    assert "RvslInd" in open(out, encoding="utf-8").read()


def test_reverse_command_no_match(tmp_path, statement_xml):
    """A reason with no match exits non-zero."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(main, ["reverse", "-i", path, "-r", "MD07"])
    assert result.exit_code == 1
    assert "Reversal failed" in result.output


def test_reverse_command_format_table_default(tmp_path, statement_xml):
    """``--format table`` emits raw reversal XML (#9)."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(
        main, ["reverse", "-i", path, "-r", "AC04", "--format", "table"]
    )
    assert result.exit_code == 0
    assert "<RvslInd>true</RvslInd>" in result.output


def test_reverse_command_format_json(tmp_path, statement_xml):
    """``--format json`` wraps the reversal in a JSON envelope (#9)."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(
        main, ["reverse", "-i", path, "-r", "AC04", "--format", "json"]
    )
    assert result.exit_code == 0
    envelope = json.loads(result.output)
    assert envelope["message_type"] == "camt.053.001.14"
    assert envelope["reason_code"] == "AC04"
    assert "<RvslInd>true</RvslInd>" in envelope["xml"]


def test_reverse_command_format_json_to_file(tmp_path, statement_xml):
    """``--format json`` writes the envelope to a file (#9)."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    out = str(tmp_path / "rev.json")
    result = CliRunner().invoke(
        main,
        ["reverse", "-i", path, "-r", "AC04", "--format", "json", "-o", out],
    )
    assert result.exit_code == 0
    assert "written to" in result.output
    envelope = json.loads(open(out, encoding="utf-8").read())
    assert envelope["message_type"] == "camt.053.001.14"


def test_reverse_command_format_json_no_match(tmp_path, statement_xml):
    """``--format json`` keeps the non-zero exit on no match (#9)."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(
        main, ["reverse", "-i", path, "-r", "MD07", "--format", "json"]
    )
    assert result.exit_code == 1
    assert "Reversal failed" in result.output


def test_validate_id_command_valid():
    """A valid identifier exits zero."""
    result = CliRunner().invoke(
        main, ["validate-id", "-k", "bic", "-v", "NWBKGB2LXXX"]
    )
    assert result.exit_code == 0
    assert "Valid BIC" in result.output


def test_validate_id_command_invalid():
    """An invalid identifier exits non-zero."""
    result = CliRunner().invoke(
        main, ["validate-id", "-k", "iban", "-v", "NOPE"]
    )
    assert result.exit_code == 1
    assert "Invalid IBAN" in result.output


def test_reverse_reads_stdin(statement_xml):
    """A '-' input reads the statement from stdin."""
    result = CliRunner().invoke(
        main, ["reverse", "-i", "-", "-r", "AC04"], input=statement_xml
    )
    assert result.exit_code == 0
    assert "RvslInd" in result.output


# ─── check-cbpr-readiness (Nov 14-16 2026 cliff) ────────────────────────────

_CBPR_READY_V08 = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08">'
    "<BkToCstmrStmt><GrpHdr><MsgId>M</MsgId>"
    "<CreDtTm>2026-06-21T10:00:00</CreDtTm></GrpHdr>"
    "<Stmt><Id>S</Id>"
    "<Acct><Id><IBAN>DE89370400440532013000</IBAN></Id></Acct>"
    "</Stmt></BkToCstmrStmt></Document>"
)

_CBPR_BAD_UNSTRUCTURED = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08">'
    "<BkToCstmrStmt><GrpHdr><MsgId>M</MsgId>"
    "<CreDtTm>2026-06-21T10:00:00</CreDtTm></GrpHdr>"
    "<Stmt><Id>S</Id>"
    "<Acct><Id><IBAN>DE89370400440532013000</IBAN></Id></Acct>"
    "<Ntry><NtryDtls><TxDtls><RltdPties><Cdtr>"
    "<PstlAdr><AdrLine>Line only</AdrLine></PstlAdr>"
    "</Cdtr></RltdPties></TxDtls></NtryDtls></Ntry>"
    "</Stmt></BkToCstmrStmt></Document>"
)


def test_check_cbpr_readiness_clean_exit_zero(tmp_path):
    """A clean v08 statement returns exit 0 and prints the ready banner."""
    path = _write(tmp_path, "good.xml", _CBPR_READY_V08)
    result = CliRunner().invoke(main, ["check-cbpr-readiness", "-i", path])
    assert result.exit_code == 0
    assert "CBPR+ ready" in result.output
    assert "camt.053.001.08" in result.output
    assert "2026-11-16" in result.output


def test_check_cbpr_readiness_unstructured_exit_one(tmp_path):
    """Unstructured-only address fails: exit 1 + issue table printed."""
    path = _write(tmp_path, "bad.xml", _CBPR_BAD_UNSTRUCTURED)
    result = CliRunner().invoke(main, ["check-cbpr-readiness", "-i", path])
    assert result.exit_code == 1
    assert "NOT CBPR+ ready" in result.output
    # The rich-table truncates long codes; assert on the summary count
    # plus the issue table header instead.
    assert "1 unstructured-only" in result.output
    assert "issue(s)" in result.output


def test_check_cbpr_readiness_json_format(tmp_path):
    """--format json prints the full structured report."""
    path = _write(tmp_path, "good.xml", _CBPR_READY_V08)
    result = CliRunner().invoke(
        main, ["check-cbpr-readiness", "-i", path, "--format", "json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["cbpr_ready"] is True
    assert payload["cutover_date"] == "2026-11-16"
    assert "summary" in payload


def test_check_cbpr_readiness_bad_file_exits_one():
    """A missing input file exits non-zero with a clear error."""
    result = CliRunner().invoke(
        main, ["check-cbpr-readiness", "-i", "/no/such.xml"]
    )
    assert result.exit_code == 1
    assert "CBPR+ check failed" in result.output


def test_check_cbpr_readiness_reads_stdin():
    """A '-' input reads the payload from stdin."""
    result = CliRunner().invoke(
        main,
        ["check-cbpr-readiness", "-i", "-"],
        input=_CBPR_READY_V08,
    )
    assert result.exit_code == 0
    assert "CBPR+ ready" in result.output
