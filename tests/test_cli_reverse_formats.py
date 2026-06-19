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

"""Tests for the reverse CLI: version, pacs.004 format, and batch mode."""

import os

from click.testing import CliRunner

from camt053.cli.cli import main


def _write(tmp_path, name, content):
    """Write ``content`` to ``tmp_path/name`` and return the path."""
    path = tmp_path / name
    path.write_text(content)
    return str(path)


def test_reverse_out_version_08(tmp_path, statement_xml):
    """--out-version selects the camt.053.001.08 schema."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(
        main, ["reverse", "-i", path, "--out-version", "camt.053.001.08"]
    )
    assert result.exit_code == 0
    assert "camt.053.001.08" in result.output


def test_reverse_out_version_json_envelope(tmp_path, statement_xml):
    """The JSON envelope reports the selected output message type."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(
        main,
        [
            "reverse",
            "-i",
            path,
            "--out-version",
            "camt.053.001.08",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"message_type": "camt.053.001.08"' in result.output


def test_reverse_pacs004_format(tmp_path, statement_xml):
    """--output-format pacs004 emits a PaymentReturn document."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(
        main, ["reverse", "-i", path, "--output-format", "pacs004"]
    )
    assert result.exit_code == 0
    assert "<PmtRtr>" in result.output
    assert "<Cd>AC04</Cd>" in result.output


def test_reverse_pacs004_json_message_type(tmp_path, statement_xml):
    """The pacs.004 JSON envelope reports the pacs.004 message type."""
    path = _write(tmp_path, "stmt.xml", statement_xml)
    result = CliRunner().invoke(
        main,
        [
            "reverse",
            "-i",
            path,
            "--output-format",
            "pacs004",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert '"message_type": "pacs.004.001.11"' in result.output


def test_reverse_requires_input_or_batch():
    """reverse with neither --input nor --batch fails clearly."""
    result = CliRunner().invoke(main, ["reverse"])
    assert result.exit_code == 1
    assert "--input or --batch" in result.output


def test_reverse_batch_to_output_dir(tmp_path, statement_xml):
    """Batch mode writes a per-file reversal and reports a summary."""
    src = tmp_path / "in"
    src.mkdir()
    _write(src, "good.xml", statement_xml)
    _write(src, "bad.xml", "<broken")
    out = str(tmp_path / "out")
    result = CliRunner().invoke(
        main, ["reverse", "--batch", str(src), "-o", out]
    )
    assert result.exit_code == 1  # one bad file -> non-zero exit
    assert "1 succeeded, 1 failed of 2." in result.output
    assert os.listdir(out) == ["good.reversal.xml"]


def test_reverse_batch_all_good_no_output_dir(tmp_path, statement_xml):
    """Batch mode with no -o just reports per-file results."""
    src = tmp_path / "in"
    src.mkdir()
    _write(src, "good.xml", statement_xml)
    result = CliRunner().invoke(main, ["reverse", "--batch", str(src)])
    assert result.exit_code == 0
    assert "1 succeeded, 0 failed of 1." in result.output
