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

"""Tests for B7: OpenTelemetry tracing + RED metrics.

The telemetry module is designed to work both with and without
OpenTelemetry installed. The CI environment has it (added as a dev
dep so the wired-in spans + counters can be exercised) but the
runtime install only pulls it in when the ``[telemetry]`` extra is
requested. These tests cover both code paths.
"""

from __future__ import annotations

import pytest

from camt053 import services, telemetry


@pytest.fixture(autouse=True)
def _reset_metric_globals():
    """Reset the module-level metric instruments between tests.

    The lazy-cached counters / histogram are global so a tracer-
    swap in one test should not leak into the next.
    """
    telemetry._REQUESTS_COUNTER = None
    telemetry._ERRORS_COUNTER = None
    telemetry._DURATION_HISTOGRAM = None
    yield


def test_module_exposes_canonical_span_names():
    """The three canonical span names are stable, dotted, lowercase."""
    assert telemetry.SPAN_PARSE == "camt053.parse"
    assert telemetry.SPAN_VALIDATE == "camt053.validate"
    assert telemetry.SPAN_REVERSE == "camt053.reverse"


def test_module_exposes_canonical_metric_names():
    """The three canonical metric names follow Prometheus naming."""
    assert telemetry.METRIC_REQUESTS == "camt053_requests_total"
    assert telemetry.METRIC_ERRORS == "camt053_errors_total"
    assert telemetry.METRIC_DURATION == "camt053_duration_seconds"


def test_is_telemetry_available_returns_bool():
    """``is_telemetry_available`` returns a real bool, not an object."""
    result = telemetry.is_telemetry_available()
    assert isinstance(result, bool)


def test_get_tracer_returns_an_object():
    """``get_tracer`` always returns a tracer-like object (real or no-op)."""
    tracer = telemetry.get_tracer()
    assert tracer is not None
    # Has the one method the camt053 service facade calls.
    assert hasattr(tracer, "start_as_current_span")


def test_get_meter_returns_an_object():
    """``get_meter`` always returns a meter-like object (real or no-op)."""
    meter = telemetry.get_meter()
    assert meter is not None
    assert hasattr(meter, "create_counter")
    assert hasattr(meter, "create_histogram")


def test_trace_span_context_manager_yields_span_object():
    """``trace_span`` yields an object that exposes the span API."""
    with telemetry.trace_span("test.span") as span:
        assert hasattr(span, "set_attribute")
        assert hasattr(span, "set_status")
        assert hasattr(span, "record_exception")
        # No-op on either path:
        span.set_attribute("test.key", "test.value")


def test_record_request_does_not_raise():
    """Recording a request is a side-effect-free no-op when OTel is absent."""
    telemetry.record_request("test_op")
    telemetry.record_request("test_op", "error")


def test_record_error_does_not_raise():
    """Recording an error is a side-effect-free no-op when OTel is absent."""
    telemetry.record_error("test_op", "test_kind")


def test_record_duration_does_not_raise():
    """Recording a duration is a side-effect-free no-op when OTel is absent."""
    telemetry.record_duration("test_op", 0.123)


def test_measure_returns_span_on_clean_exit():
    """``measure`` yields a span object the caller can attribute."""
    with telemetry.measure("test_op") as span:
        span.set_attribute("test.key", "test.value")


def test_measure_re_raises_exceptions_unchanged():
    """``measure`` records error metrics but re-raises the exception."""

    class _Boom(RuntimeError):
        """Sentinel exception class for the error-path test."""

    with pytest.raises(_Boom, match="boom"):
        with telemetry.measure("test_op"):
            raise _Boom("boom")


def test_safe_span_attribute_redacts_iban_keys():
    """``safe_span_attribute`` applies the same redaction rules as logs."""
    redacted = telemetry.safe_span_attribute("iban", "GB29NWBK60161331926819")
    # The redact_iban helper masks all but the last 4 characters.
    assert redacted != "GB29NWBK60161331926819"
    assert redacted.endswith("6819")


def test_safe_span_attribute_passes_neutral_keys_through():
    """Keys that are not flagged as sensitive pass through unchanged."""
    assert telemetry.safe_span_attribute("op", "parse") == "parse"


# ─── services-facade wiring ─────────────────────────────────────────────────


_CLEAN_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08">'
    "<BkToCstmrStmt>"
    "<GrpHdr><MsgId>M</MsgId>"
    "<CreDtTm>2026-06-21T10:00:00</CreDtTm></GrpHdr>"
    "<Stmt><Id>S</Id>"
    "<Acct><Id><IBAN>DE89370400440532013000</IBAN></Id></Acct>"
    "</Stmt></BkToCstmrStmt></Document>"
)


def test_services_parse_statement_runs_without_telemetry_errors():
    """parse_statement runs cleanly with telemetry wired in."""
    result = services.parse_statement(_CLEAN_XML)
    assert result["msg_id"] == "M"


def test_services_parse_statement_re_raises_underlying_exceptions():
    """The telemetry wrapper doesn't swallow exceptions on error paths."""
    from camt053.exceptions import StatementParseError

    with pytest.raises(StatementParseError):
        services.parse_statement("<not-a-document/>")


def test_services_exports_telemetry_module():
    """The telemetry module is reachable via the services facade."""
    assert services.telemetry is telemetry
