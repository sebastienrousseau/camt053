<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->

# AGENTS.md

Invariants for AI-assisted contributions to `camt053`. Read this before changing anything.

Everything here applies equally to humans and automated agents. It is addressed to agents because agents can make breaking changes across multiple files before anyone notices.

## What this repository is

`camt053` is the core of the camt053 suite: the library, CLI and REST API that read ISO 20022 camt.052, camt.053 and camt.054 statements, find entries by return reason code, and generate reversing entries validated against the official ISO 20022 XSDs. Every other member (`camt053-mcp`, `camt053-lsp`, the MT940 and MT942 loaders, the Excel writer) calls its `camt053.services` facade, so a change here reaches all of them. Its core value is that what it emits is correct: a reversal that does not validate is never returned.

## 1. Core Invariants

1. **Versioning**: releases stay on the `0.0.x` line and increment strictly by `0.0.1`. Version work happens on `feat/v<next-version>` only. `v0.1.0` follows `v0.0.999`.
2. **Suite lockstep**: every member ships the core's version, and the core releases first. `scripts/check_suite_consistency.py` is the shared copy every member carries (only `THIS` differs); change it in every member or not at all.
3. **Single source of truth**: the version in `pyproject.toml` must agree with `camt053/__init__.py`, `camt053/constants.py`, `CHANGELOG.md`, `CITATION.cff`, the README's latest-release line and `SECURITY.md` (checked by `scripts/verify_versions.py`). `docs/conf.py` reads it from `pyproject.toml`.
4. **Output is the contract**: a change to the XML a reversal produces, the JSON shape of `parse` or `entries --format json`, the CSV columns, or an error `code` is breaking even when no signature moves.
5. **Untrusted input**: inbound XML is parsed with `defusedxml` only. Never add a parser path that resolves DTDs or external entities.
6. **Dual licensing**: Apache-2.0 OR MIT.

## 2. Before You Claim To Be Done

```console
make check
```

It runs the version check, ruff, black, mypy `--strict`, bandit, the complexity gate, pytest (100% line and branch coverage) and the examples. Every function stays within cyclomatic 10, cognitive 15, Halstead difficulty 30 and 60 lines, every file within 500 lines; existing offenders are in `complexity-baseline.json`, which may only shrink.

## 3. Hygiene First

Before any feature, fix or release work: open Dependabot PRs and alerts, code-scanning and secret-scanning alerts, `pip-audit`, and a red CI on `main` are cleared first. A dependency with an advisory is floored in `pyproject.toml` (and the `requirements/*.in` it appears in) so no affected version resolves.

## 4. Leave Alone

- `tests/test_suite_conformance.py` is a vendored, checksummed copy shared across the suite; it is excluded from black for that reason.
- `camt053/xsd/` holds the official ISO 20022 schemas, verbatim.
- `poetry.lock` and `requirements/*.txt` are generated (`poetry lock`, `make pip-compile`); never hand-edit them.
- `.benchmarks/baseline/` is the performance baseline the advisory CI job compares against.
