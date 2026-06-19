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

"""pytest-benchmark performance suite + regression guard (#11).

These benchmarks measure the two hot paths of the library on a representative
multi-entry statement:

* parsing a camt.053 document into the typed model, and
* generating a validated reversing-entry document from it.

They are marked ``perf`` and excluded from the coverage gate (run with
``--no-cov``); the CI ``performance`` job runs them on their own and compares
against a stored baseline so a regression beyond the configured threshold
fails the build. Run locally with::

    pytest tests/test_benchmarks.py -m perf --no-cov --benchmark-only
"""

from __future__ import annotations

import pytest

from camt053.parse.statement_parser import parse_statement
from camt053.xml.generate_xml import generate_reversal_for_statement


def _representative_statement_xml(entry_count: int = 50) -> str:
    """Build a representative camt.053 statement with many booked entries.

    Half the entries carry an AC04 return reason (so they are reversible),
    giving the parser and reversal generator a realistic workload.
    """
    entries = []
    for i in range(entry_count):
        returnable = i % 2 == 0
        rtr = (
            "<RtrInf><Rsn><Cd>AC04</Cd></Rsn>"
            "<AddtlInf>Beneficiary account closed</AddtlInf></RtrInf>"
            if returnable
            else ""
        )
        entries.append(
            "<Ntry>"
            f"<NtryRef>NTRY-{i:04d}</NtryRef>"
            f'<Amt Ccy="EUR">{(i + 1) * 10}.00</Amt>'
            "<CdtDbtInd>CRDT</CdtDbtInd>"
            "<Sts><Cd>BOOK</Cd></Sts>"
            "<BookgDt><Dt>2026-06-15</Dt></BookgDt>"
            "<ValDt><Dt>2026-06-15</Dt></ValDt>"
            "<NtryDtls><TxDtls>"
            f"<Refs><EndToEndId>E2E-{i:04d}</EndToEndId>"
            f"<TxId>TX-{i:04d}</TxId></Refs>"
            f"{rtr}"
            "<RltdPties>"
            "<Dbtr><Nm>Globex SA</Nm></Dbtr>"
            "<DbtrAcct><Id><IBAN>DE89370400440532013000</IBAN></Id>"
            "</DbtrAcct>"
            "</RltdPties>"
            "</TxDtls></NtryDtls>"
            "</Ntry>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">'
        "<BkToCstmrStmt>"
        "<GrpHdr><MsgId>STMT-MSG-PERF</MsgId>"
        "<CreDtTm>2026-06-15T08:00:00</CreDtTm></GrpHdr>"
        "<Stmt><Id>STMT-PERF</Id><ElctrncSeqNb>1</ElctrncSeqNb>"
        "<CreDtTm>2026-06-15T08:00:00</CreDtTm>"
        "<Acct><Id><IBAN>GB29NWBK60161331926819</IBAN></Id>"
        "<Ccy>EUR</Ccy><Ownr><Nm>Acme Treasury Ltd</Nm></Ownr>"
        "<Svcr><FinInstnId><BICFI>NWBKGB2LXXX</BICFI></FinInstnId></Svcr>"
        "</Acct>"
        "<Bal><Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>"
        '<Amt Ccy="EUR">10000.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>'
        "<Dt><Dt>2026-06-15</Dt></Dt></Bal>"
        f"{''.join(entries)}"
        "</Stmt></BkToCstmrStmt></Document>"
    )


@pytest.fixture(scope="module")
def representative_xml() -> str:
    """A representative 50-entry camt.053 statement for benchmarking."""
    return _representative_statement_xml(50)


@pytest.mark.perf
def test_benchmark_parse_statement(benchmark, representative_xml) -> None:
    """Benchmark parsing a representative multi-entry statement."""
    stmt = benchmark(parse_statement, representative_xml)
    assert len(stmt.entries) == 50


@pytest.mark.perf
def test_benchmark_generate_reversal(benchmark, representative_xml) -> None:
    """Benchmark reversal generation (parse done once, outside the timer)."""
    stmt = parse_statement(representative_xml)
    xml = benchmark(generate_reversal_for_statement, stmt, "AC04")
    assert "<RvslInd>true</RvslInd>" in xml


@pytest.mark.perf
def test_benchmark_parse_and_reverse(benchmark, representative_xml) -> None:
    """Benchmark the full parse + reversal-generation round."""

    def _parse_and_reverse() -> str:
        stmt = parse_statement(representative_xml)
        return generate_reversal_for_statement(stmt, "AC04")

    xml = benchmark(_parse_and_reverse)
    assert "<RvslInd>true</RvslInd>" in xml
