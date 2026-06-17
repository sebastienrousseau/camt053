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

"""Tests for the FastAPI REST API."""

from fastapi.testclient import TestClient

from camt053.api.app import app

client = TestClient(app)


def test_health():
    """The health endpoint reports the version."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_message_types_and_reasons():
    """Reference endpoints list message types and reasons."""
    assert len(client.get("/message-types").json()) == 3
    codes = [r["code"] for r in client.get("/reasons").json()]
    assert "AC04" in codes


def test_schema_and_required_fields():
    """Schema and required-field endpoints return data for a known type."""
    schema = client.get("/message-types/camt.053.001.14/schema").json()
    assert "properties" in schema
    fields = client.get(
        "/message-types/camt.053.001.14/required-fields"
    ).json()
    assert "reason_code" in fields


def test_schema_unknown_type_404():
    """An unknown message type yields 404."""
    resp = client.get("/message-types/camt.999.001.01/schema")
    assert resp.status_code == 404
    resp = client.get("/message-types/camt.999.001.01/required-fields")
    assert resp.status_code == 404


def test_validate_identifier():
    """Identifier validation works and unsupported kinds yield 400."""
    resp = client.get(
        "/validate-identifier", params={"kind": "bic", "value": "NWBKGB2LXXX"}
    )
    assert resp.json()["valid"] is True
    resp = client.get(
        "/validate-identifier", params={"kind": "ssn", "value": "1"}
    )
    assert resp.status_code == 400


def test_validate_records(reversal_record):
    """Record validation returns a report."""
    resp = client.post(
        "/validate-records",
        json={
            "message_type": "camt.053.001.14",
            "records": [reversal_record],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


def test_validate_records_unknown_type():
    """Validating against an unknown type yields 400."""
    resp = client.post(
        "/validate-records",
        json={"message_type": "camt.999.001.01", "records": [{}]},
    )
    assert resp.status_code == 400


def test_parse_and_entries(statement_xml):
    """The parse and entries endpoints read a statement."""
    resp = client.post("/parse", json={"xml": statement_xml})
    assert resp.json()["msg_id"] == "STMT-MSG-0001"

    resp = client.post("/entries", json={"xml": statement_xml})
    assert len(resp.json()) == 3

    resp = client.post(
        "/entries", params={"reason_code": "AC04"}, json={"xml": statement_xml}
    )
    assert len(resp.json()) == 1


def test_parse_bad_xml():
    """Malformed input yields 400."""
    resp = client.post("/parse", json={"xml": "<nope/>"})
    assert resp.status_code == 400


def test_entries_bad_xml():
    """The entries endpoint yields 400 on unparseable input."""
    resp = client.post("/entries", json={"xml": "<nope/>"})
    assert resp.status_code == 400


def test_reverse_returns_xml(statement_xml):
    """The reverse endpoint returns validated XML."""
    resp = client.post(
        "/reverse", json={"xml": statement_xml, "reason_code": "AC04"}
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/xml")
    assert "<RvslInd>true</RvslInd>" in resp.text


def test_reverse_no_match_422(statement_xml):
    """No matching entry yields 422."""
    resp = client.post(
        "/reverse", json={"xml": statement_xml, "reason_code": "MD07"}
    )
    assert resp.status_code == 422
