#!/usr/bin/env python3
"""Example: the REST API's reference and validation endpoints.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/rest_api_reference.py

``examples/rest_api_client.py`` covers the statement workflow (parse,
entries, reverse). This script covers the rest of the surface: health,
reference lookups, identifier / record validation, the CBPR+ readiness
check, and the OpenAPI document via ``services.load_openapi``.
To run the real server: ``uvicorn camt053.api.app:app``.
"""

import json

from fastapi.testclient import TestClient

from camt053.api.app import app
from camt053.services import load_openapi

STATEMENT = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.13">
  <BkToCstmrStmt><Stmt>
    <Acct>
      <Id><IBAN>GB29NWBK60161331926819</IBAN></Id>
      <Ownr>
        <Nm>Acme Treasury Ltd</Nm>
        <PstlAdr><StrtNm>1 Main St</StrtNm><TwnNm>London</TwnNm>
          <Ctry>GB</Ctry></PstlAdr>
      </Ownr>
    </Acct>
  </Stmt></BkToCstmrStmt>
</Document>"""


def main() -> None:
    """Hit every reference / validation endpoint in-process."""
    client = TestClient(app)

    print(f"GET /health -> {client.get('/health').json()}")

    types = client.get("/message-types").json()
    print(f"GET /message-types -> {len(types)} supported types")

    reasons = client.get("/reasons").json()
    print(f"GET /reasons -> {len(reasons)} known reason codes")

    mt = "camt.053.001.14"
    fields = client.get(f"/message-types/{mt}/required-fields").json()
    print(f"GET /message-types/{mt}/required-fields -> {fields}")

    schema = client.get(f"/message-types/{mt}/schema").json()
    print(
        f"GET /message-types/{mt}/schema -> {len(schema['properties'])} properties"
    )

    check = client.get(
        "/validate-identifier",
        params={"kind": "iban", "value": "GB29NWBK60161331926819"},
    ).json()
    print(f"GET /validate-identifier -> valid={check['valid']}")

    report = client.post(
        "/validate-records",
        json={"message_type": mt, "records": [{"credit_debit": "SIDEWAYS"}]},
    ).json()
    print(f"POST /validate-records -> valid={report['valid']}")

    cbpr = client.post("/check/cbpr-readiness", json={"xml": STATEMENT}).json()
    print(f"POST /check/cbpr-readiness -> cbpr_ready={cbpr['cbpr_ready']}")

    openapi = json.loads(load_openapi())
    print(
        f"\nservices.load_openapi -> OpenAPI {openapi['openapi']}, "
        f"{len(openapi['paths'])} paths"
    )


if __name__ == "__main__":
    main()
