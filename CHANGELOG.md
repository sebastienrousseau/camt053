# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Configurable reason-code action policy mapping ISO return reason codes to a
  handling action (`return` / `retry` / `ignore`) with a sensible built-in
  default (account-level rejections such as AC01/AC04/AC06/AC13 return,
  transient conditions such as AM04/AM05 retry, informational reasons ignore;
  unknown / unmapped codes fall back to a configurable default). Exposed via
  `services.classify_reason(code) -> {"code", "name", "action"}` and
  `services.reason_policy() -> {"default", "actions", "policy"}` (both accept
  an `overrides` mapping and a custom `default`); surfaced on the CLI as an
  Action column on `camt053 reasons` and a new `camt053 classify -r AC04`
  command (#24)
- Add a `--format {table,json}` option to the `camt053 entries` and
  `camt053 reverse` commands (`table` is the default). For `entries`, `json`
  emits the (optionally filtered) entries as a JSON array; for `reverse`,
  `json` emits a `{"message_type", "reason_code", "xml"}` envelope instead
  of raw XML. The `parse` command accepts `--format json` as a no-op alias
  for symmetry. Exit codes are unchanged (#9)
- Ship a PEP 561 `py.typed` marker so downstream projects pick up the
  library's inline type hints (#3)
- `services.validate_statement(xml)` and a `camt053 validate` CLI command
  that validate an incoming camt.052 / camt.053 / camt.054 document against
  the matching official ISO 20022 XSD (detected from its namespace),
  returning a `{"valid", "message_type", "errors"}` report (#17)
- Filter statement entries by `status`, booking-date range (`date_from` /
  `date_to`), and amount range (`min_amount` / `max_amount`) — all ANDed
  with the existing reason filter — via `services.filter_entries(...)` and
  new `--status` / `--from` / `--to` / `--min` / `--max` flags on the
  `camt053 entries` command (#21)
- Export parsed (and optionally filtered) entries to CSV or JSON via the
  `camt053 entries --export {csv,json}` option, to stdout or a file
  (`-o/--output`); CSV ships a stable, documented column set and an empty
  statement yields a header-only CSV / `[]` JSON (#23)
- Expose amounts as `Decimal` via `Entry.amount_decimal` and
  `Balance.amount_decimal` (the string `amount` is kept verbatim for XML
  fidelity; empty/invalid values yield `None`), and add an ISO 4217 currency
  validator (`camt053.validation.currency_validator` with
  `validate_currency(code)` and `currency_minor_units(code)`) plus
  `services.validate_currency(code) -> {"code", "valid", "minor_units"}`
  (EUR=2, JPY=0, BHD=3, …) (#22)
- Expand the ISO 20022 `ExternalReturnReason1Code` table to cover the
  common SEPA / CBPR+ return reasons (AC01–AC14, AG01/AG02, AM01–AM09,
  BE01/BE05, CNOR/DNOR, DT01, ED01/ED05, FF01, MD01/MD06/MD07, MS02/MS03,
  NARR/NOAS/NOOR, RC01, RR01–RR04, SL01, TM01) with their official names,
  and add `services.validate_reason_code(code) -> {"code", "name", "valid"}`
  (case-insensitive; unknown codes report `valid=False`); the full set is
  listed by `camt053 reasons` (#12)
- Give every exception in `camt053.exceptions` a stable, unique class-level
  `code` (e.g. `STATEMENT_PARSE_ERROR`, `REVERSAL_GENERATION_ERROR`) so
  consumers can switch on `exc.code` without depending on class names or
  message text; documented as a code → meaning table in the module
  docstring and the README (#30)

### Fixed

- Reverse matching entries across **all** statements in a document, not
  just the first; a return reason carried only by a later statement is no
  longer missed (#20)

## [0.0.1] - 2026-06-17

### Added

- Initial release of the camt053 library for ISO 20022 camt
  Bank-to-Customer Cash Management messages (2025/2026 maintenance
  release, variant `.001.14`)
- Namespace-agnostic statement parser for camt.053 (Bank to Customer
  Statement), camt.052 (Account Report), and camt.054 (Debit Credit
  Notification), into a typed model (group header, statements, accounts,
  balances, entries, and transaction details)
- Return-reason extraction and filtering, including the headline AC04
  (Closed Account) case, with a table of common ISO external return
  reason codes
- Reversing-entry generation: a one-shot workflow that reads an incoming
  statement, selects the entries carrying a given return reason, and emits
  a validated camt.053.001.14 reversal statement (credit/debit indicator
  flipped, `RvslInd` set, return reason carried in `RtrInf`)
- Generated reversals are validated against the **official ISO 20022
  camt.053.001.14 XSD** bundled with the package
- Shared service facade (`camt053.services`) backing the CLI, REST API,
  MCP server, and LSP server, so every interface behaves identically
- Click + Rich CLI (`camt053`) with `parse`, `entries`, `reverse`,
  `message-types`, `reasons`, and `validate-id` commands
- FastAPI REST API with parse, entries, reverse, validation, and
  reference endpoints
- IBAN, BIC, and LEI validators (ISO 13616 / ISO 9362 / ISO 17442)
- JSON Schema validation for the flat reversing-entry record vocabulary
- Path-traversal protection and XXE-safe XML parsing (`defusedxml`)
- Companion package `camt053-mcp`: a Model Context Protocol server
  exposing camt053 as agent tools (Python 3.10+)
- Companion package `camt053-lsp`: a Language Server for authoring
  reversing-entry data with diagnostics, completion, and hover
  (Python 3.10+)

[0.0.1]: https://github.com/sebastienrousseau/camt053/releases/tag/v0.0.1
