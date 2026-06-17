"""Shared fixtures for the camt053 test suite."""

import pytest

# A camt.053 Bank-to-Customer Statement with three booked entries:
#   * NTRY-0001 - a EUR 1500.00 credit returned AC04 (Closed Account)
#   * NTRY-0002 - a EUR 980.50 credit returned AC06 (Blocked Account)
#   * NTRY-0003 - a EUR 42.00 debit with no return reason
SAMPLE_STATEMENT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">
  <BkToCstmrStmt>
    <GrpHdr>
      <MsgId>STMT-MSG-0001</MsgId>
      <CreDtTm>2026-06-15T08:00:00</CreDtTm>
    </GrpHdr>
    <Stmt>
      <Id>STMT-0001</Id>
      <ElctrncSeqNb>1</ElctrncSeqNb>
      <CreDtTm>2026-06-15T08:00:00</CreDtTm>
      <Acct>
        <Id><IBAN>GB29NWBK60161331926819</IBAN></Id>
        <Ccy>EUR</Ccy>
        <Ownr><Nm>Acme Treasury Ltd</Nm></Ownr>
        <Svcr><FinInstnId><BICFI>NWBKGB2LXXX</BICFI></FinInstnId></Svcr>
      </Acct>
      <Bal>
        <Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>
        <Amt Ccy="EUR">10000.00</Amt>
        <CdtDbtInd>CRDT</CdtDbtInd>
        <Dt><Dt>2026-06-15</Dt></Dt>
      </Bal>
      <Ntry>
        <NtryRef>NTRY-0001</NtryRef>
        <Amt Ccy="EUR">1500.00</Amt>
        <CdtDbtInd>CRDT</CdtDbtInd>
        <Sts><Cd>BOOK</Cd></Sts>
        <BookgDt><Dt>2026-06-15</Dt></BookgDt>
        <ValDt><Dt>2026-06-15</Dt></ValDt>
        <NtryDtls><TxDtls>
          <Refs><EndToEndId>E2E-0001</EndToEndId><TxId>TX-0001</TxId></Refs>
          <Amt Ccy="EUR">1500.00</Amt>
          <CdtDbtInd>CRDT</CdtDbtInd>
          <RtrInf><Rsn><Cd>AC04</Cd></Rsn><AddtlInf>Beneficiary account closed</AddtlInf></RtrInf>
          <RltdPties>
            <Dbtr><Nm>Globex SA</Nm></Dbtr>
            <DbtrAcct><Id><IBAN>DE89370400440532013000</IBAN></Id></DbtrAcct>
          </RltdPties>
        </TxDtls></NtryDtls>
      </Ntry>
      <Ntry>
        <NtryRef>NTRY-0002</NtryRef>
        <Amt Ccy="EUR">980.50</Amt>
        <CdtDbtInd>CRDT</CdtDbtInd>
        <Sts><Cd>BOOK</Cd></Sts>
        <BookgDt><Dt>2026-06-15</Dt></BookgDt>
        <NtryDtls><TxDtls>
          <Refs><EndToEndId>E2E-0002</EndToEndId></Refs>
          <RtrInf><Rsn><Cd>AC06</Cd></Rsn></RtrInf>
        </TxDtls></NtryDtls>
      </Ntry>
      <Ntry>
        <NtryRef>NTRY-0003</NtryRef>
        <Amt Ccy="EUR">42.00</Amt>
        <CdtDbtInd>DBIT</CdtDbtInd>
        <Sts>BOOK</Sts>
      </Ntry>
    </Stmt>
  </BkToCstmrStmt>
</Document>"""


@pytest.fixture
def statement_xml() -> str:
    """A camt.053 statement with AC04, AC06, and a plain debit entry."""
    return SAMPLE_STATEMENT_XML


@pytest.fixture
def reversal_record() -> dict:
    """A complete, valid flat reversing-entry record."""
    return {
        "statement_msg_id": "RVSL-STMT-0001",
        "creation_date_time": "2026-06-15T08:00:00",
        "statement_id": "RVSL-STMT-0001",
        "electronic_seq_nb": "1",
        "account_id": "GB29NWBK60161331926819",
        "account_currency": "EUR",
        "account_owner_name": "Acme Treasury Ltd",
        "account_servicer_bic": "NWBKGB2LXXX",
        "bal_type_code": "CLBD",
        "bal_amount": "10000.00",
        "bal_currency": "EUR",
        "bal_credit_debit": "CRDT",
        "bal_date": "2026-06-15",
        "entry_ref": "RVSL-NTRY-0001",
        "original_ref": "NTRY-0001",
        "amount": "1500.00",
        "currency": "EUR",
        "credit_debit": "DBIT",
        "reversal_indicator": "true",
        "status": "BOOK",
        "booking_date": "2026-06-15",
        "value_date": "2026-06-15",
        "end_to_end_id": "E2E-0001",
        "tx_id": "TX-0001",
        "reason_code": "AC04",
        "additional_info": "Reversal of NTRY-0001: Closed Account Number",
        "counterparty_name": "Globex SA",
        "counterparty_account": "DE89370400440532013000",
    }
