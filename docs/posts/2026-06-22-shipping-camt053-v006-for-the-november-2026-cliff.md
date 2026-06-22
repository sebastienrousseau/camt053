<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->

# Shipping `camt053` v0.0.6 for the 14-16 November 2026 ISO 20022 cliff

*A vertical slice — core library, CLI, REST API, MCP server, LSP
server, two companion packages — released together to ride the
last structural deadline of the 4-year ISO 20022 cross-border
migration.*

**Published:** 2026-06-22
**Author:** Sebastien Rousseau
**Project:** [`camt053`](https://github.com/sebastienrousseau/camt053) + 4-package suite

---

## TL;DR

I just shipped v0.0.6 of [`camt053`](https://github.com/sebastienrousseau/camt053),
a Python library that parses, validates, and reverses ISO 20022
`camt.05x` bank statements (the standardised account reports
banks send their corporate customers). The release was timed
against the **14-16 November 2026** coordinated CBPR+ / Fedwire /
CHAPS / T2 cutover — the last structural deadline of the cross-
border ISO 20022 migration that started in 2022. Five months out,
the producer/consumer gap is real, and most Python tooling is not
ready.

v0.0.6 ships a vertical slice across the suite:

| Package | Role |
| :--- | :--- |
| [`camt053`](https://pypi.org/project/camt053/) | core library (Click CLI + FastAPI REST API) |
| [`camt053-mcp`](https://pypi.org/project/camt053-mcp/) | Model Context Protocol server (for AI agents) |
| [`camt053-lsp`](https://pypi.org/project/camt053-lsp/) | Language Server (editor diagnostics + completion) |
| [`camt053-writer-xlsx`](https://pypi.org/project/camt053-writer-xlsx/) | Excel writer for parsed statements (v0.0.7, shipped under the same milestone) |
| [`camt053-loader-mt940`](https://pypi.org/project/camt053-loader-mt940/) | SWIFT MT940 → camt.053 converter (v0.0.7) |

The headline new capabilities:

- **`check_cbpr_readiness`** — pre-flight that tells you whether
  a `camt.05x` payload will pass the Nov 2026 acceptance rules
  *before* you forward it on.
- **Schema-version negotiation** — `detect_schema_version` +
  `classify_schema_version` + `validate_schema_version(strict=)`
  across `.001.02` → `.001.13` → `.001.14`, with a curated
  *current* / *deprecated* / *unsupported* taxonomy.
- **HMAC-SHA-256 hash-chain audit log** — tamper-evident,
  append-only, with a documented HMAC scheme so a third party
  can verify the chain offline.
- **OpenTelemetry instrumentation + RED metrics** —
  `camt053.parse` / `.validate` / `.reverse` spans;
  `camt053_requests_total{op, status}` counters.
- **Exactly-once dedupe primitives** — `compute_dedupe_key(s)`
  on the `(GrpHdr/MsgId, Stmt/Id, Stmt/ElctrncSeqNb)` tuple, plus
  `stable_reversal_reference` for byte-identical reversing-entry
  IDs across runs.
- **Partial-batch (`strict: bool = True`) parsing** with a
  `ParseReport.corrupt_entry_count` envelope so corrupt entries
  never get silently dropped.

Below: why the cliff matters, what the producer/consumer gap
actually looks like in practice, and why the competitive landscape
for ISO 20022 tooling in Python is uncontested for the camt.053
niche.

---

## Why the 14-16 November 2026 cliff matters

The four-year ISO 20022 cross-border migration is wrapping up. The
final structural deadline is a coordinated cutover weekend that
hits **three things at once**:

### 1. CBPR+ stops accepting unstructured-only postal addresses

From the Nov 14-16 cutover, every CBPR+ message (`pacs.008`,
`pacs.009`, `camt.053`, `camt.054` and related) must carry **structured**
postal addresses on debtor, creditor, and ultimate parties. A
`<PstlAdr>` containing only `<AdrLine>` lines (without sibling
`<TwnNm>` and `<Ctry>`) will be **rejected at FINplus**.

This breaks every system that today serialises a customer address
as "ACME Corp, 1 Main St, Anytown, USA" into a single `AdrLine`
and lets the bank figure it out. In practice that is most ERPs,
treasury middleware, and a surprising number of in-house adapters
written in the past five years.

`check_cbpr_readiness` walks a payload and flags every `<PstlAdr>`
that will fail this check, before you ship the payload to your
correspondent. v0.0.6 also adds the matching `validate_records`
schema check for the corresponding inbound flow.

### 2. `camt.110` / `camt.111` become mandatory

Legacy MT 19x exception and investigation flows are retired on
cross-border. They become `camt.110` (Account Reporting Request)
and `camt.111` (Notification of Case Closure), with structured
fields replacing the free-form MT n92 / n95 / n96 / n99 narrative
that's been around for decades.

If your reconciliation pipeline today does string-match on MT
narrative — and a startling number of them do — Nov 16 is the
day that stops working.

### 3. T2S R2026.NOV upgrades to MR2026

The Eurosystem T2S RTGS and T2 RTGS systems uplift to maintenance
release **MR2026** the same weekend. `camt.053` / `camt.054`
produced by T2 RTGS move to the MR2026 variant; older variants
are no longer accepted by T2 / T2S at receipt.

The [version-matrix](https://github.com/sebastienrousseau/camt053/blob/main/docs/version-matrix.md) page lists every
revision the suite supports, with the Nov 2026 cliff annotated
row-by-row.

---

## The producer/consumer schema gap is real

The clean migration story is: banks produce `camt.053.001.13` (the
CBPR+ current set), corporate customers consume `camt.053.001.13`,
everyone's happy.

The actual story, from talking to corporate treasury teams:

- **Banks ship `.001.08`** — the cross-border current set on the
  producer side. Goldman Sachs, JPMorgan, Citi, BNP, Standard
  Chartered, Deutsche Bank, BNY Mellon. Every CBPR+-active bank.
- **ERPs consume `.001.02`** — SAP, Oracle, Workday. Yes, in 2026.
  Yes, even after `.02` was deprecated.
- **Treasury middleware sits in the middle** — Cobase, FinLync,
  Kyriba, and dozens of in-house adapters. They translate. Most
  of them translate by string-replacing the namespace declaration.

The cross-version delta isn't huge but it's not zero. New optional
elements, tightened patterns, restructured `<PstlAdr>` for the
cliff. The string-replace adapters that work today break the
moment a bank starts using a new optional element.

`camt053` v0.0.6 handles the version gap by **classifying** every
payload (`current` / `deprecated` / `unsupported`) and giving the
caller an explicit `validate_schema_version(strict=True)` gate.
The default mode is lenient: parse what you can, return a
`ParseReport.corrupt_entry_count` for what you can't, never
silently drop entries.

The classification taxonomy is in
[`camt053/schema_version.py`](../../camt053/schema_version.py)
and exposed through every interface: CLI, REST API, MCP
`validate_statement` tool, LSP diagnostics.

---

## Competitive landscape

The Python ecosystem for ISO 20022 cash-management messages is
surprisingly empty:

- **The only direct ISO 20022 MCP competitor is
  [`deniskarlinsky/iso20022-mcp`](https://github.com/deniskarlinsky/iso20022-mcp)**:
  9 generic tools, 2 GitHub stars, no Prompts, no Resources, no
  Sampling, no auth. Hasn't seen a commit in months.
- Aggregator-style MCP servers (Stripe, Modern Treasury, Plaid,
  bank-mcp) never touch raw camt / pain / pacs XML. They surface
  bank-API abstractions, not ISO 20022 primitives.
- The "real" ISO 20022 toolchains are in Java: Prowide, Volante,
  IBM Sterling. They are enterprise-licensed and not
  pip-installable.

`camt053-mcp` v0.0.6 ships **13 tools**, **2 resources**, and
a **`reversal_preview` prompt** (the four-step
parse → filter → confirm → generate workflow encoded so an
agent can quote it verbatim). v0.0.7 adds two more: **`cite_rulebook`**
and **`list_rulebook_clauses`**, which quote curated SEPA / CBPR+ /
HVPS+ rulebook clauses with canonical source URLs so agents can
ground their reasoning in the actual scheme documents. As of
publication, no other ISO 20022 MCP server does this.

The LSP server (`camt053-lsp`) is currently the only Language
Server I'm aware of that targets reversing-entry data files
specifically — diagnostics (schema + IBAN/BIC), completion (field
names + message types), hover (schema descriptions), code-actions
(insert missing required fields), document-symbols (outline view),
and formatting (full-document pretty-print) — all backed by the
shared `camt053.services` layer so the editor's behaviour matches
the CLI exactly.

---

## What v0.0.6 ships (a vertical slice)

Every new capability lands in `camt053.services` first, then is
re-exported through the other surfaces. This is deliberate: the
CLI, REST API, MCP server, and LSP server are all thin wrappers
over the same `services` layer, so they cannot drift.

### Core library

- `camt053.compliance.check_cbpr_readiness(xml)` — walks the
  payload and reports every issue that will fail the Nov 2026
  rules. Returns a structured `{cbpr_ready, schema_version,
  checked_at, cutover_date, issues, summary}` envelope.
- `camt053.schema_version.{detect,classify,validate}_schema_version`
  — the four-state taxonomy above.
- `camt053.audit.{HashChain, AuditEvent, ChainVerification,
  verify_chain, compute_event_hmac, GENESIS_HASH}` — append-only
  HMAC hash-chain audit primitives.
- `camt053.telemetry.{trace_span, measure, record_request}` —
  optional `[telemetry]` extra; ships an OpenTelemetry tracer +
  RED metric counters out of the box.
- `camt053.parse.dedupe.{compute_dedupe_key, compute_dedupe_keys}`
  — exactly-once helpers on the canonical statement triple.
- `camt053.parse.report.{ParseReport, EntryDiagnostic}` —
  partial-batch envelope (lenient mode never drops entries
  silently).
- `camt053.reversal.reversal.stable_reversal_reference` —
  deterministic 32-char reversal identifier
  (`sha256(originalRef || "REV")[:32]`).

### CLI

```sh
camt053 check-cbpr-readiness statement.xml
camt053 detect-schema-version statement.xml
camt053 generate-reversal statement.xml --reason AC04
```

### REST API

`POST /check-cbpr-readiness`, `POST /reverse`, `POST /validate`,
`POST /parse` — same payloads as the CLI, same data shape on the
wire.

### MCP server (`camt053-mcp`)

13 tools + 2 resources + 1 prompt. Full per-tool example in
[`examples/`](https://github.com/sebastienrousseau/camt053-mcp/tree/main/examples).
The [10-minute quickstart](https://github.com/sebastienrousseau/camt053-mcp/blob/main/docs/quickstart.md)
walks through Claude Desktop wiring.

### LSP server (`camt053-lsp`)

Diagnostics, completion, hover, code-actions, document-symbols,
formatting — all on plain JSON arrays of reversing-entry records.
[Editor wiring quickstart](https://github.com/sebastienrousseau/camt053-lsp/blob/main/docs/quickstart.md)
covers Neovim, VS Code, and generic LSP clients.

### Companion packages (shipped at v0.0.7 under the same milestone)

- [`camt053-writer-xlsx`](https://pypi.org/project/camt053-writer-xlsx/)
  — `write_xlsx(document, "out.xlsx")` produces a stable four-sheet
  workbook (Metadata / Balances / Entries / Reversals) for
  accountants and auditors.
- [`camt053-loader-mt940`](https://pypi.org/project/camt053-loader-mt940/)
  — `parse_mt940(text)` returns the same `ParsedDocument` shape
  as the core parser, so the SWIFT MT940 → camt.053 conversion
  drops into every downstream consumer (writer, validator,
  reversal builder, MCP, LSP) without changes. MT940 retires Nov
  2028; this package bridges the two-year tail.

---

## Try it

```sh
pip install camt053
```

Pre-flight a statement before forwarding it on:

```sh
camt053 check-cbpr-readiness statement.xml
```

Add the MCP server to Claude Desktop:

```sh
pip install camt053-mcp
```

```json
{
  "mcpServers": {
    "camt053": { "command": "camt053-mcp" }
  }
}
```

Open a reversing-entry data file in Neovim with diagnostics on:

```sh
pip install camt053-lsp
```

```lua
vim.lsp.config["camt053"] = {
  cmd = { "camt053-lsp" },
  filetypes = { "json" },
  root_markers = { ".git" },
}
vim.lsp.enable("camt053")
```

Or write parsed statements to Excel for the accounting team:

```python
from camt053.parse.statement_parser import parse_document
from camt053_writer_xlsx import write_xlsx

write_xlsx(parse_document(open("statement.xml").read()), "out.xlsx")
```

---

## Quality posture

Every package in the suite enforces (in CI):

- 100% line + branch coverage (`--cov-fail-under=100`)
- 100% docstring coverage (`interrogate --fail-under=100`)
- strict `mypy`, `ruff`, `black`, `bandit -ll`
- OpenSSF Scorecard weekly
- SLSA Build L3 provenance (`actions/attest-build-provenance@v3`)
- PEP 740 sigstore attestations on PyPI uploads
- CycloneDX 1.6 + SPDX 2.3 SBOMs + pip-licenses manifest attached
  to every GitHub release
- Signed commits + branch protection
- Hypothesis property tests (`tests/test_property_based.py`)
- pytest-benchmark performance regression guards

The `SECURITY.md` in each repo maps every shipped control to its
**NIST SP 800-218 SSDF practice ID** so security-conscious
procurement teams can do a one-pass review.

---

## Roadmap

v0.0.7 is the next ride: per-version profile dispatch
(`.02` / `.08` / `.13` differ in optional-element semantics, not
just XSD), MCP `cite_rulebook` (already shipped), MCP
`export_journal(target=xero|qbo|netsuite|sap)` (in flight), MCP
Sampling (`classify_entry` under MCP's structured-tool envelope),
and the OpenSSF Best Practices Silver application.

If you're consuming `camt.05x` in production, the
[v0.0.6 release notes](https://github.com/sebastienrousseau/camt053/releases/tag/v0.0.6)
and the [Nov 2026 cliff matrix](https://github.com/sebastienrousseau/camt053/blob/main/docs/version-matrix.md) are the two
pages worth reading today.

If you find an issue, open one. If a payment payload that should
pass `check_cbpr_readiness` fails it (or vice versa), I want to
know — the registry is rule-level, not exhaustive, and field
reports are the fastest way to close the long-tail gaps.

— Sebastien
