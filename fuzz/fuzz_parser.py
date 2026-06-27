#!/usr/bin/env python3
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

"""Atheris fuzz harness for the camt053 statement-processing entry points.

Every function exercised here consumes *untrusted* statement text (raw
camt.05x XML) straight from an external party -- a bank file, an upload, an
API request body. The harness feeds them arbitrary bytes (malformed XML,
truncated documents, control characters, hostile entity tricks, ...) and
asserts they only ever fail in *documented* ways.

The library documents that these entry points raise
``camt053.exceptions.Camt053Error`` (and its subclasses), plus the stdlib
``ValueError`` (which covers ``XmlSecurityError`` / ``UnsupportedSchemaError``)
and ``json.JSONDecodeError``. Those are caught here so they do not register as
findings. ANY OTHER exception is undocumented -- a real bug -- and is allowed
to propagate so the fuzzer surfaces it. Where a tolerant variant exists
(``parse_statement_lenient``) it is preferred.

Run locally::

    pip install atheris
    python fuzz/fuzz_parser.py -atheris_runs=100000

In CI this target is built and run by ClusterFuzzLite (see ``.clusterfuzzlite``).
"""

import json
import sys

import atheris

with atheris.instrument_imports():
    from camt053 import schema_version, services
    from camt053.exceptions import Camt053Error

# Exceptions the camt053 API documents for untrusted-input entry points.
# XmlSecurityError and UnsupportedSchemaError both subclass ValueError, so the
# ValueError entry covers them too. A crash outside this set is a real bug.
_DOCUMENTED = (Camt053Error, ValueError, json.JSONDecodeError)


def test_one_input(data: bytes) -> None:
    """Drive the untrusted-input entry points with fuzzed statement text."""
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(sys.maxsize)

    # Security gate -- must reject hostile payloads, never crash unexpectedly.
    try:
        services.guard_xml(text)
    except _DOCUMENTED:
        pass

    # Schema-version detection on arbitrary text.
    try:
        schema_version.detect_schema_version(text)
    except _DOCUMENTED:
        pass

    # Full parse pipelines -- strict, lenient, and the derived helpers.
    try:
        services.parse_statement(text)
    except _DOCUMENTED:
        pass

    try:
        services.parse_statement_lenient(text)
    except _DOCUMENTED:
        pass

    try:
        services.list_entries(text)
    except _DOCUMENTED:
        pass

    try:
        services.compute_dedupe_keys(text)
    except _DOCUMENTED:
        pass

    # XSD + profile validation pipelines.
    try:
        services.validate_statement(text)
    except _DOCUMENTED:
        pass

    try:
        services.validate_against_profile(text)
    except _DOCUMENTED:
        pass

    # Round-trip parse -> re-serialise.
    try:
        services.serialize_statement(text)
    except _DOCUMENTED:
        pass


def main() -> None:
    """Wire the harness into the libFuzzer driver and start fuzzing."""
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
