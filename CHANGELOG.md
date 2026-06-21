# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`services.compute_dedupe_key(xml)` and `compute_dedupe_keys(xml)` helpers**
  for exactly-once statement processing (#58 B3). Returns the canonical
  `"{MsgId}:{StmtId}:{ElctrncSeqNb}"` dedupe key per ISO 20022 conventions
  so downstream consumers can detect bank replays (same key → already
  processed). Multi-statement documents expose one key per statement via
  `compute_dedupe_keys`. Colon separator (invalid in ISO 20022 ID fields)
  guarantees the key can be split unambiguously back into its three
  components. New module: `camt053.parse.dedupe`. Constant
  `DEDUPE_KEY_SEPARATOR` re-exported via `camt053.services`.
- **`services.stable_reversal_reference(original)` helper** (#58 B2)
  exposes the deterministic algorithm that the reversal builder already
  uses internally. Default scheme is a human-readable `RVSL-{original}`
  prefix (preserved across releases for navigability in audit logs);
  falls back to a `RVSL-{sha256(original|REV)}` truncated digest when
  the prefixed form would exceed the ISO 20022 35-char ID limit, ensuring
  collision-resistant IDs even for long or adversarial inputs. Pinned by
  property tests; the prefix and salt are load-bearing.

- **`camt053 check-cbpr-readiness -i statement.xml` CLI command**.
  Wraps `services.check_cbpr_readiness`, prints a Rich summary table
  (or `--format json` for the full structured report), and exits 0 if
  the document is CBPR+ ready or 1 if any error-severity issue is
  raised. Warnings (deprecated schema versions) do not affect the
  exit code. Reads stdin with `-i -`.
- **`POST /check/cbpr-readiness` REST endpoint**. Wraps the same
  underlying function and returns the structured report as JSON. HTTP
  status is `200` for any parseable input (CBPR+-not-ready is a
  *result*, not an error); `400` for malformed XML; the existing
  `XmlSecurityError` handler returns `400` for hostile payloads.
  Tagged `compliance` in the OpenAPI spec.
- **`services.check_cbpr_readiness` re-export**. The function and
  `CBPR_CUTOVER_DATE` constant are now available at the
  `camt053.services` facade alongside the other public surfaces so
  the CLI, REST, MCP, and LSP consumers all import from one place.

- **`check_cbpr_readiness(xml)` pre-flight checker** for the coordinated
  CBPR+ / Fedwire / CHAPS / T2 cutover on **14-16 November 2026**.
  Walks a camt.053 payload and reports issues that will fail the
  Nov 2026 acceptance rules: schema-version drift (.02-.07 deprecated;
  .08 / .13 current) and **unstructured-only postal addresses**
  (`AdrLine` without `TwnNm` + `Ctry` siblings, the Nov 2026 reject
  case). Returns a structured report with `cbpr_ready: bool`, per-issue
  XPath-style paths, severities, stable codes, and an
  address-classification summary (fully structured / hybrid /
  unstructured-only). Available via `camt053.compliance.check_cbpr_readiness`
  and the `CBPR_CUTOVER_DATE = "2026-11-16"` constant. Backed by
  `defusedxml` and the existing `xml_guard` byte-cap + DOCTYPE
  pre-flight; raises `XmlSecurityError` / `ValueError` on hostile or
  malformed input. Part of the v0.0.6 batch tracked in #58.

## [0.0.5] - 2026-06-19

### Added

- Property-based (Hypothesis) tests for parser robustness and reversal
  invariants (#25): a new `tests/test_property_based.py` generates plausible
  and edge-case inputs and asserts that a reversing entry flips `CdtDbtInd`,
  sets the reversal indicator, and preserves amount/currency; that the parser
  never crashes on structurally-odd-but-well-formed XML and only ever raises
  `StatementParseError`; that `reverse_credit_debit` is an involution; and that
  serialise→parse round-trips preserve entries (the slower round-trip property
  is marked `slow`).
- Mutation testing with mutmut (#26): `[tool.mutmut]` configuration targeting
  `camt053/`, a documented "Mutation testing" workflow in `CONTRIBUTING.md`,
  and an advisory, non-blocking `mutation` CI job (`continue-on-error`). Not a
  required 100% gate.
- Performance benchmark suite and CI regression guard (#11): a new
  `tests/test_benchmarks.py` (marker `perf`) benchmarks parse + reversal
  generation on a representative statement with pytest-benchmark, a committed
  baseline under `.benchmarks/baseline/`, and a `performance` CI job that
  compares against it and fails only on a large (>200% mean) regression.
  Benchmarks are excluded from the 100% coverage gate (`-m "not perf"` by
  default).
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
- Output camt.053 version selection for generated reversing entries (#8). The
  reversal services now accept a `version` argument selecting the bundled
  camt.053 schema version to emit, validated against the matching official ISO
  XSD. The default is unchanged (`camt.053.001.14`); `camt.053.001.08` is now
  also bundled (template + official XSD) so the selection is real. An unknown
  version raises a clear `ReversalGenerationError`. Surfaced via
  `services.generate_reversal(..., version=...)` / `services.generate(...)` and
  the CLI `camt053 reverse --out-version`.
- Optional pacs.004 PaymentReturn output as an alternative reversal format
  (#7). The same reversing-entry records can now be emitted as a pacs.004
  PaymentReturn document (the canonical ISO "payment return" message) carrying
  and echoing the return reason, validated against a bundled pacs.004.001.11
  XSD. Selected via `services.generate_reversal(..., output_format="pacs004")`
  and the CLI `camt053 reverse --output-format pacs004`. camt.053 remains the
  default.
- Batch processing of multiple statements or a directory (#13). A new
  `services.generate_batch(paths)` processes a list of files, a glob pattern, or
  a directory (scanned recursively for `*.xml`) in one call, producing per-file
  results with an aggregate summary and per-file error isolation (one bad file
  does not abort the batch). Exposed on the CLI as
  `camt053 reverse --batch DIR -o OUTDIR`, writing a per-file reversal to the
  output directory and reporting a succeeded/failed summary.
- Streaming, memory-bounded statement parsing (#10): a new
  `camt053.parse.statement_parser.iter_statement_entries(xml)` generator walks a
  statement with `defusedxml`'s `iterparse`, yielding each `Entry` as its
  `<Ntry>` element closes and clearing the consumed subtree so peak memory stays
  bounded by a single entry rather than the whole document. Exposed via the
  service facade as `services.iter_entries(xml)` and
  `services.list_entries(xml, streaming=True)`; for well-formed input the
  streamed entries are identical to the whole-tree `list_entries(xml)`, in
  document order. XXE / billion-laughs protection is preserved (DTDs and
  external/general entities are still rejected). The parser module docstring
  documents the streaming vs. whole-tree memory trade-offs.
- Hosted documentation site (#5): a `.github/workflows/docs.yml` GitHub Actions
  workflow builds the Sphinx documentation (API reference + Design History
  File) with `sphinx-build` and deploys it to GitHub Pages via
  `actions/configure-pages`, `actions/upload-pages-artifact`, and
  `actions/deploy-pages`. Pull requests build the docs (warnings-as-errors) for
  validation without deploying; pushes to `main` deploy. A new `docs/api.rst`
  page documents the public `camt053` / `camt053.services` / `camt053.exceptions`
  API via autodoc.
- Dependency vulnerability audit and coverage reporting in CI (#15): a new
  advisory `audit` job runs `pip-audit` against the resolved Poetry environment
  on every push/PR, and the `test` job now uploads the generated `coverage.xml`
  as a build artifact. The audit is advisory (`continue-on-error`) because the
  only outstanding findings are CVEs in the runner's own `pip` build tool, not
  in any project runtime dependency (the project's dependencies audit clean).
- GHCR Docker image publishing for the REST API (#31): a new
  `.github/workflows/docker.yml` builds the existing `Dockerfile` and pushes
  `ghcr.io/sebastienrousseau/camt053` tagged with the release version and
  `latest` on `release: published` (and `workflow_dispatch`), independent of the
  PyPI publish job and never running on PRs. A PR-safe `docker-build`
  validation job in CI builds the image (no push) to catch Dockerfile breakage.
- CycloneDX SBOM attached to releases (#32): a separate `sbom` job in the
  release workflow generates a CycloneDX SBOM with `cyclonedx-bom` and uploads
  it as a release asset via `gh release upload`. It is isolated from the PyPI
  `publish` job so an SBOM failure cannot block the package release.
- OpenSSF Scorecard workflow and README badge (#33): a new
  `.github/workflows/scorecard.yml` runs `ossf/scorecard-action` on a schedule,
  on push to `main`, and on `branch_protection_rule` (not on pull requests, so
  its code-scanning findings cannot block merges), publishing results and a
  Scorecard badge now shown in the README.

### Changed

- Cache compiled XSDs and the Jinja2 environment for faster repeated parsing,
  validation, and generation (#27): a new `camt053.xml.template_env` module
  memoises one autoescaping Jinja2 `Environment` per template directory and one
  compiled template per `(directory, name)` pair, so repeated `generate` /
  `serialize` calls reuse the compiled template instead of rebuilding it. The
  compiled XSD schema cache (`functools.lru_cache`) is now also exercised by the
  statement serialiser. Public APIs are unchanged and the cached artefacts are
  read-only, so no state leaks between documents.

### Fixed

- Broken `camt053.com` documentation links and badges (#4): the unresolved
  `https://camt053.com` website/documentation links and the "Docs" badge in
  `README.md` now point at the hosted GitHub Pages site
  (`https://sebastienrousseau.github.io/camt053/`), and the project `homepage`
  in `pyproject.toml` is repointed to the same URL.

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

[0.0.5]: https://github.com/sebastienrousseau/camt053/releases/tag/v0.0.5
[0.0.4]: https://github.com/sebastienrousseau/camt053/releases/tag/v0.0.4
[0.0.3]: https://github.com/sebastienrousseau/camt053/releases/tag/v0.0.3
[0.0.2]: https://github.com/sebastienrousseau/camt053/releases/tag/v0.0.2
[0.0.1]: https://github.com/sebastienrousseau/camt053/releases/tag/v0.0.1
