<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->

# camt053 suite v0.0.14: OAuth 2.1 on the MCP transport, measured benchmarks, and a clean security slate

*Seven packages released in lockstep. The MCP server graduates from
a local stdio tool to an authenticated, observable, network-grade
service — and every number on the suite's security dashboard reads
zero.*

**Published:** 2026-07-16
**Author:** Sebastien Rousseau
**Project:** [`camt053`](https://github.com/sebastienrousseau/camt053) + 6-package suite

---

## TL;DR

All seven packages of the [`camt053`](https://pypi.org/project/camt053/)
suite — the Python toolkit that parses, validates, and reverses
ISO 20022 `camt.05x` bank statements — are now at **v0.0.14** on PyPI,
released in lockstep. The headline is
[`camt053-mcp`](https://pypi.org/project/camt053-mcp/): the Model
Context Protocol server that lets AI agents (Claude Desktop, Cursor,
custom orchestrators) work with real bank-statement XML now runs as a
production network service, not just a desktop subprocess.

| Package | v0.0.14 role |
| :--- | :--- |
| [`camt053`](https://pypi.org/project/camt053/) | core library (Click CLI + FastAPI REST API) |
| [`camt053-mcp`](https://pypi.org/project/camt053-mcp/) | MCP server — 22 tools, now with authenticated HTTP transport |
| [`camt053-lsp`](https://pypi.org/project/camt053-lsp/) | Language Server (editor diagnostics + completion) |
| [`camt-exceptions`](https://pypi.org/project/camt-exceptions/) | camt.056 Exceptions & Investigations generation |
| [`camt053-loader-mt940`](https://pypi.org/project/camt053-loader-mt940/) | SWIFT MT940 → camt.053 converter |
| [`camt053-loader-mt942`](https://pypi.org/project/camt053-loader-mt942/) | SWIFT MT942 → camt.052 converter |
| [`camt053-writer-xlsx`](https://pypi.org/project/camt053-writer-xlsx/) | Excel writer for parsed statements |

## What's new in the MCP server

Surveys of the public MCP ecosystem keep finding the same thing:
roughly 40% of servers ship with no authentication at all, and tool
metadata itself has become an attack surface. Financial-data tooling
has to clear a higher bar. v0.0.14's transport work is aimed squarely
at it:

- **Streamable HTTP transport** (`--transport=http`) alongside the
  stdio default — horizontal scaling and shared deployments instead of
  one subprocess per client.
- **OAuth 2.1 resource-server auth** with RFC 9728 protected-resource
  metadata: JWTs validated against your IdP's JWKS (algorithm taken
  from the key, never the token header), issuer/audience/scope
  enforcement, and spec-correct 401/403 challenges. A static bearer
  token remains as an explicit dev-mode fallback.
- **Multi-tenant scoping** via a `Camt053-Account` request header that
  flows into tool context.
- **Prometheus observability**: request counters, per-tool invocation
  counters and latency histograms on `/metrics`.
- **Tamper-evident audit**: every tool invocation logs session id,
  tool, redacted arguments, tenant, and outcome, HMAC-chained so a
  modified record breaks verification.
- **Measured, not extrapolated, benchmarks** — a k6 script plus an
  asyncio harness driven at 100 and 1,000 concurrent sessions with
  zero errors: ~300 requests/second per container with session reuse
  (2.4x the fresh-session rate), single-digit-millisecond p95 at
  realistic concurrency. Full methodology and honest queueing math in
  [BENCHMARKS.md](https://github.com/sebastienrousseau/camt053-mcp/blob/main/docs/BENCHMARKS.md).

The server is listed in the
[official MCP registry](https://registry.modelcontextprotocol.io) as
`io.github.sebastienrousseau/camt053-mcp`, and if you're evaluating
options, there's an honest, dated comparison of everything that
speaks ISO 20022 over MCP (and what the SaaS finance servers do
instead): [ISO 20022 MCP Servers Compared (2026)](https://github.com/sebastienrousseau/camt053-mcp/blob/main/docs/iso20022-mcp-servers-compared.md).

## The security slate

This release cycle also closed out the suite's entire security
backlog:

- **CVE-2026-7246 / PYSEC-2026-2132** (click < 8.3.3) fixed in every
  published wheel.
- **CodeQL scanning now active in all ten suite repositories**; every
  alert fixed or formally dispositioned — zero open findings.
- All GitHub Actions SHA-pinned, Docker base images digest-pinned,
  pip installs hash-pinned; the few residuals that cannot be pinned
  are documented in SECURITY.md.
- Load and soak test suites in every repo (concurrency, large-input,
  memory-growth), excluded from coverage gates but run in CI.
- SLSA Build Level 3 provenance and PEP 740 attestations on every
  release, as before.

## Why this matters

The November 2026 ISO 20022 cutover is now four months away, and AI
agents are arriving in payments operations faster than the tooling
that keeps them safe. The IMF places protocols like MCP in the
intent-and-orchestration layer of agentic payments; the BIS has shown
general-purpose LLMs replicating prudential cash-management practice.
What's been missing is statement-level ISO 20022 tooling an agent can
use through an authenticated, auditable, observable interface. That's
the gap this release is built for.

```sh
pip install camt053-mcp
camt053-mcp --transport=http --bind 127.0.0.1:8080
```

Feedback, issues, and PRs welcome on
[GitHub](https://github.com/sebastienrousseau/camt053-mcp).
