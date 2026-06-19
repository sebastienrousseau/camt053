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

"""Tests for cached XSD/Jinja artefacts (#27) and streaming parse (#10)."""

import os

import pytest

from camt053 import services
from camt053.constants import REVERSAL_MESSAGE_TYPE, TEMPLATES_DIR
from camt053.exceptions import StatementParseError
from camt053.parse.statement_parser import (
    iter_statement_entries,
    parse_document,
)
from camt053.xml import template_env
from camt053.xml.validate_via_xsd import _get_cached_schema

XSD = str(
    TEMPLATES_DIR / REVERSAL_MESSAGE_TYPE / f"{REVERSAL_MESSAGE_TYPE}.xsd"
)


# ── #27 caching ──────────────────────────────────────────────────────


def test_cached_schema_reused():
    """Compiling the same XSD twice returns the identical cached object."""
    _get_cached_schema.cache_clear()
    first = _get_cached_schema(XSD)
    second = _get_cached_schema(XSD)
    assert first is second
    assert _get_cached_schema.cache_info().hits >= 1


def test_cached_template_reused():
    """The same template is compiled once and reused across calls."""
    template_env.get_template.cache_clear()
    template_env._get_environment.cache_clear()
    tdir = str(TEMPLATES_DIR / REVERSAL_MESSAGE_TYPE)
    first = template_env.get_template(tdir, "template.xml")
    second = template_env.get_template(tdir, "template.xml")
    assert first is second
    assert template_env.get_template.cache_info().hits >= 1


def test_cached_environment_shared_across_templates():
    """Two templates in one directory share one cached environment."""
    template_env.get_template.cache_clear()
    template_env._get_environment.cache_clear()
    tdir = str(TEMPLATES_DIR / REVERSAL_MESSAGE_TYPE)
    reversal = template_env.get_template(tdir, "template.xml")
    statement = template_env.get_template(tdir, "statement.xml")
    assert reversal.environment is statement.environment


def test_cached_template_round_trips(reversal_record):
    """Reusing the cached template still renders valid output."""
    first = services.generate([reversal_record])
    second = services.generate([reversal_record])
    assert first == second
    assert os.path.exists(XSD)


# ── #10 streaming parse ──────────────────────────────────────────────


def test_stream_matches_whole_tree(statement_xml):
    """Streaming yields exactly the whole-tree entries, in order."""
    streamed = [e.to_dict() for e in iter_statement_entries(statement_xml)]
    whole = [e.to_dict() for e in parse_document(statement_xml).all_entries()]
    assert streamed == whole


def test_service_list_entries_streaming_matches(statement_xml):
    """services.list_entries(streaming=True) == the default path."""
    default = services.list_entries(statement_xml)
    streamed = services.list_entries(statement_xml, streaming=True)
    assert streamed == default


def test_service_iter_entries_matches(statement_xml):
    """services.iter_entries yields the same dicts as list_entries."""
    streamed = list(services.iter_entries(statement_xml))
    assert streamed == services.list_entries(statement_xml)


def test_stream_empty_input_raises():
    """An empty document raises before any entry is yielded."""
    with pytest.raises(StatementParseError, match="empty"):
        list(iter_statement_entries("   "))


def test_stream_malformed_raises_after_partial():
    """A truncated document raises a malformed error mid-stream."""
    truncated = (
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">'
        "<BkToCstmrStmt><Stmt>"
        "<Ntry><NtryRef>A</NtryRef></Ntry>"
        "<Ntry><NtryRef>B</NtryRef>"  # unclosed - truncated stream
    )
    seen = []
    with pytest.raises(StatementParseError, match="Malformed"):
        for entry in iter_statement_entries(truncated):
            seen.append(entry.reference)
    assert seen == ["A"]
