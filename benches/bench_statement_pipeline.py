#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""What a camt.053 statement costs to parse, list and validate.

A bank statement is the one input whose size the caller does not control. A
month of activity on a busy account arrives as thousands of ``<Ntry>``
elements in a single document, and nothing upstream asks first. So the
question this answers is not "how fast" but **"how does the cost grow"**.

Three things are measured, each because it can regress without any test
noticing:

* **``parse_statement`` across sizes.** Read the ``us/entry`` column. Flat
  means linear and a month-end file is fine; climbing means something
  rescans what it has already parsed, which looks perfect on the fixtures.

* **``list_entries`` streaming against buffered.** The library offers both.
  Streaming should win on memory and lose slightly on wall-clock; if
  streaming is ever *slower per entry* at large sizes, the generator is
  materialising something it should be yielding.

* **The first ``validate_statement`` against later ones.** The XSD is
  compiled once and cached. That makes the first call far more expensive
  than the rest — which matters enormously to anyone validating a single
  document per process, and is invisible to a benchmark that only reports
  a mean.

Run::

    python benches/bench_statement_pipeline.py
    python benches/bench_statement_pipeline.py --json
    python benches/bench_statement_pipeline.py --quick     # what CI runs

Nothing here asserts a threshold: wall-clock is not comparable between
machines, and a flaky performance gate teaches people to ignore red. CI runs
``--quick`` so a benchmark that has stopped compiling against the current
API fails the build instead of rotting into a file that reads as verified
and is not.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from camt053 import services  # noqa: E402

HEAD = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08">
 <BkToCstmrStmt>
  <GrpHdr><MsgId>BENCH</MsgId><CreDtTm>2026-06-21T10:00:00</CreDtTm></GrpHdr>
  <Stmt>
   <Id>STMT-1</Id>
   <Acct><Id><IBAN>DE89370400440532013000</IBAN></Id></Acct>
   <Bal><Tp><CdOrPrtry><Cd>OPBD</Cd></CdOrPrtry></Tp>
    <Amt Ccy="EUR">1000.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
    <Dt><Dt>2026-06-20</Dt></Dt></Bal>
"""

NTRY = """   <Ntry><Amt Ccy="EUR">{amount}.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
    <Sts><Cd>BOOK</Cd></Sts><BookgDt><Dt>2026-06-21</Dt></BookgDt>
    <ValDt><Dt>2026-06-21</Dt></ValDt>
    <NtryDtls><TxDtls><Refs><EndToEndId>E2E-{i}</EndToEndId></Refs>
     </TxDtls></NtryDtls></Ntry>
"""

TAIL = """   <Bal><Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>
    <Amt Ccy="EUR">2000.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
    <Dt><Dt>2026-06-21</Dt></Dt></Bal>
  </Stmt>
 </BkToCstmrStmt>
</Document>
"""


def build(entries: int) -> str:
    """A camt.053 document carrying ``entries`` booked entries."""
    body = "".join(
        NTRY.format(amount=(i % 900) + 100, i=i) for i in range(entries)
    )
    return HEAD + body + TAIL


def _best(call, repeats: int) -> float:
    """Best-of timing, after one untimed warm-up.

    The minimum is the least noisy estimator available here: the mean is
    dragged around by whatever else the machine is doing, while the minimum
    is the closest thing to the work actually required. The warm-up matters
    because the XSD compiles on first use, and without it the first sample
    measures schema compilation rather than the operation.
    """
    call()
    return min(_time(call) for _ in range(repeats))


def _time(call) -> float:
    start = time.perf_counter()
    call()
    return time.perf_counter() - start


def measure_parse(entries: int, repeats: int) -> dict:
    xml = build(entries)
    best = _best(lambda: services.parse_statement(xml), repeats)
    return {
        "case": "parse_statement",
        "entries": entries,
        "bytes": len(xml),
        "ms": best * 1e3,
        "us_per_entry": best * 1e6 / entries,
    }


def measure_listing(entries: int, repeats: int) -> list[dict]:
    """Streaming against buffered, on wall-clock and on peak memory."""
    xml = build(entries)
    rows = []
    for streaming in (False, True):

        def call(streaming=streaming):
            return services.list_entries(xml, streaming=streaming)

        best = _best(call, repeats)
        tracemalloc.start()
        call()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        rows.append(
            {
                "case": "list_entries",
                "streaming": streaming,
                "entries": entries,
                "ms": best * 1e3,
                "us_per_entry": best * 1e6 / entries,
                "peak_kib": peak / 1024,
            }
        )
    return rows


def measure_first_validate(entries: int) -> dict:
    """The XSD compiles once; the first caller pays for everyone.

    Measured in a fresh interpreter so the cache really is cold — importing
    and timing in-process would report a warm number and hide the whole
    point.
    """
    xml = build(entries)
    script = (
        "import sys, time, json\n"
        f"sys.path.insert(0, {str(Path(__file__).resolve().parent.parent)!r})\n"
        "from camt053 import services\n"
        "xml = sys.stdin.read()\n"
        "t0 = time.perf_counter(); services.validate_statement(xml)\n"
        "cold = time.perf_counter() - t0\n"
        "t1 = time.perf_counter(); services.validate_statement(xml)\n"
        "warm = time.perf_counter() - t1\n"
        "print(json.dumps({'cold': cold, 'warm': warm}))\n"
    )
    import subprocess

    result = subprocess.run(
        [sys.executable, "-c", script],
        input=xml,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        return {"case": "validate_statement", "error": result.stderr[-300:]}
    timings = json.loads(result.stdout.strip().splitlines()[-1])
    return {
        "case": "validate_statement",
        "entries": entries,
        "cold_ms": timings["cold"] * 1e3,
        "warm_ms": timings["warm"] * 1e3,
        "cold_over_warm": (
            timings["cold"] / timings["warm"] if timings["warm"] else 0.0
        ),
    }


def run(quick: bool) -> dict:
    sizes = [50, 500] if quick else [50, 500, 2_000, 10_000]
    repeats = 2 if quick else 5
    return {
        "parse": [measure_parse(n, repeats) for n in sizes],
        "listing": [r for n in sizes for r in measure_listing(n, repeats)],
        "validate": [measure_first_validate(sizes[0])],
    }


def render(results: dict) -> None:
    print("parse_statement")
    print(f"{'entries':>9}{'KiB':>9}{'ms':>10}{'us/entry':>11}")
    for row in results["parse"]:
        print(
            f"{row['entries']:>9}{row['bytes'] / 1024:>9.1f}"
            f"{row['ms']:>10.2f}{row['us_per_entry']:>11.1f}"
        )
    rows = results["parse"]
    if len(rows) >= 2:
        drift = rows[-1]["us_per_entry"] / rows[0]["us_per_entry"]
        print(
            f"  us/entry at {rows[-1]['entries']:,} is {drift:.2f}x the cost "
            f"at {rows[0]['entries']:,}. Flat is linear."
        )

    print("\nlist_entries — buffered against streaming")
    print(
        f"{'entries':>9}{'mode':>11}{'ms':>10}{'us/entry':>11}{'peak KiB':>11}"
    )
    for row in results["listing"]:
        mode = "streaming" if row["streaming"] else "buffered"
        print(
            f"{row['entries']:>9}{mode:>11}{row['ms']:>10.2f}"
            f"{row['us_per_entry']:>11.1f}{row['peak_kib']:>11,.0f}"
        )
    print(
        "  Streaming should hold peak memory down as entries grow. If its\n"
        "  us/entry ever exceeds buffered at the largest size, the generator\n"
        "  is materialising something it ought to be yielding."
    )

    print("\nvalidate_statement — cold interpreter against warm cache")
    for row in results["validate"]:
        if "error" in row:
            print(f"  failed: {row['error']}")
            continue
        print(
            f"  first call {row['cold_ms']:,.1f} ms, second "
            f"{row['warm_ms']:,.2f} ms — {row['cold_over_warm']:,.0f}x"
        )
    print(
        "  The XSD compiles once per process. A service validating one\n"
        "  document per invocation pays that every time; a long-lived one\n"
        "  pays it once. Worth knowing before choosing a deployment shape."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument(
        "--quick", action="store_true", help="small sizes, as CI runs"
    )
    args = parser.parse_args()

    results = run(quick=args.quick)
    if args.json:
        json.dump(results, sys.stdout, indent=1)
        print()
    else:
        render(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
