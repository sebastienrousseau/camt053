<!-- markdownlint-disable MD033 MD041 -->

<img src="https://kura.pro/camt053/images/logos/camt053.svg" alt="camt053 logo" width="66" align="right" />

<!-- markdownlint-enable MD033 MD041 -->

# camt053

A Python library for the modern, AI-assisted treasury stack: read ISO 20022
**camt** Bank-to-Customer Cash Management messages, extract booked entries by
return reason code (e.g. **AC04 — Closed Account**), and generate **validated
reversing entries**.

[![Made With Love][made-with-python]][00]
[![License][license-badge]][01]
[![Codecov][codecov-badge]][02]

camt053 is the core of a three-package stack with native AI and editor
integrations:

| Package | Role |
|---------|------|
| **`camt053`** | Core library, CLI, and REST API |
| [`camt053-mcp`][mcp] | Model Context Protocol server — exposes camt053 as tools for AI agents (Claude Desktop, IDEs) |
| [`camt053-lsp`][lsp] | Language Server — diagnostics, completion, and hover for reversing-entry data files |

## The prompt-engineering dream

> *"Hey Claude, read this incoming bank statement XML, parse out the
> transactions with error code AC04, and automatically generate the reversing
> entry."*

That is one function call:

```python
from camt053 import services

reversal_xml = services.generate_reversal(incoming_statement_xml, reason_code="AC04")
```

`generate_reversal` parses the camt.053 statement, selects the entries returned
with reason **AC04 (Closed Account)**, flips each entry's credit/debit
indicator, sets `RvslInd`, carries the return reason in `RtrInf`, and validates
the result against the **official ISO 20022 `camt.053.001.14` XSD** before
returning it.

## Features

- **Parse** camt.053 (Bank to Customer Statement), camt.052 (Account Report),
  and camt.054 (Debit Credit Notification) — into a typed, JSON-serialisable
  model. Parsing is **namespace-agnostic**, so every ISO version (`.001.01`
  through `.001.14`) is read, and real-world bank files Just Work.
- **Filter** entries by ISO external return reason code (AC04, AC06, MD07, …).
- **Reverse** — generate a validated `camt.053.001.14` reversing entry from the
  matching entries, in one call.
- **Validated output** — generated reversals are checked against the official
  ISO 20022 XSD shipped with the package.
- **Safe by default** — XML is parsed with `defusedxml` (XXE / billion-laughs
  safe); output paths are traversal-checked.
- **One facade, four interfaces** — the CLI, REST API, MCP server, and LSP
  server all call the same `camt053.services` layer, so they behave identically.
- **IBAN / BIC / LEI validators** (ISO 13616 / 9362 / 17442).
- **Typed** (mypy strict) and **tested** (99%+ coverage), validated against the
  official ISO 20022 business samples.

## Installation

```sh
pip install camt053          # Python 3.10+
```

From source:

```sh
git clone https://github.com/sebastienrousseau/camt053.git
cd camt053
poetry install
```

## Quick start

### Python

```python
from camt053 import services, parse_statement

# 1. Inspect the statement.
stmt = parse_statement(incoming_xml)
print(stmt.account.identifier(), len(stmt.entries), "entries")

# 2. Which entries were returned AC04?
ac04 = services.filter_entries(incoming_xml, "AC04")

# 3. Generate the reversing entry (validated camt.053.001.14 XML).
reversal_xml = services.generate_reversal(incoming_xml, reason_code="AC04")
```

### CLI

```sh
# Generate a reversing entry for every AC04 entry on a statement
camt053 reverse -i statement.xml -r AC04 -o reversal.xml

# List the entries on a statement (optionally filtered by reason)
camt053 entries -i statement.xml -r AC04

# Inspect the parsed statement as JSON
camt053 parse -i statement.xml

# Reference data
camt053 message-types
camt053 reasons

# Validate an identifier
camt053 validate-id -k iban -v GB29NWBK60161331926819
```

The `reverse` and `parse`/`entries` commands accept `-i -` to read from stdin,
so they compose in a pipeline.

### REST API

```sh
uvicorn camt053.api.app:app --reload
```

```sh
curl -s -X POST localhost:8000/reverse \
  -H 'content-type: application/json' \
  -d '{"xml": "<Document>…</Document>", "reason_code": "AC04"}'
```

Endpoints: `GET /health`, `GET /message-types`, `GET /reasons`,
`GET /message-types/{type}/schema`, `GET /message-types/{type}/required-fields`,
`GET /validate-identifier`, `POST /validate-records`, `POST /parse`,
`POST /entries`, `POST /reverse`.

## Supported messages

| Message type | Name | Direction |
|--------------|------|-----------|
| `camt.052.001.14` | Bank To Customer Account Report | read |
| `camt.053.001.14` | Bank To Customer Statement | read + **reverse** |
| `camt.054.001.14` | Bank To Customer Debit Credit Notification | read |

The parser is namespace-agnostic and reads every ISO version of these messages;
the official XSDs for `.001.01`–`.001.14` are bundled under `camt053/xsd/`.
Reversing entries are generated as `camt.053.001.14`.

## How the reversing entry is built

For each selected entry, camt053:

1. flips the credit/debit indicator (`CRDT` ⇄ `DBIT`),
2. sets `RvslInd` to `true`,
3. carries the original references (`InstrId` / `EndToEndId` / `TxId`),
4. records the return reason in `RtrInf/Rsn/Cd` with a human-readable
   `AddtlInf`,
5. preserves the counterparty (`RltdPties`), and
6. validates the whole document against the official ISO 20022
   `camt.053.001.14` XSD.

## Architecture

```text
            ┌─────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────────┐
            │   CLI   │  │ REST API │  │  MCP server  │  │  LSP server  │
            └────┬────┘  └────┬─────┘  └──────┬───────┘  └──────┬───────┘
                 └───────────┴───────────────┴─────────────────┘
                                     │
                          camt053.services  (one facade)
                                     │
        ┌────────────────┬───────────┴────────────┬──────────────────┐
     parse/            reversal/                 xml/             validation/
  statement_parser   reversal builder    template + ISO XSD     IBAN/BIC/LEI
```

## Companion packages

- **[`camt053-mcp`][mcp]** — a Model Context Protocol server exposing
  `parse_statement`, `filter_entries`, `generate_reversal`, and the reference
  and validation tools to AI agents over stdio.
- **[`camt053-lsp`][lsp]** — a Language Server that gives diagnostics,
  completion, and hover when authoring reversing-entry data files in your
  editor.

## Development

```sh
make dev          # install with dev dependencies
make test         # pytest with coverage (99% gate)
make lint         # ruff + black --check
make type-check   # mypy --strict
make check        # everything
```

## License

Licensed under the [Apache License, Version 2.0][01].

[00]: https://www.python.org/
[01]: https://www.apache.org/licenses/LICENSE-2.0
[02]: https://codecov.io/gh/sebastienrousseau/camt053
[mcp]: https://github.com/sebastienrousseau/camt053-mcp
[lsp]: https://github.com/sebastienrousseau/camt053-lsp
[made-with-python]: https://img.shields.io/badge/Made%20with-Python-1f425f.svg?style=for-the-badge
[license-badge]: https://img.shields.io/badge/license-Apache%202.0-blue.svg?style=for-the-badge
[codecov-badge]: https://img.shields.io/codecov/c/github/sebastienrousseau/camt053?style=for-the-badge
