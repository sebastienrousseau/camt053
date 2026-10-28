<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->

<p align="center">
  <img src="https://cloudcdn.pro/camt053/v1/logos/camt053.svg" alt="camt053 logo" width="128" />
</p>

<h1 align="center">camt053</h1>

<p align="center">
  Read ISO 20022 camt.053, camt.052 and camt.054 bank statements, find entries by return reason code, and generate validated reversing entries.
</p>

<p align="center">
  <a href="https://github.com/sebastienrousseau/camt053/actions"><img src="https://img.shields.io/github/actions/workflow/status/sebastienrousseau/camt053/ci.yml?style=for-the-badge&logo=github" alt="Build" height="28" /></a>
  <a href="https://pypi.org/project/camt053/"><img src="https://img.shields.io/pypi/v/camt053?style=for-the-badge&color=fc8d62&logo=python" alt="Registry" height="28" /></a>
  <a href="https://sebastienrousseau.github.io/camt053/"><img src="https://img.shields.io/badge/docs-GitHub%20Pages-blue?style=for-the-badge&labelColor=555555&logo=readthedocs" alt="Docs" height="28" /></a>
  <a href="https://scorecard.dev/viewer/?uri=github.com/sebastienrousseau/camt053"><img src="https://img.shields.io/ossf-scorecard/github.com/sebastienrousseau/camt053?style=for-the-badge&label=OpenSSF%20Scorecard&logo=openssf" alt="OpenSSF Scorecard" height="28" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0%20OR%20MIT-blue.svg?style=for-the-badge" alt="License: Apache-2.0 OR MIT" height="28" /></a>
  <a href="https://github.com/sebastienrousseau/camt053/blob/main/docs/POLICIES.md"><img src="https://img.shields.io/badge/Python-3.11%2B-93450a.svg?style=for-the-badge&logo=python" alt="Python 3.11 or newer" height="28" /></a>
  <a href="https://www.bestpractices.dev/projects/13373"><img src="https://img.shields.io/cii/level/13373?style=for-the-badge&label=OpenSSF%20Best%20Practices&logo=openssf" alt="OpenSSF Best Practices" height="28" /></a>
</p>

<p align="center">
  <img src=".github/demo.gif" alt="camt053 demo: list a statement's entries, filter the AC04 return, generate the reversing entry, then validate it against the camt.053.001.14 XSD and list it" width="100%" />
</p>

---

## Contents

**Getting started**

- [Install](#install) — pip, the `fast` and `telemetry` extras, Docker
- [Requirements](#requirements) — toolchain floor, platforms
- [Quick Start](#quick-start) — parse a statement, find the AC04 return, generate its reversing entry

**The camt053 ecosystem**

- [The camt053 ecosystem](#the-camt053-ecosystem) — the core, the MCP and LSP servers, the MT940 and MT942 loaders, the Excel writer

**Library reference**

- [Capabilities at a glance](#capabilities-at-a-glance) — the current surface by theme
- [Ecosystem comparison](#ecosystem-comparison) — short matrix; full table at [`docs/COMPARISON.md`](docs/COMPARISON.md)
- [Benchmarks](#benchmarks) — headline numbers; full table at [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md)
- [Features](#features) — module-level capability list
- [Configuration](#configuration) — core options
- [Examples](#examples) — runnable example index

**Operational**

- [When not to use camt053](#when-not-to-use-camt053) — limitations
- [Development](#development) — make targets, fuzzing, CI
- [Security](#security) — guarantees and compliance
- [Documentation](#documentation) — all reference docs
- [Stability guarantees](#stability-guarantees) — SemVer axis, output stability, minimum toolchain discipline
- [License](#license)

---

## Install

### As a Python library

```sh
python -m pip install camt053
```

> **Latest release: v0.0.24**: namespace-agnostic camt.052/053/054 parsing and
> one-shot reversing-entry generation, validated against the official ISO 20022
> `camt.053.001.14` schema, for Python 3.11+, released with the whole suite at
> one version.
> [See what's new →][release-latest]

Two optional extras:

```sh
python -m pip install "camt053[fast]"        # lxml: XSD validation ~31x faster
python -m pip install "camt053[telemetry]"   # OpenTelemetry API for spans and metrics
```

`fast` only changes speed: a document `lxml` accepts is one the pure-Python
validator accepts too. The `camt053` command (the CLI) is installed with the
package. The REST API ships as a container image built from the
[`Dockerfile`](Dockerfile); see the
[deployment cookbook](docs/deployment-cookbook.md) for Compose, systemd and
Kubernetes recipes.

---

## Requirements

- Python 3.11 or newer, tested in CI on 3.11, 3.12, 3.13 and 3.14 on Linux,
  macOS and Windows ([toolchain policy](docs/POLICIES.md)).
- No system libraries. `lxml` is optional (the `fast` extra).
- Runtime dependencies are bounded in `pyproject.toml` (all but the
  calendar-versioned `certifi`), and each package with a published
  advisory, direct or pulled in by the REST API's web stack, is floored
  so no affected release can resolve.

---

## Quick Start

```python
from camt053 import parse_statement, services

# A minimal incoming camt.053 statement: a EUR 1,500 credit transfer that was
# booked, then returned because the beneficiary account was closed (AC04).
statement_xml = """<?xml version="1.0" encoding="UTF-8"?>
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

# 1. Parse into the typed model.
statement = parse_statement(statement_xml)
print(statement.account.identifier())          # -> GB29NWBK60161331926819
print(len(statement.entries))                   # -> 1

# 2. Select the entries returned AC04 (Closed Account).
ac04 = statement.entries_with_reason("AC04")
print(ac04[0].amount, ac04[0].credit_debit_indicator)   # -> 1500.00 CRDT

# 3. Generate the validated reversing entry (the original CRDT becomes DBIT).
reversal_xml = services.generate_reversal(statement_xml, reason_code="AC04")
assert "<RvslInd>true</RvslInd>" in reversal_xml
assert "<CdtDbtInd>DBIT</CdtDbtInd>" in reversal_xml
```

The same workflow from the command line, as in the demo above:

```sh
camt053 entries -i statement.xml -r AC04                  # the AC04 entries
camt053 reverse -i statement.xml -r AC04 -o reversal.xml  # the reversing entry
camt053 validate -i reversal.xml                          # against the ISO XSD
```

`parse`, `entries`, `reverse` and `validate` accept `-i -` to read from stdin.
The [10-minute quickstart](docs/quickstart.md) walks install, validate, parse
and reverse with real commands and output.

---

## The camt053 ecosystem

`camt053` is the core of six packages that release together at one version:
every member ships the core's number, so `camt053-mcp 0.0.24` is meant for
`camt053 0.0.24`. The wrappers, loaders and writer call the shared
`camt053.services` facade, so every interface behaves the same.
`scripts/check_suite_consistency.py` checks PyPI daily and fails when a
member disagrees.

| Component | Purpose | Use case |
| :--- | :--- | :--- |
| [`camt053`](https://pypi.org/project/camt053/) | Core library, Click CLI and FastAPI REST API: parse, filter, validate, reverse | You process bank statements in Python or from a shell: **this package** |
| [`camt053-mcp`](https://github.com/sebastienrousseau/camt053-mcp) | Model Context Protocol server exposing the library as agent tools | An AI agent reads statements and drafts reversals |
| [`camt053-lsp`](https://github.com/sebastienrousseau/camt053-lsp) | Language Server Protocol server for reversing-entry data files | You author reversal data in an editor with diagnostics |
| [`camt053-loader-mt940`](https://github.com/sebastienrousseau/camt053-loader-mt940) | SWIFT MT940 statements to a camt.053 `ParsedDocument` | Your bank still sends MT940 |
| [`camt053-loader-mt942`](https://github.com/sebastienrousseau/camt053-loader-mt942) | SWIFT MT942 interim reports to a camt.052 `ParsedDocument` | You receive intraday MT942 reports |
| [`camt053-writer-xlsx`](https://github.com/sebastienrousseau/camt053-writer-xlsx) | Excel `.xlsx` writer for parsed statements | Someone downstream wants a spreadsheet |

For outbound payments (pain.001) use the sibling
[`pain001`](https://github.com/sebastienrousseau/pain001) library.

---

## Capabilities at a glance

| Area | Capability | Status |
| :--- | :--- | :--- |
| Parsing | camt.052, camt.053, camt.054, every ISO revision `.001.01` to `.001.14`, namespace-agnostic | Released |
| Filtering | By return reason code, status, booking-date range and amount range | Released |
| Reversal | `camt.053.001.14` reversing entries (also `.001.08` and `pacs.004`), deterministic references | Released |
| Validation | Inbound and generated documents against the bundled official ISO 20022 XSDs | Released |
| Readiness | CBPR+ November 2026 pre-flight (`check_cbpr_readiness`) | Released |
| Interfaces | Python API, CLI, REST API; MCP and LSP through the suite | Released |
| Observability | Structured logging, optional OpenTelemetry spans and metrics | Released |

---

## Ecosystem comparison

The choice inside the suite is which surface to use; every row calls the same
`camt053.services` facade.

| Project | Reads camt.05x | Generates reversals | Interface |
| :--- | :---: | :---: | :---: |
| **camt053** | Yes | Yes | Python, CLI, REST |
| camt053-mcp | Yes | Yes | MCP tools |
| camt053-loader-mt940 / -mt942 | MT940 / MT942 in | Through the core | Python |

See [`docs/COMPARISON.md`](docs/COMPARISON.md) for the evidence and complete matrix.

---

## Benchmarks

Streaming holds peak memory down, and the XSD compiles once per process, so
the first validation costs far more than later ones. Measured with
`benches/bench_statement_pipeline.py` on a shared machine, so wall-clock
figures are ranges over three runs.

| Scenario | Result | Environment |
| :--- | ---: | :--- |
| `parse_statement`, 2,000 entries (531 KiB) | 69 to 167 ms | Apple A18 Pro, Python 3.12.15 |
| `list_entries` peak memory, 10,000 entries | 22,926 KiB streaming, 32,935 KiB buffered | Apple A18 Pro, Python 3.12.15 |
| First `validate_statement` in a process | 0.35 to 3.0 s | Apple A18 Pro, Python 3.12.15, lxml 6.1.3 |
| Later `validate_statement` calls | 28 to 273 ms | Apple A18 Pro, Python 3.12.15, lxml 6.1.3 |

See [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md) for methodology and full results.

---

## Features

- **Parse** camt.053 / camt.052 / camt.054 into a typed, JSON-serialisable
  model. Parsing is **namespace-agnostic**, so every ISO version (`.001.01`
  through `.001.14`) and real-world bank file is read.
- **Filter** booked entries by ISO external return reason code (AC04, AC06,
  MD07, …), and by **status**, **booking-date range**, and **amount range**
  (all ANDed) via `services.filter_entries(...)` or the `camt053 entries`
  flags.
- **Return reason codes**: a substantial slice of the ISO 20022
  `ExternalReturnReason1Code` set (the common SEPA / CBPR+ return reasons),
  listed via `camt053 reasons`, with case-insensitive lookup through
  `services.validate_reason_code(code) -> {"code", "name", "valid"}`.
- **Reason-code action policy**: classify a return reason into a handling
  action (`"return"`, `"retry"`, or `"ignore"`) via
  `services.classify_reason(code) -> {"code", "name", "action"}`, with a
  built-in default (account-level rejections return, transient conditions
  such as `AM04` / `AM05` retry, informational reasons ignore). The full
  mapping is `services.reason_policy()`; both accept an `overrides` mapping
  and a custom `default`. `camt053 classify -r AC04` classifies one code.
- **Export** the (filtered) entries to **CSV** or **JSON** (`camt053 entries
  --export {csv,json} [-o file]`); CSV columns are `reference, amount,
  currency, credit_debit_indicator, status, booking_date, value_date,
  reason_code`.
- **Structured output**: `camt053 entries --format json` emits the entries
  as a JSON array, and `camt053 reverse --format json` emits a
  `{"message_type", "reason_code", "xml"}` envelope instead of raw XML.
- **Reverse**: generate a `camt.053.001.14` reversing entry from the matching
  entries (credit/debit indicator flipped, `RvslInd` set, return reason carried
  in `RtrInf`), in one call.
- **Validated output**: generated reversals are checked against the **official
  ISO 20022 `camt.053.001.14` XSD** bundled with the package.
- **SWIFT charset cleansing**: opt-in cleansing of the name / narrative fields
  bound for SWIFT FIN / CBPR+ rails. Characters outside the **SWIFT X** set
  are transliterated (`é` → `e`, `ß` → `ss`) or stripped, and field maximum
  lengths are enforced. Enable it with
  `services.generate_reversal(xml, cleanse=True)`, or cleanse records directly
  with `services.cleanse_records(records)`, which reports exactly what changed.
- **Validate incoming statements**: `services.validate_statement(xml)` (and
  `camt053 validate`) check an inbound camt.052 / camt.053 / camt.054 document
  against the matching **official ISO 20022 XSD**, detected from its
  namespace, returning `{"valid", "message_type", "errors"}`.
- **Re-serialise (round-trip)**: render a parsed `ParsedDocument` /
  `Statement` back to a validated `camt.053.001.14` document via
  `services.serialize_statement(xml)`. The output is deterministic and
  round-trip stable for the account, balances and entries.
- **Safe by default**: XML is parsed with `defusedxml` (XXE / billion-laughs
  safe); output paths are traversal-checked.
- **IBAN / BIC / LEI validators** (ISO 13616 / 9362 / 17442) and **ISO 4217
  currencies** with minor units (`services.validate_currency`).
- **Typed** (mypy `--strict`) and **tested** (100% line and branch coverage),
  validated against the official ISO 20022 business samples.

### Supported messages

| Message type | Name | Direction |
| :--- | :--- | :--- |
| `camt.052.001.14` | Bank To Customer Account Report | read |
| `camt.053.001.14` | Bank To Customer Statement | read + **reverse** |
| `camt.054.001.14` | Bank To Customer Debit Credit Notification | read |

The parser reads every ISO version of these messages; the official XSDs for
`.001.01` to `.001.14` are bundled under `camt053/xsd/`.

### Error codes

Every exception in [`camt053.exceptions`](camt053/exceptions.py) inherits from
`Camt053Error` and carries a stable, machine-readable `code`, so callers can
switch on `exc.code` rather than the class name or message text.

| Code | Exception | Meaning |
| :--- | :--- | :--- |
| `CAMT053_ERROR` | `Camt053Error` | Base error for any Camt053 failure |
| `ACCOUNT_VALIDATION_ERROR` | `AccountValidationError` | Account/input data failed validation |
| `XML_GENERATION_ERROR` | `XMLGenerationError` | XML rendering or template failure |
| `CONFIGURATION_ERROR` | `ConfigurationError` | Invalid configuration or CLI arguments |
| `DATA_SOURCE_ERROR` | `DataSourceError` | A data source could not be read |
| `SCHEMA_VALIDATION_ERROR` | `SchemaValidationError` | XML did not conform to its ISO 20022 XSD |
| `INVALID_IBAN_ERROR` | `InvalidIBANError` | IBAN format / checksum validation failed |
| `INVALID_BIC_ERROR` | `InvalidBICError` | BIC/SWIFT format validation failed |
| `INVALID_LEI_ERROR` | `InvalidLEIError` | LEI format / checksum validation failed |
| `MISSING_REQUIRED_FIELD_ERROR` | `MissingRequiredFieldError` | A required field was absent |
| `STATEMENT_PARSE_ERROR` | `StatementParseError` | An incoming statement could not be parsed |
| `REVERSAL_GENERATION_ERROR` | `ReversalGenerationError` | A reversing entry could not be generated |

### Robustness

Malformed-but-recoverable statements degrade gracefully. Missing optional
elements read as `None` or empty, unknown elements are ignored (children are
matched by local name), and prefixed, missing or non-ISO namespaces parse the
same way. Non-well-formed XML still raises `StatementParseError`, carrying the
1-based source `line` (and column, where reported).

---

## Configuration

| Setting | Default | Effect |
| :--- | :--- | :--- |
| `CAMT053_MAX_BODY_BYTES` | `1048576` | REST API request-body cap; larger requests get HTTP 413 |
| `CAMT053_LOG_FORMAT` | unset (logging untouched) | `json` or `text` structured logging |
| `CAMT053_LOG_LEVEL` | `INFO` | Level used when `CAMT053_LOG_FORMAT` is set |
| `guard_xml_payload(..., max_bytes=)` | `1048576` | Byte cap for the pre-parse XML guard, per call |
| `generate_reversal(..., cleanse=)` | `False` | SWIFT X charset cleansing of the reversal |

OpenTelemetry is configured through its own standard environment variables
(for example `OTEL_SERVICE_NAME`); camt053 emits spans and metrics only when
the API is installed.

---

## Examples

Twenty-seven runnable, self-contained scripts live in
[`examples/`](examples/), indexed in [`examples/README.md`](examples/README.md)
and executed in CI by `tests/test_examples.py`:

| Example | Demonstrates |
| :--- | :--- |
| [`reverse_ac04.py`](examples/reverse_ac04.py) | The headline workflow: find AC04 entries and generate the reversing entry |
| [`parse_statement.py`](examples/parse_statement.py) | Parsing a statement into the typed model |
| [`services_facade.py`](examples/services_facade.py) | The shared `camt053.services` facade |
| [`validate_identifiers.py`](examples/validate_identifiers.py) | IBAN / BIC / LEI validation |
| [`check_cbpr_readiness.py`](examples/check_cbpr_readiness.py) | The CBPR+ November 2026 pre-flight |
| [`rest_api_client.py`](examples/rest_api_client.py) | Driving the FastAPI REST API in-process |

```sh
git clone https://github.com/sebastienrousseau/camt053.git && cd camt053
python examples/reverse_ac04.py
```

---

## When not to use camt053

- **You need to generate payment files** (pain.001 credit transfers, pain.008
  direct debits). Use [`pain001`](https://github.com/sebastienrousseau/pain001),
  the sibling library for outbound ISO 20022.
- **You need to parse pacs.\* (FI-to-FI) messages.** Out of scope; this
  library targets the camt.05x (Bank-to-Customer) family only.
- **You need bank API transport** (PSD2, EBICS, SWIFTNet). camt053 reads
  files and emits files; it does not move them.
- **You need a GUI.** This is a library, CLI and REST API; the closest thing
  to a UI is the LSP server's in-editor diagnostics.
- **You need real-time processing** (FedNow / TIPS / RTP). Those rails use
  camt.052 intraday reporting; the parser reads camt.052 but the
  reversing-entry workflow is camt.053-shaped.
- **You need authentication on the REST API.** There is none built in; put
  an authenticating gateway in front.

---

## Development

```bash
git clone https://github.com/sebastienrousseau/camt053.git && cd camt053
poetry install
make check        # versions, lint, mypy strict, bandit, complexity, tests, examples
make complexity   # per-function ceilings against complexity-baseline.json
make demo         # re-render .github/demo.gif (needs vhs)
python benches/bench_statement_pipeline.py --quick
```

`make check` runs ruff, black, mypy in strict mode, bandit, the complexity
gate (cyclomatic 10, cognitive 15, Halstead difficulty 30, 60 lines per
function, 500 per file, against a baseline that may only shrink), pytest with
a 100% line and branch coverage gate, and the examples. CI also runs the test
matrix (Linux, macOS, Windows × Python 3.11 to 3.14), pip-audit on the
resolved environment and every hash-pinned requirements file, CodeQL, OpenSSF
Scorecard, a Docker build, and ClusterFuzzLite: five minutes of fuzzing on
every code change and 30 minutes weekly against `fuzz/fuzz_parser.py`. See
[`DEVELOPMENT.md`](DEVELOPMENT.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## Security

`camt053` is the entry point for untrusted XML from banks for every consumer
in the suite. Parsing uses `defusedxml` (XXE and billion-laughs neutralised),
a pre-flight `xml_guard` enforces a byte cap and refuses inline DOCTYPE and
ENTITY declarations, the REST API caps request bodies, and output paths are
traversal-checked. Releases are published to PyPI by Trusted Publishing from a
signed tag, with SLSA build provenance, PEP 740 attestations, sigstore
signatures and CycloneDX and SPDX SBOMs. The parser is fuzzed by
ClusterFuzzLite on every code change; it is not enrolled in OSS-Fuzz. The
project holds the [OpenSSF Best Practices](https://www.bestpractices.dev/projects/13373)
passing badge, and [`SECURITY.md`](SECURITY.md) maps the practices to NIST SSDF.

Report vulnerabilities according to [`SECURITY.md`](SECURITY.md).

---

## Documentation

[User manual](https://sebastienrousseau.github.io/camt053/) ·
[API reference](https://sebastienrousseau.github.io/camt053/api.html) ·
[Developer guide](DEVELOPMENT.md) ·
[Architecture](docs/ARCHITECTURE.md) ·
[Family map](#the-camt053-ecosystem) ·
[Quickstart](docs/quickstart.md) ·
[Deployment cookbook](docs/deployment-cookbook.md) ·
[Version matrix](docs/version-matrix.md) ·
[Changelog](CHANGELOG.md) ·
[Roadmap](ROADMAP.md) ·
[Governance](GOVERNANCE.md) ·
[Support](SUPPORT.md) ·
[Style guide](STYLEGUIDE.md)

---

## Stability guarantees

The project is pre-1.0 and versions advance in `0.0.1` steps, in lockstep
with the rest of the suite. The breaking axis is the public Python API
(`camt053`, `camt053.services`, `camt053.exceptions`), the CLI's commands and
flags, the REST API routes, and the error `code` values, which are unique and
never reused. Output is part of the contract: a change to the XML a reversal
produces, the JSON shape of `parse` or `entries --format json`, or the CSV
columns is breaking even when no signature moves, and is called out in the
[changelog](CHANGELOG.md). The Python floor moves only as described in the
[toolchain policy](docs/POLICIES.md).

---

## License

This project is dual-licensed under either:

* Apache License, Version 2.0 ([`LICENSE-APACHE`](LICENSE-APACHE) or <https://www.apache.org/licenses/LICENSE-2.0>)
* MIT License ([`LICENSE-MIT`](LICENSE-MIT) or <https://opensource.org/licenses/MIT>)

at your option. Any contribution submitted for inclusion is licensed the same
way, without additional terms. Dependencies keep their own licences; the
bundled ISO 20022 XSDs are the published ISO 20022 schemas.

[release-latest]: https://github.com/sebastienrousseau/camt053/releases/latest
