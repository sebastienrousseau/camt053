# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
