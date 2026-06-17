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

from typing import Any

from fastapi import FastAPI, HTTPException, Response

from camt053 import services
from camt053.api.models import (
    HealthResponse,
    ReversalRequest,
    StatementRequest,
    ValidateRecordsRequest,
)
from camt053.constants import VERSION
from camt053.exceptions import Camt053Error

app = FastAPI(
    title="Camt053 API",
    description=(
        "Read ISO 20022 camt Bank-to-Customer Statements and generate "
        "validated reversing entries."
    ),
    version=VERSION,
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
    try:
        return services.parse_statement(request.xml)
    except Camt053Error as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/entries", tags=["statements"])
def entries(
    request: StatementRequest, reason_code: str | None = None
) -> list[dict[str, Any]]:
    """List the entries on a statement (optionally filtered by reason)."""
    try:
        if reason_code:
            return services.filter_entries(request.xml, reason_code)
        return services.list_entries(request.xml)
    except Camt053Error as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/reverse", tags=["statements"])
def reverse(request: ReversalRequest) -> Response:
    """Generate a reversing entry for matching statement entries."""
    try:
        xml = services.generate_reversal(request.xml, request.reason_code)
    except Camt053Error as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(content=xml, media_type="application/xml")
