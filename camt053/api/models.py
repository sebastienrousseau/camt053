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

"""Pydantic request/response models for the Camt053 REST API."""

from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "StatementRequest",
    "ReversalRequest",
    "ValidateRecordsRequest",
    "HealthResponse",
]


class StatementRequest(BaseModel):
    """An incoming statement document."""

    xml: str = Field(..., description="Raw camt.05x statement XML.")


class ReversalRequest(BaseModel):
    """A request to generate a reversing entry from a statement."""

    xml: str = Field(..., description="Raw incoming camt.05x statement XML.")
    reason_code: str = Field(
        "AC04",
        description="ISO external return reason code to reverse.",
    )


class ValidateRecordsRequest(BaseModel):
    """A batch of flat reversing-entry records to validate."""

    message_type: str = Field(
        ..., description="Supported cash-management message type."
    )
    records: list[dict[str, Any]] = Field(
        ..., description="Flat reversing-entry records."
    )


class HealthResponse(BaseModel):
    """Service health response."""

    status: str = "ok"
    version: str
