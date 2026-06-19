# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Optional structured JSON logging with PII redaction (#28). A new
  `camt053.logging` module emits one structured JSON record per log line
  (`timestamp`, `level`, `event`, and structured `context`) and redacts
  sensitive banking fields (IBAN keeps only its last four characters, BIC keeps
  its institution prefix, party/owner names keep only an initial, and amounts
  are masked) before any record reaches a handler. Logging is **off by
  default** so importing `camt053` neither configures handlers nor changes the
  root logger; callers opt in programmatically via
  `services.configure_logging()` / `camt053.logging.configure_logging()` or via
  the `CAMT053_LOG_FORMAT` (`json` / `text`) and `CAMT053_LOG_LEVEL`
  environment variables read by `configure_logging_from_env()`. Meaningful log
  points are wired through parsing (`statement.parsed` /
  `statement.parse.failed`) and reversal generation (`reversal.generated`).
  Redaction helpers (`redact_iban`, `redact_bic`, `redact_name`,
  `redact_context`) are public.
- Defense-in-depth hardening of the REST API against untrusted/malicious XML
  (#29). The FastAPI app enforces a configurable maximum request-body size
  (`CAMT053_MAX_BODY_BYTES`, default 1 MiB) via middleware, rejecting oversized
  payloads with a structured HTTP `413` — checking both the declared
  `Content-Length` and the measured streamed body so an understated length
  cannot smuggle an oversized payload through. A new
  `camt053.security.xml_guard` module (exposed as `services.guard_xml()`) runs
  a parser-agnostic pre-flight check that rejects any inline `DOCTYPE` /
  `ENTITY` declaration (neutralising XXE and "billion laughs" entity-expansion
  bombs) and enforces a byte-size limit before the payload reaches the parser,
  complementing the existing `defusedxml` parsing. Malformed or malicious input
  now returns structured 4xx error objects rather than 5xx responses or stack
  traces. Security-marked tests prove oversized payloads → 413, malformed XML →
  4xx, and XXE/entity payloads are rejected cleanly.

## [0.0.4] - 2026-06-19

### Changed

- Version-alignment release with no functional code changes. This bump keeps the
  `camt053`, `camt053-mcp`, and `camt053-lsp` packages in lockstep at a single
  shared version. The companion packages shipped governance and security
  additions in their `0.0.4` releases; core's code is unchanged and is versioned
  to `0.0.4` solely to maintain a consistent version across the suite.

## [0.0.3] - 2026-06-19

### Fixed

- The version reported by `camt053.__version__`, `camt053 --version`, and the
  REST API now matches the package version. It was previously stuck at `0.0.1`
  because the in-code version strings were not bumped alongside
  `pyproject.toml`. Added a pyproject↔code version-consistency test to prevent
  this drift recurring.

## [0.0.2] - 2026-06-18

### Added

- Re-serialise a parsed statement back to camt.053 XML (round-trip): a new
  `camt053.xml.serialize_statement` module renders a parsed `ParsedDocument` /
  `Statement` back to a validated `camt.053.001.14` document via a Jinja2
  statement template, exposed as `services.serialize_statement(xml)` and
  `camt053.serialize_document` / `camt053.serialize_statement`. The output is
  deterministic and round-trip stable:
  `parse_document(serialize_statement(parse_document(xml)))` preserves the
  account, balances, and entries (references, amounts, currencies,
  credit/debit indicators, and return reasons); schema-mandatory elements
  absent from the source are filled with safe defaults so the document still
  validates against the bundled XSD (#18)
- SWIFT charset cleansing of name / narrative fields (`Nm` / `AddtlInf` /
  party / counterparty names) bound for SWIFT FIN / CBPR+ rails: a new
  `camt053.compliance` module transliterates or strips characters outside the
  SWIFT X charset (`é` → `e`, `ß` → `ss`, smart quotes / dashes folded) and
  enforces field maximum lengths, returning a `FieldCleansing` audit report of
  what changed. Wired into the reversal path as opt-in
  (`services.generate_reversal(xml, cleanse=True)` /
  `services.generate(records, cleanse=True)`, default off so existing golden
  output is unchanged) and exposed directly via
  `services.cleanse_records(records) -> {"changed", "fields"}`. Cleansed
  reversals still validate against the bundled XSD (#19)
- Resilient parsing of malformed-but-recoverable statements: missing optional
  elements degrade gracefully (read as `None` / empty), unknown / extra
  elements and unexpected namespaces and prefixes are ignored rather than
  fatal, while genuinely non-well-formed XML still raises a
  `StatementParseError` carrying precise source context (1-based `line`, plus
  column where the parser reports one). Recovery limits are documented in the
  parser module docstring and covered by a dedicated resilience test suite
  (#16)
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
- Add a security policy (`SECURITY.md`) describing supported versions and the
  coordinated-disclosure process, a Dependabot configuration keeping the `pip`
  and `github-actions` ecosystems up to date weekly, and a weekly CodeQL code
  scanning workflow for Python (#14)
- Add GitHub issue templates (bug report and feature request, the latter
  prompting for an `As a / I want / So that` user story and `Given/When/Then`
  acceptance criteria), a pull-request template, and a `CODEOWNERS` file;
  expand `CONTRIBUTING.md` with the protected-branch requirements, the 100%
  coverage gate, the ruff / black / mypy toolchain, and signed-commit
  guidance (#34)

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

[0.0.4]: https://github.com/sebastienrousseau/camt053/releases/tag/v0.0.4
[0.0.3]: https://github.com/sebastienrousseau/camt053/releases/tag/v0.0.3
[0.0.2]: https://github.com/sebastienrousseau/camt053/releases/tag/v0.0.2
[0.0.1]: https://github.com/sebastienrousseau/camt053/releases/tag/v0.0.1
