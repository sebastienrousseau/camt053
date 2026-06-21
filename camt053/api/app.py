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

"""FastAPI REST API for Camt053.

Exposes the shared :mod:`camt053.services` facade over HTTP: list message types
and return reasons, validate records and identifiers, parse statements, and
generate reversing entries. The reversal endpoint returns the validated
camt.053 document as ``application/xml``.
"""

import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)

from camt053 import services
from camt053.api.models import (
    HealthResponse,
    ReversalRequest,
    StatementRequest,
    ValidateRecordsRequest,
)
from camt053.constants import VERSION
from camt053.exceptions import Camt053Error
from camt053.security.xml_guard import (
    DEFAULT_MAX_XML_BYTES,
    XmlSecurityError,
)


def _max_body_bytes() -> int:
    """Return the configured maximum request-body size in bytes.

    Reads ``CAMT053_MAX_BODY_BYTES`` (a positive integer) and falls back to
    :data:`~camt053.security.xml_guard.DEFAULT_MAX_XML_BYTES` when the variable
    is unset, empty, or not a positive integer.
    """
    raw = os.environ.get("CAMT053_MAX_BODY_BYTES", "").strip()
    if not raw:
        return DEFAULT_MAX_XML_BYTES
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_XML_BYTES
    return value if value > 0 else DEFAULT_MAX_XML_BYTES


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose body exceeds the configured maximum size.

    Enforces the limit defence-in-depth: a declared ``Content-Length`` over
    the limit is rejected up front, and the streamed body is measured so a
    chunked / understated ``Content-Length`` cannot smuggle an oversized
    payload past the check. Oversized requests get a structured HTTP ``413``.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Reject oversized bodies, otherwise defer to the next handler."""
        max_bytes = _max_body_bytes()
        declared = request.headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) > max_bytes:
                    return _too_large_response(max_bytes)
            except ValueError:
                # A non-integer Content-Length is ignored here; the streamed
                # body below is measured directly, which rejects oversized
                # payloads regardless of a malformed declared length.
                pass
        body = await request.body()
        if len(body) > max_bytes:
            return _too_large_response(max_bytes)
        return await call_next(request)


def _too_large_response(max_bytes: int) -> JSONResponse:
    """Build the structured ``413 Payload Too Large`` response."""
    return JSONResponse(
        status_code=413,
        content={
            "error": "payload_too_large",
            "detail": (f"Request body exceeds the {max_bytes}-byte limit."),
        },
    )


app = FastAPI(
    title="Camt053 API",
    description=(
        "Read ISO 20022 camt Bank-to-Customer Statements and generate "
        "validated reversing entries."
    ),
    version=VERSION,
)
app.add_middleware(BodySizeLimitMiddleware)


@app.exception_handler(XmlSecurityError)
async def _xml_security_handler(
    request: Request, exc: XmlSecurityError
) -> JSONResponse:
    """Map an XML security violation onto a structured 4xx response.

    Oversized payloads yield ``413``; a forbidden DOCTYPE / entity declaration
    yields ``400``. The body is a structured error object, never a stack
    trace, so malicious input cannot surface internal detail.
    """
    status_code = 413 if exc.reason == "too_large" else 400
    return JSONResponse(
        status_code=status_code,
        content={"error": exc.reason, "detail": str(exc)},
    )


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    """Liveness probe."""
    return HealthResponse(status="ok", version=VERSION)


@app.get("/message-types", tags=["reference"])
def message_types() -> list[dict[str, str]]:
    """List the supported cash-management message types."""
    return services.list_message_types()


@app.get("/reasons", tags=["reference"])
def reasons() -> list[dict[str, str]]:
    """List the known ISO external return reason codes."""
    return services.list_return_reasons()


@app.get("/message-types/{message_type}/schema", tags=["reference"])
def input_schema(message_type: str) -> dict[str, Any]:
    """Return the reversing-entry input JSON Schema for a message type."""
    try:
        return services.get_input_schema(message_type)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/message-types/{message_type}/required-fields", tags=["reference"])
def required_fields(message_type: str) -> list[str]:
    """Return the required reversing-entry fields for a message type."""
    try:
        return services.get_required_fields(message_type)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/validate-identifier", tags=["validation"])
def validate_identifier(kind: str, value: str) -> dict[str, Any]:
    """Validate an IBAN, BIC, or LEI."""
    try:
        return services.validate_identifier(kind, value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/validate-records", tags=["validation"])
def validate_records(request: ValidateRecordsRequest) -> dict[str, Any]:
    """Validate flat reversing-entry records against a message type."""
    try:
        return services.validate_records(request.message_type, request.records)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/parse", tags=["statements"])
def parse(request: StatementRequest) -> dict[str, Any]:
    """Parse an incoming statement into structured data."""
    services.guard_xml(request.xml)
    try:
        return services.parse_statement(request.xml)
    except Camt053Error as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/check/cbpr-readiness", tags=["compliance"])
def check_cbpr_readiness(request: StatementRequest) -> dict[str, Any]:
    """Check a statement against the CBPR+ Nov 2026 acceptance rules.

    Walks the supplied camt.05x payload and reports every issue that will
    fail the coordinated CBPR+ / Fedwire / CHAPS / T2 cutover on
    **14-16 November 2026**: unstructured-only postal addresses and
    deprecated / unrecognised schema versions.

    Returns the structured report ``{"cbpr_ready": bool, ...}``. The HTTP
    status is always ``200`` for parseable XML, even when ``cbpr_ready`` is
    ``False`` (the absence of CBPR+ readiness is a *result*, not an error).
    Malformed XML returns ``400``.
    """
    services.guard_xml(request.xml)
    try:
        return services.check_cbpr_readiness(request.xml)
    except (ValueError, Camt053Error) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/entries", tags=["statements"])
def entries(
    request: StatementRequest, reason_code: str | None = None
) -> list[dict[str, Any]]:
    """List the entries on a statement (optionally filtered by reason)."""
    services.guard_xml(request.xml)
    try:
        if reason_code:
            return services.filter_entries(request.xml, reason_code)
        return services.list_entries(request.xml)
    except Camt053Error as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/reverse", tags=["statements"])
def reverse(request: ReversalRequest) -> Response:
    """Generate a reversing entry for matching statement entries."""
    services.guard_xml(request.xml)
    try:
        xml = services.generate_reversal(request.xml, request.reason_code)
    except Camt053Error as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(content=xml, media_type="application/xml")
