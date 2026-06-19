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

"""Tests for batch reversal generation across many statement files."""

import os

from camt053 import services


def _write(directory, name, content):
    """Write ``content`` to ``directory/name`` and return the path."""
    path = directory / name
    path.write_text(content)
    return str(path)


def test_batch_directory_mixed_good_and_bad(tmp_path, statement_xml):
    """A directory batch isolates failures from the good files."""
    _write(tmp_path, "good1.xml", statement_xml)
    _write(tmp_path, "good2.xml", statement_xml)
    _write(tmp_path, "broken.xml", "<not-valid-xml")
    _write(
        tmp_path,
        "no_reason.xml",
        statement_xml.replace("AC04", "ZZ99").replace("AC06", "ZZ98"),
    )

    summary = services.generate_batch(str(tmp_path), reason_code="AC04")

    assert summary["total"] == 4
    assert summary["succeeded"] == 2
    assert summary["failed"] == 2
    by_name = {
        os.path.basename(result["path"]): result
        for result in summary["results"]
    }
    assert by_name["good1.xml"]["ok"] is True
    assert by_name["good1.xml"]["xml"] is not None
    assert by_name["good1.xml"]["error"] is None
    assert by_name["broken.xml"]["ok"] is False
    assert by_name["broken.xml"]["xml"] is None
    assert by_name["broken.xml"]["error"]
    assert by_name["no_reason.xml"]["ok"] is False


def test_batch_list_of_paths(tmp_path, statement_xml):
    """A list of explicit file paths is processed in order."""
    a = _write(tmp_path, "a.xml", statement_xml)
    b = _write(tmp_path, "b.xml", statement_xml)
    summary = services.generate_batch([a, b])
    assert [r["path"] for r in summary["results"]] == [a, b]
    assert summary["succeeded"] == 2


def test_batch_glob_pattern(tmp_path, statement_xml):
    """A glob pattern expands to its matching files."""
    _write(tmp_path, "stmt-1.xml", statement_xml)
    _write(tmp_path, "stmt-2.xml", statement_xml)
    _write(tmp_path, "other.txt", "ignored")
    summary = services.generate_batch(str(tmp_path / "stmt-*.xml"))
    assert summary["total"] == 2
    assert summary["succeeded"] == 2


def test_batch_missing_path_is_per_file_error(tmp_path):
    """A path matching nothing surfaces as a per-file not-found error."""
    missing = str(tmp_path / "absent.xml")
    summary = services.generate_batch([missing])
    assert summary["total"] == 1
    assert summary["failed"] == 1
    assert summary["results"][0]["path"] == missing
    assert summary["results"][0]["ok"] is False


def test_batch_deduplicates_paths(tmp_path, statement_xml):
    """The same file referenced twice is processed once."""
    path = _write(tmp_path, "dup.xml", statement_xml)
    summary = services.generate_batch([path, path])
    assert summary["total"] == 1


def test_batch_pacs004_and_version(tmp_path, statement_xml):
    """Batch honours the output format and version selection."""
    _write(tmp_path, "s.xml", statement_xml)
    summary = services.generate_batch(
        str(tmp_path),
        output_format="pacs004",
        version="camt.053.001.08",
    )
    assert summary["succeeded"] == 1
    assert "<PmtRtr>" in summary["results"][0]["xml"]
