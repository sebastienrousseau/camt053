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

"""Security tests hardening the REST API against malicious XML."""

import importlib
import json

import pytest
from fastapi.testclient import TestClient

# ``camt053.api.__init__`` rebinds the ``app`` attribute on the package to the
# FastAPI instance, so a plain ``import camt053.api.app`` would not resolve to
# the module. ``import_module`` returns the real module object directly.
app_module = importlib.import_module("camt053.api.app")

pytestmark = pytest.mark.security

_XXE = (
    '<?xml version="1.0"?>'
    '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
    "<Document>&xxe;</Document>"
)

_BILLION_LAUGHS = (
    '<?xml version="1.0"?>'
    "<!DOCTYPE lolz ["
    '<!ENTITY lol "lol">'
    '<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;">'
    "]>"
    "<Document>&lol2;</Document>"
)


@pytest.fixture
def client():
    """A TestClient over the default app (default 1 MiB limit)."""
    return TestClient(app_module.app)


def test_oversized_body_rejected_413(client):
    """A request body over the limit is rejected with a structured 413."""
    big = "x" * (app_module.DEFAULT_MAX_XML_BYTES + 1)
    resp = client.post("/parse", json={"xml": big})
    assert resp.status_code == 413
    body = resp.json()
    assert body["error"] in ("payload_too_large", "too_large")


def test_oversized_declared_content_length_rejected_413(client):
    """An over-limit declared Content-Length is rejected up front."""
    headers = {
        "content-length": str(app_module.DEFAULT_MAX_XML_BYTES + 10),
        "content-type": "application/json",
    }
    resp = client.post("/parse", content=b"{}", headers=headers)
    assert resp.status_code == 413


def test_understated_content_length_measured(monkeypatch):
    """A body larger than its declared length is still rejected (413)."""
    monkeypatch.setenv("CAMT053_MAX_BODY_BYTES", "20")
    client = TestClient(app_module.app)
    payload = json.dumps({"xml": "y" * 200}).encode()
    resp = client.post(
        "/parse",
        content=payload,
        headers={
            # Understate the length so the up-front check passes and the
            # streamed-body measurement is what catches the oversized body.
            "content-length": "5",
            "content-type": "application/json",
        },
    )
    assert resp.status_code == 413


def test_bad_content_length_header_ignored(client, statement_xml):
    """A non-numeric Content-Length header does not crash the guard."""
    resp = client.post(
        "/parse",
        content=json.dumps({"xml": statement_xml}),
        headers={
            "content-length": "not-a-number",
            "content-type": "application/json",
        },
    )
    # Starlette recomputes the real length; request still succeeds.
    assert resp.status_code == 200


def test_xxe_payload_neutralized_400(client):
    """An XXE entity payload is rejected with a structured 400, not 5xx."""
    resp = client.post("/parse", json={"xml": _XXE})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"] == "doctype_forbidden"
    # No file contents leaked.
    assert "root:" not in resp.text


def test_billion_laughs_rejected_400(client):
    """An entity-expansion bomb is refused before parsing."""
    resp = client.post("/reverse", json={"xml": _BILLION_LAUGHS})
    assert resp.status_code == 400
    assert resp.json()["error"] == "doctype_forbidden"


def test_entries_doctype_rejected_400(client):
    """The entries endpoint also guards against DOCTYPE payloads."""
    resp = client.post("/entries", json={"xml": _XXE})
    assert resp.status_code == 400
    assert resp.json()["error"] == "doctype_forbidden"


def test_malformed_xml_returns_400_not_500(client):
    """Malformed (well-formed-looking but unrecognised) XML yields 4xx."""
    resp = client.post("/parse", json={"xml": "<nope/>"})
    assert resp.status_code == 400


def test_configurable_limit_via_env(monkeypatch, statement_xml):
    """CAMT053_MAX_BODY_BYTES lowers the accepted body size."""
    monkeypatch.setenv("CAMT053_MAX_BODY_BYTES", "50")
    client = TestClient(app_module.app)
    resp = client.post("/parse", json={"xml": statement_xml})
    assert resp.status_code == 413


def test_max_body_bytes_invalid_falls_back(monkeypatch):
    """A non-integer limit env var falls back to the default."""
    monkeypatch.setenv("CAMT053_MAX_BODY_BYTES", "abc")
    assert app_module._max_body_bytes() == app_module.DEFAULT_MAX_XML_BYTES


def test_max_body_bytes_nonpositive_falls_back(monkeypatch):
    """A non-positive limit env var falls back to the default."""
    monkeypatch.setenv("CAMT053_MAX_BODY_BYTES", "0")
    assert app_module._max_body_bytes() == app_module.DEFAULT_MAX_XML_BYTES


def test_max_body_bytes_custom(monkeypatch):
    """A valid positive limit env var is honoured."""
    monkeypatch.setenv("CAMT053_MAX_BODY_BYTES", "123")
    assert app_module._max_body_bytes() == 123
