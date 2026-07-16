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

"""Load / stress test suite (marker ``stress``).

Complements the ``perf`` micro-benchmarks in ``test_benchmarks.py`` with
sustained-load, large-document, and soak scenarios:

* **Concurrent parsing** -- a 32-worker thread pool hammers
  :func:`~camt053.parse.statement_parser.parse_statement` with several
  hundred parses of a representative multi-entry statement and asserts
  zero errors plus a generous p95 latency ceiling.
* **Large documents** -- a synthesized statement with several thousand
  entries must parse and generate its reversal within a generous
  wall-clock bound, and the streaming ``iterparse`` path
  (:func:`~camt053.parse.statement_parser.iter_statement_entries`, the
  engine behind ``services.list_entries(..., streaming=True)``) must
  keep peak memory bounded.
* **Soak** -- repeated parse/serialize round-trips must not leak memory.

Like ``perf``, the ``stress`` marker is excluded from the default
coverage-gated run (see ``addopts`` in ``pyproject.toml``); the CI
``performance`` job runs it on its own. All bounds carry a deliberately
generous cushion so shared CI runners do not flake the build -- a
failure here signals a real regression, not runner noise. Run locally
with::

    pytest tests/test_stress.py -m stress --no-cov
"""

from __future__ import annotations

import gc
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor

import pytest

from camt053 import services
from camt053.parse.statement_parser import (
    iter_statement_entries,
    parse_statement,
)
from camt053.xml.generate_xml import generate_reversal_for_statement
from tests.test_benchmarks import _representative_statement_xml

# ─── Tunables ────────────────────────────────────────────────────────────────
#
# Every bound below is generous by design: locally the suite runs in a
# few seconds, and even a shared GitHub Actions runner running ~10×
# slower stays comfortably inside the limits. Tighten them only with a
# matching cushion analysis (see the ``_PERF_MARGIN`` discussion in
# ``test_benchmarks.py``).

#: Thread-pool width for the sustained-concurrency scenario.
_CONCURRENCY_WORKERS = 32

#: Total parses submitted to the pool ("several hundred").
_CONCURRENCY_PARSES = 400

#: Generous per-parse p95 latency ceiling under 32-way contention.
#: Local p95 is ~2-30 ms; CI runners are ~10× slower; 2 s ≈ 60×+ cushion.
_CONCURRENCY_P95_CEILING_S = 2.0

#: Entry count for the large-document scenario ("several thousand").
_LARGE_DOC_ENTRIES = 4000

#: Wall-clock bound for parse + reversal of the large document.
#: Locally ~1 s; 30 s absorbs a 10×-slow runner three times over.
_LARGE_DOC_WALL_CLOCK_S = 30.0

#: Peak tracemalloc cap for streaming entry iteration over the large
#: document. Streaming holds one entry at a time (~tens of kB); the
#: 32 MiB cap is far below full-document materialisation yet impossible
#: to trip without a real unbounded-buffering regression.
_STREAMING_PEAK_CAP_BYTES = 32 * 1024 * 1024

#: Entry count for the soak workload. Kept small because the whole
#: soak runs under tracemalloc, which multiplies the per-round-trip
#: cost ~8-10x; a leak shows up regardless of the document size.
_SOAK_DOC_ENTRIES = 10

#: Warm-up round-trips before the soak baseline (populates caches,
#: template compilation, and interned schema state).
_SOAK_WARMUP_ITERATIONS = 10

#: Measured soak round-trips after the baseline snapshot.
_SOAK_ITERATIONS = 60

#: Allowed net traced-memory growth across the measured soak window.
#: A leak of even 1 kB per round-trip would show as ~80 kB; the 8 MiB
#: cap only trips on genuinely unbounded growth.
_SOAK_GROWTH_CAP_BYTES = 8 * 1024 * 1024


@pytest.fixture(scope="module")
def representative_xml() -> str:
    """A representative 50-entry camt.053 statement (shared workload)."""
    return _representative_statement_xml(50)


@pytest.fixture(scope="module")
def large_xml() -> str:
    """A large synthesized statement with several thousand entries."""
    return _representative_statement_xml(_LARGE_DOC_ENTRIES)


@pytest.fixture(scope="module")
def soak_xml() -> str:
    """A small statement for the tracemalloc-instrumented soak loop."""
    return _representative_statement_xml(_SOAK_DOC_ENTRIES)


# ─── (a) Sustained concurrent parsing ────────────────────────────────────────


@pytest.mark.stress
def test_sustained_concurrent_parsing(representative_xml: str) -> None:
    """32 workers x several hundred parses: zero errors, sane p95.

    Submits ``_CONCURRENCY_PARSES`` parses of the representative
    50-entry statement to a ``ThreadPoolExecutor`` with
    ``_CONCURRENCY_WORKERS`` workers, records per-call latency, and
    asserts that every parse succeeded with the expected entry count
    and that the p95 latency stays under the (generous) ceiling.
    """
    errors: list[Exception] = []
    latencies: list[float] = []

    def _one_parse() -> None:
        start = time.perf_counter()
        try:
            stmt = parse_statement(representative_xml)
            assert len(stmt.entries) == 50
        except Exception as exc:
            errors.append(exc)
        finally:
            latencies.append(time.perf_counter() - start)

    with ThreadPoolExecutor(max_workers=_CONCURRENCY_WORKERS) as pool:
        futures = [pool.submit(_one_parse) for _ in range(_CONCURRENCY_PARSES)]
        for future in futures:
            future.result()

    assert not errors, (
        f"{len(errors)} of {_CONCURRENCY_PARSES} concurrent parses "
        f"failed; first error: {errors[0]!r}"
    )
    assert len(latencies) == _CONCURRENCY_PARSES

    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95) - 1]
    p50 = latencies[len(latencies) // 2]
    print(
        f"\nconcurrent parse ({_CONCURRENCY_WORKERS} workers, "
        f"{_CONCURRENCY_PARSES} parses): "
        f"p50 {p50 * 1000:.1f} ms, p95 {p95 * 1000:.1f} ms "
        f"(ceiling {_CONCURRENCY_P95_CEILING_S * 1000:.0f} ms)"
    )
    assert p95 <= _CONCURRENCY_P95_CEILING_S, (
        f"p95 parse latency {p95 * 1000:.0f} ms exceeded the "
        f"{_CONCURRENCY_P95_CEILING_S * 1000:.0f} ms ceiling under "
        f"{_CONCURRENCY_WORKERS}-way concurrency. The ceiling carries a "
        f">60x cushion, so this is a real regression, not runner noise."
    )


# ─── (b) Large-document handling ─────────────────────────────────────────────


@pytest.mark.stress
def test_large_document_parse_and_reversal(large_xml: str) -> None:
    """A several-thousand-entry statement parses + reverses in bounds.

    Parses the ``_LARGE_DOC_ENTRIES``-entry document and generates the
    AC04 reversal for it, asserting correctness of the output and a
    generous wall-clock bound for the combined operation.
    """
    start = time.perf_counter()
    stmt = parse_statement(large_xml)
    reversal = generate_reversal_for_statement(stmt, "AC04")
    elapsed = time.perf_counter() - start

    assert len(stmt.entries) == _LARGE_DOC_ENTRIES
    assert "<RvslInd>true</RvslInd>" in reversal
    print(
        f"\nlarge document ({_LARGE_DOC_ENTRIES} entries, "
        f"{len(large_xml.encode('utf-8')) / 1_000_000:.1f} MB): "
        f"parse + reversal in {elapsed:.2f} s "
        f"(bound {_LARGE_DOC_WALL_CLOCK_S:.0f} s)"
    )
    assert elapsed <= _LARGE_DOC_WALL_CLOCK_S, (
        f"Parse + reversal of a {_LARGE_DOC_ENTRIES}-entry statement "
        f"took {elapsed:.1f} s, over the {_LARGE_DOC_WALL_CLOCK_S:.0f} s "
        f"bound (locally ~1 s; the bound absorbs a 10x-slow runner "
        f"three times over)."
    )


@pytest.mark.stress
def test_streaming_iteration_keeps_memory_bounded(large_xml: str) -> None:
    """Streaming entry iteration stays under the tracemalloc peak cap.

    Walks the large document through the ``iterparse``-backed
    :func:`iter_statement_entries` path (the engine behind
    ``services.list_entries(..., streaming=True)`` and
    ``services.iter_entries``) without materialising the entries, and
    asserts the tracemalloc peak stays under ``_STREAMING_PEAK_CAP_BYTES``
    -- i.e. memory is bounded by a single entry, not the document.
    """
    gc.collect()
    tracemalloc.start()
    try:
        count = 0
        for entry in iter_statement_entries(large_xml):
            # Touch the entry so parsing is not elided, then drop it.
            assert entry.reference is not None
            count += 1
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert count == _LARGE_DOC_ENTRIES
    print(
        f"\nstreaming iteration ({_LARGE_DOC_ENTRIES} entries): "
        f"tracemalloc peak {peak / 1024 / 1024:.2f} MiB "
        f"(cap {_STREAMING_PEAK_CAP_BYTES / 1024 / 1024:.0f} MiB)"
    )
    assert peak <= _STREAMING_PEAK_CAP_BYTES, (
        f"Streaming iteration peaked at {peak / 1024 / 1024:.1f} MiB, "
        f"over the {_STREAMING_PEAK_CAP_BYTES / 1024 / 1024:.0f} MiB "
        f"cap -- the iterparse path is buffering instead of streaming."
    )


# ─── (c) Soak: repeated round-trips, no unbounded growth ─────────────────────


@pytest.mark.stress
def test_soak_round_trips_do_not_grow_memory(soak_xml: str) -> None:
    """Repeated parse/serialize round-trips show no unbounded growth.

    Runs ``_SOAK_WARMUP_ITERATIONS`` warm-up round-trips (so template
    compilation, schema caches, and interning settle), snapshots traced
    memory, then runs ``_SOAK_ITERATIONS`` more
    ``services.serialize_statement`` round-trips (each one is a full
    parse + re-serialise + XSD validation) and asserts net traced-memory
    growth stays under ``_SOAK_GROWTH_CAP_BYTES``.
    """

    def _round_trip() -> None:
        out = services.serialize_statement(soak_xml)
        assert "<Ntry>" in out

    gc.collect()
    tracemalloc.start()
    try:
        for _ in range(_SOAK_WARMUP_ITERATIONS):
            _round_trip()
        gc.collect()
        baseline, _ = tracemalloc.get_traced_memory()

        for _ in range(_SOAK_ITERATIONS):
            _round_trip()
        gc.collect()
        final, _ = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    growth = final - baseline
    print(
        f"\nsoak ({_SOAK_ITERATIONS} round-trips after "
        f"{_SOAK_WARMUP_ITERATIONS} warm-up): traced memory "
        f"{baseline / 1024:.0f} KiB -> {final / 1024:.0f} KiB, "
        f"growth {growth / 1024:+.0f} KiB "
        f"(cap {_SOAK_GROWTH_CAP_BYTES / 1024:.0f} KiB)"
    )
    assert growth <= _SOAK_GROWTH_CAP_BYTES, (
        f"Traced memory grew by {growth / 1024 / 1024:.2f} MiB over "
        f"{_SOAK_ITERATIONS} parse/serialize round-trips (cap "
        f"{_SOAK_GROWTH_CAP_BYTES / 1024 / 1024:.0f} MiB) -- a leak of "
        f"~{growth / _SOAK_ITERATIONS / 1024:.1f} KiB per round-trip."
    )
