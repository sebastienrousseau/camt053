# Quickstart: from bank statement to validated reversing entry in 10 minutes

This guide walks you from "the bank sent me a camt.053 statement with a
returned payment on it" to "I have a validated ISO 20022 reversing entry"
in five short steps. No prior ISO 20022 knowledge required.

If you already know what camt.053 is and just want the CLI flags, skip to
the [README](../README.md#quick-start).

---

## Prerequisites

- Python 3.10 or later
- 10 minutes
- A terminal

That's it. You won't need a bank account, a sandbox, or an ISO 20022 spec
PDF. Everything the tutorial needs ships inside the package (including the
official XSD schemas the validation runs against).

## Step 1: Install

```bash
pip install camt053
```

Verify:

```bash
camt053 -V
# -> Camt053, version 0.0.10
```

If you'd rather not pollute your global Python environment:

```bash
python -m venv venv
source venv/bin/activate          # macOS/Linux
venv\Scripts\activate             # Windows
pip install camt053
```

## Step 2: See what camt053 can do

```bash
camt053 -h
```

You'll see a command suite: `parse`, `entries`, `validate`, `reverse`,
`reasons`, `classify`, `message-types`, `validate-id`,
`check-cbpr-readiness`. We'll use five of them.

List the message families the library reads:

```bash
camt053 message-types
```

Output:

```text
                    Supported message types
  Message type      Name
 ──────────────────────────────────────────────────────────────
  camt.052.001.14   Bank To Customer Account Report
  camt.053.001.14   Bank To Customer Statement
  camt.054.001.14   Bank To Customer Debit Credit Notification
```

And the ISO return reason codes it knows (41 of them), each with the
handling action the built-in policy assigns:

```bash
camt053 reasons
```

```text
                    Return reason codes
  Code   Name                                       Action
 ──────────────────────────────────────────────────────────
  AC01   Incorrect Account Number                   return
  AC02   Invalid Debtor Account Number              return
  AC03   Invalid Creditor Account Number            return
  AC04   Closed Account Number                      return
  ...
  TM01   Cut Off Time                               retry
```

`AC04` (Closed Account Number) is the tutorial's return reason: a payment
you sent bounced because the beneficiary account was closed, and your bank
reported it back on your statement.

## Step 3: Get a statement to work with

Real statements come from your bank channel (EBICS, SFTP, portal
download). For the tutorial, save this minimal but fully schema-valid
camt.053.001.14 statement as `statement.xml`. It carries one booked EUR
1,500 credit that was returned with reason `AC04`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">
  <BkToCstmrStmt>
    <GrpHdr><MsgId>STMT-MSG-0001</MsgId><CreDtTm>2026-06-15T08:00:00</CreDtTm></GrpHdr>
    <Stmt>
      <Id>STMT-0001</Id>
      <CreDtTm>2026-06-15T08:00:00</CreDtTm>
      <Acct>
        <Id><IBAN>GB29NWBK60161331926819</IBAN></Id>
        <Ccy>EUR</Ccy>
        <Ownr><Nm>Acme Treasury Ltd</Nm></Ownr>
      </Acct>
      <Bal>
        <Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>
        <Amt Ccy="EUR">10000.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
        <Dt><Dt>2026-06-15</Dt></Dt>
      </Bal>
      <Ntry>
        <NtryRef>NTRY-0001</NtryRef>
        <Amt Ccy="EUR">1500.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
        <Sts><Cd>BOOK</Cd></Sts>
        <BookgDt><Dt>2026-06-14</Dt></BookgDt>
        <ValDt><Dt>2026-06-14</Dt></ValDt>
        <BkTxCd><Domn><Cd>PMNT</Cd><Fmly><Cd>RCDT</Cd><SubFmlyCd>RRTN</SubFmlyCd></Fmly></Domn></BkTxCd>
        <NtryDtls><TxDtls>
          <Refs><EndToEndId>E2E-0001</EndToEndId></Refs>
          <RtrInf><Rsn><Cd>AC04</Cd></Rsn></RtrInf>
        </TxDtls></NtryDtls>
      </Ntry>
    </Stmt>
  </BkToCstmrStmt>
</Document>
```

First thing to do with any incoming file: validate it against the official
ISO XSD (bundled with the package, no download needed):

```bash
camt053 validate -i statement.xml
```

```text
✓ Valid camt.053.001.14
```

## Step 4: Inspect the statement

See the entries, filtered down to the AC04 returns:

```bash
camt053 entries -i statement.xml -r AC04
```

```text
              Statement entries
  Reference    Amount   Ccy   Cr/Dr   Reason
 ────────────────────────────────────────────
  NTRY-0001   1500.00   EUR   CRDT    AC04
1 entry.
```

Or dump the whole parsed statement as JSON (group header, account,
balances, entries), ready for `jq` or your pipeline:

```bash
camt053 parse -i statement.xml
```

```json
{
  "message_type": "camt.053.001.14",
  "msg_id": "STMT-MSG-0001",
  "creation_date_time": "2026-06-15T08:00:00",
  "statements": [ ... ]
}
```

## Step 5: Generate the reversing entry

The headline command. Find every AC04 entry and emit a validated
camt.053.001.14 reversing-entry document:

```bash
camt053 reverse -i statement.xml -r AC04 -o reversal.xml
```

```text
✓ Reversing entry written to reversal.xml
```

Look at what it wrote:

```bash
head -12 reversal.xml
```

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	<BkToCstmrStmt>
		<GrpHdr>
			<MsgId>RVSL-STMT-0001</MsgId>
			<CreDtTm>2026-06-15T08:00:00</CreDtTm>
		</GrpHdr>
		<Stmt>
			<Id>RVSL-STMT-0001</Id>
```

The reversing entry mirrors the original booked entry with the
credit/debit indicator flipped (`CRDT` becomes `DBIT`), `RvslInd` set,
a stable `RVSL-` reference derived from the original (same input, same
output, every time), and the AC04 return reason carried in `RtrInf`.
It is XSD-validated before it is written; prove it to yourself:

```bash
camt053 validate -i reversal.xml
```

```text
✓ Valid camt.053.001.14
```

Prefer Python? The same workflow is three lines through the shared
services facade (the CLI, REST API, and MCP/LSP servers all call the
same functions):

```python
from camt053 import services

xml = open("statement.xml", encoding="utf-8").read()
ac04 = services.filter_entries(xml, "AC04")        # 1 entry
reversal = services.generate_reversal(xml, reason_code="AC04")
```

## What you just learned

- `camt053 validate` - XSD pre-flight for any incoming file (use this every time)
- `camt053 entries` / `camt053 parse` - inspect what the bank sent
- `camt053 reverse` - generate the validated reversing entry
- `camt053 reasons` / `message-types` - the built-in reference data

That's 80% of the surface for 90% of users.

## Where to go next

| If you want to... | Read |
| :--- | :--- |
| Reverse a whole directory of statements at once | `camt053 reverse --batch` ([`examples/generate_batch.py`](https://github.com/sebastienrousseau/camt053/blob/main/examples/generate_batch.py)) |
| Emit a pacs.004 PaymentReturn instead of camt.053 | `camt053 reverse --output-format pacs004` |
| Run camt053 as a REST service | `uvicorn camt053.api.app:app` ([README Usage](../README.md#usage)) |
| Pre-flight the Nov 14-16 2026 CBPR+ cutover | `camt053 check-cbpr-readiness` ([version matrix](version-matrix.md)) |
| Stream very large statements with bounded memory | [`examples/stream_entries.py`](https://github.com/sebastienrousseau/camt053/blob/main/examples/stream_entries.py) |
| Deploy the REST API with Redis + Prometheus + Grafana | [Deployment cookbook](deployment-cookbook.md) |
| Wire camt053 into an AI assistant (Claude Desktop, etc.) | `pip install camt053-mcp` |
| See every public function exercised in a runnable script | [`examples/`](https://github.com/sebastienrousseau/camt053/tree/main/examples) |

## Troubleshooting

| Symptom | Likely cause | Fix |
| :--- | :--- | :--- |
| `camt053: command not found` | Install went to a directory not on `PATH` | Re-install in a venv (see Step 1) |
| `✗ Invalid camt.053.001.14` on a file your bank sent | Bank emits an older revision (.02, .08) | camt053 detects the version from the namespace; run `camt053 parse` (parsing accepts all revisions), and see the [version matrix](version-matrix.md) |
| `No statement entries match return reason AC04` | The statement has no entry with that reason | Run `camt053 entries -i <file>` (no `-r`) to see which reasons are present |
| `XML payload contains a DOCTYPE or ENTITY declaration` | The file carries a DTD (or an XXE attempt) | Deliberate: the security guard refuses inline DTDs; re-export the file without a DOCTYPE |
| Reversal amounts look re-ordered / reformatted | They aren't | Amounts are carried as strings end to end and rendered byte-for-byte; diff the `Amt` elements |

## Stuck?

- [Open an issue](https://github.com/sebastienrousseau/camt053/issues/new/choose)
  with the CLI invocation that failed plus the error output.
- See [SUPPORT.md](../SUPPORT.md) for the full support matrix.

---

*Found a confusing bit in this tutorial? PRs to
[`docs/quickstart.md`](https://github.com/sebastienrousseau/camt053/blob/main/docs/quickstart.md)
are the most useful thing a new user can contribute. You spot the sharp
edges that long-time users no longer see.*
