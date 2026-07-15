#!/usr/bin/env python3
"""Example: OpenTelemetry hooks with graceful no-op degradation.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/telemetry_hooks.py

``camt053.telemetry`` wraps the optional OpenTelemetry API (installed via
``pip install 'camt053[telemetry]'``). Without the extra, every hook is a
zero-overhead no-op, so library code can instrument unconditionally. This
script exercises the tracer / meter accessors, the ``trace_span`` and
``measure`` context managers, and the RED metric recorders.
"""

import time

from camt053.telemetry import (
    get_meter,
    get_tracer,
    is_telemetry_available,
    measure,
    record_duration,
    record_error,
    record_request,
    safe_span_attribute,
    trace_span,
)


def main() -> None:
    """Instrument a fake parse operation with spans and RED metrics."""
    available = is_telemetry_available()
    print(f"opentelemetry-api installed: {available}")
    print(f"tracer: {type(get_tracer()).__name__}")
    print(f"meter:  {type(get_meter()).__name__}")

    # 1. Tracing: a span around a unit of work. Span attributes must be
    #    OTel-safe primitives; safe_span_attribute coerces anything else.
    with trace_span("camt053.parse") as span:
        span.set_attribute("camt053.op", "parse")
        span.set_attribute(
            "camt053.entries", safe_span_attribute("entries", 3)
        )

    # 2. RED metrics, recorded individually...
    record_request("parse", status="ok")
    record_error("parse", kind="StatementParseError")
    record_duration("parse", 0.0421)
    print("recorded: 1 request, 1 error, 1 duration sample")

    # 3. ...or via the one-liner that times a block and records all three
    #    (request + duration always; error only when the block raises).
    started = time.perf_counter()
    with measure("reverse"):
        sum(range(10_000))  # stand-in for real work
    elapsed = time.perf_counter() - started
    print(f"measure('reverse') timed a {elapsed * 1000:.2f} ms block")

    print(
        "\nWithout the [telemetry] extra these calls cost nothing; "
        "with it, spans\nand RED counters flow to your configured "
        "OTLP exporter."
    )


if __name__ == "__main__":
    main()
