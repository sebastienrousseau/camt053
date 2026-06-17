#!/usr/bin/env python3
"""Example: drive the REST API in-process with the FastAPI test client.

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/rest_api_client.py

Exercises the API without starting a server. To run the real server:
    uvicorn camt053.api.app:app --reload
"""

from fastapi.testclient import TestClient

from camt053.api.app import app

STATEMENT = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">
  <BkToCstmrStmt>
    <GrpHdr><MsgId>STMT-MSG-0001</MsgId><CreDtTm>2026-06-15T08:00:00</CreDtTm></GrpHdr>
    <Stmt>
      <Id>STMT-0001</Id><CreDtTm>2026-06-15T08:00:00</CreDtTm>
      <Acct><Id><IBAN>GB29NWBK60161331926819</IBAN></Id><Ccy>EUR</Ccy></Acct>
      <Bal><Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>
        <Amt Ccy="EUR">10000.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
        <Dt><Dt>2026-06-15</Dt></Dt></Bal>
      <Ntry>
        <NtryRef>NTRY-0001</NtryRef>
        <Amt Ccy="EUR">1500.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
        <Sts><Cd>BOOK</Cd></Sts>
        <NtryDtls><TxDtls>
          <RtrInf><Rsn><Cd>AC04</Cd></Rsn></RtrInf>
        </TxDtls></NtryDtls>
      </Ntry>
    </Stmt>
  </BkToCstmrStmt>
</Document>"""


def main() -> None:
    client = TestClient(app)

    print("GET /health ->", client.get("/health").json())
    print(
        "GET /message-types ->",
        [m["message_type"] for m in client.get("/message-types").json()],
    )

    entries = client.post(
        "/entries", params={"reason_code": "AC04"}, json={"xml": STATEMENT}
    ).json()
    print(f"POST /entries?reason_code=AC04 -> {len(entries)} entry(ies)")

    resp = client.post(
        "/reverse", json={"xml": STATEMENT, "reason_code": "AC04"}
    )
    print(
        f"POST /reverse -> {resp.status_code} {resp.headers['content-type']}"
    )
    print(resp.text[:120], "...")


if __name__ == "__main__":
    main()
