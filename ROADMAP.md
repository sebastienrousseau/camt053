<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->

# `camt053` roadmap

## Mission

A robust, secure, high-performance ISO 20022 `camt.05x` bank-statement
library with a small well-tested core, first-class developer surfaces
(library, CLI, REST, MCP, LSP), companion packages for adjacent
formats (Excel writer, MT940 loader), and a vertical commitment to
the **14-16 November 2026** CBPR+ / T2S MR2026 cutover.

## Where we are (v0.0.7, shipped 2026-06-22)

- **Parsing**: `camt.052/053/054` revisions `.001.08`, `.001.13`,
  `.001.14`; deprecated `.001.02` → `.001.07` still parse with a
  deprecation diagnostic.
- **Validation**: official ISO 20022 XSDs bundled per revision +
  partial-batch lenient mode with a `ParseReport` envelope that
  surfaces corrupt entries rather than dropping them.
- **Per-version profile dispatch** (`camt053.profiles`):
  `Profile_v02` / `_v08` / `_v13` / `_v14` enforce version-specific
  rules (structured-address mandate, deprecation, MR2026 strictness)
  on top of the namespace-agnostic parser.
- **CBPR+ Nov 2026 cliff pre-flight**:
  `camt053.compliance.check_cbpr_readiness(xml)` + the
  `cite_rulebook` MCP tool for SEPA/CBPR+/HVPS+ citations.
- **Reversing-entry generation**: deterministic IDs
  (`sha256(originalRef || "REV")[:32]`); XSD-valid camt.053.001.14
  output.
- **Idempotency**: `compute_dedupe_key` / `compute_dedupe_keys` on
  the `(MsgId, StmtId, ElctrncSeqNb)` triple.
- **HMAC hash-chain audit log** (`camt053.audit`) with offline
  verification via `verify_chain`.
- **OpenTelemetry instrumentation** (`camt053.telemetry`) with RED
  metric counters; ships as the `[telemetry]` extra.
- **Surfaces**: CLI command suite; REST API
  (`camt053.api.app:app`); MCP server (`camt053-mcp`: 19 tools, 3
  resources, 4 prompts); LSP server (`camt053-lsp`: diagnostics,
  completion, hover, code-actions, document-symbols, formatting).
- **Companion packages**:
  [`camt053-writer-xlsx`](https://pypi.org/project/camt053-writer-xlsx/)
  and [`camt053-loader-mt940`](https://pypi.org/project/camt053-loader-mt940/),
  both live on PyPI at v0.0.7.
- **Supply chain**: 100% line + branch coverage; 100% docstring
  coverage; OpenSSF Scorecard; signed git tags; SLSA Build L3
  provenance via `actions/attest-build-provenance@v3`; PEP 740
  sigstore attestations on PyPI; CycloneDX 1.6 + SPDX 2.3 +
  pip-licenses SBOM bundle on every GitHub release; NIST SP 800-218
  SSDF practice mapping in `SECURITY.md`.

## v0.0.8 — Q3 2026

Goal: HTTP transport, multi-tenant deployments, OpenSSF Best
Practices Gold.

- **MCP HTTP/SSE transport variant**
  (`camt053-mcp/issues/42`): `camt053-mcp --transport=http
  --bind=…` + bearer-token auth + optional `Camt053-Account`
  tenant header → `Context` for multi-tenant scoping. Closes D7
  in #17.
- **MCP `export_journal` NetSuite + SAP S/4HANA targets**:
  complete D5 of #17 (Xero + QBO shipped in v0.0.7).
- **OpenSSF Best Practices Silver** badges live across all three
  badged repos (camt053, camt053-mcp, camt053-lsp); Gold
  application starts once a second maintainer is named.
- **Second maintainer** named in `MAINTAINERS.md` (active
  recruiting — see [`GOVERNANCE.md`](GOVERNANCE.md)).
- **Expanded `camt053.profiles` registry**: dedicated profile for
  each future minor revision as the ISO 20022 maintenance
  releases land.
- **Examples expansion**: from 10 today to 20+ runnable examples
  in `camt053/examples/`, one per public function in
  `camt053.services`.

## v0.0.9 — Q4 2026

Goal: Nov 2026 cliff readiness verified by production users.

- **Cliff lessons-learned post** on the docs site once banks
  publish their post-Nov-2026 producer behaviour.
- **`camt.110` / `camt.111`** parsing + generation (the
  Nov-2026-mandated cross-border exception and investigation
  flows replacing legacy MT 19x).
- **Streaming + back-pressure parsing benchmarks** rerun against
  real T2 RTGS MR2026 statements.

## v0.1.0 — Q1 2027

Goal: first stable minor; SemVer minor-bump policy applies to
deprecation-set changes.

- **Schema version classification taxonomy frozen**: any future
  current→deprecated transition is a minor bump (SemVer-anchored).
- **Backwards-compatibility policy** moves from "informal" to
  binding (documented per-API).
- **OpenSSF Best Practices Gold** across all three badged repos.

## Beyond v0.1.0

These are **explicitly out of scope** until a contributor steps up
with a concrete proposal and a maintenance plan:

- **camt.05x writer surface from raw data** (currently only via
  the Excel writer / loader → ParsedDocument → camt.053 round-trip
  through `camt053.services.serialize_statement`).
- **Real-time gateway** for streaming statements from a bank's
  webhook into a downstream system (better fit for a separate
  package; the library is happy to be plugged into one).
- **Bundled UI** (any HTTP surface stays headless; UIs live in
  consumer projects).

## How to influence the roadmap

- Open an issue with the proposed change + the use case it
  unblocks.
- For larger items, sketch a design in the issue body and ping
  the lead maintainer.
- See [`GOVERNANCE.md`](GOVERNANCE.md) for the decision-making
  process.
