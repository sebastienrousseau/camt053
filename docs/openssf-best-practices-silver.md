# OpenSSF Best Practices Badge — Silver submission

Step-by-step submission pack for the
[OpenSSF Best Practices Badge program](https://www.bestpractices.dev/).
Designed so the maintainer can paste each answer verbatim into the
web form at https://www.bestpractices.dev/projects/new and reach
Silver in one sitting.

Three projects file separately (one badge per repo); the answers
overlap substantially.

## Projects to submit

1. **`camt053`** — https://github.com/sebastienrousseau/camt053
2. **`camt053-mcp`** — https://github.com/sebastienrousseau/camt053-mcp
3. **`camt053-lsp`** — https://github.com/sebastienrousseau/camt053-lsp

Submit each as a separate badge. The Bronze + Silver criteria
shared across the three are below; project-specific notes follow.

## Identity (every project)

| Field | Value |
| :--- | :--- |
| Name | `camt053` / `camt053-mcp` / `camt053-lsp` |
| Description | See the project's `glama.json` `description` or README opening paragraph |
| Project home URL | the GitHub repo page |
| Repository URL | the GitHub repo page |
| What programming language(s) does the project use? | Python |

## Bronze answers (every project)

Every Bronze answer has `Met`-tier evidence and a single short URL
to point at.

### Basics

| Criterion | Answer | Evidence |
| :--- | :--- | :--- |
| `description_good` | Met | `README.md` opening paragraph |
| `interact` | Met | `SUPPORT.md` (links to Discussions + Issues + Security Advisories) |
| `contribution` | Met | `CONTRIBUTING.md` |
| `contribution_requirements` | Met | `CONTRIBUTING.md` — submission + style + signed commits + branch policy |
| `floss_license` | Met | `LICENSE` (Apache-2.0) |
| `floss_license_osi` | Met | Apache-2.0 is OSI-approved |
| `license_location` | Met | `LICENSE` at repo root |

### Change Control

| Criterion | Answer | Evidence |
| :--- | :--- | :--- |
| `repo_public` | Met | The repo is on github.com and public |
| `repo_track` | Met | git history available since first commit |
| `repo_distributed` | Met | git is a distributed VCS |
| `version_unique` | Met | every release has a unique signed git tag `vX.Y.Z` |
| `version_semver` | Met | `pyproject.toml` declares SemVer in the `[project]` metadata |
| `release_notes` | Met | `CHANGELOG.md` + `releases/vX.Y.Z.md` per release |
| `release_notes_vulns` | Met | every security fix is announced in the GitHub Security Advisory and cross-referenced in `CHANGELOG.md` |

### Reporting

| Criterion | Answer | Evidence |
| :--- | :--- | :--- |
| `report_process` | Met | `SECURITY.md` — coordinated disclosure with 3-day ack / 7-day assessment / 30-day fix |
| `report_tracker` | Met | GitHub Issues |
| `report_responses` | Met | last-quarter response rate visible in the repo's issue history |
| `enhancement_responses` | Met | every feature request gets a maintainer response within 7 days (see closed-issue history) |
| `report_archive` | Met | GitHub Issues are public + archived |
| `vulnerability_report_process` | Met | `SECURITY.md` — GitHub Security Advisories + maintainer email |
| `vulnerability_report_private` | Met | "Please do not report security vulnerabilities through public GitHub issues" line + private channels |
| `vulnerability_report_response` | Met | 3-day acknowledgement target documented in `SECURITY.md` |

### Quality

| Criterion | Answer | Evidence |
| :--- | :--- | :--- |
| `build` | Met | `python -m build` (Poetry-backed) produces the wheel + sdist |
| `build_common_tools` | Met | Poetry (universally available via `pip install poetry`) |
| `build_floss_tools` | Met | Poetry is Apache-2.0 |
| `test` | Met | `pytest tests/` |
| `test_invocation` | Met | `pytest tests/` documented in `CONTRIBUTING.md` and `README.md` |
| `test_most` | Met | 100% line + branch coverage enforced via `--cov-fail-under=100` |
| `test_policy` | Met | `CONTRIBUTING.md` — every PR adds a test for new functionality |
| `tests_are_added` | Met | every PR in the recent history adds the corresponding tests |
| `tests_documented_added` | Met | `STYLEGUIDE.md` documents the "tests-with-the-code" policy |
| `warnings` | Met | ruff + black + bandit + mypy strict on every PR |
| `warnings_fixed` | Met | CI rejects PRs that introduce new warnings (`--strict-markers`, mypy strict) |
| `warnings_strict` | Met | mypy is run with `--strict` |

### Security

| Criterion | Answer | Evidence |
| :--- | :--- | :--- |
| `know_secure_design` | Met | `SECURITY.md` "NIST SSDF practice mapping" section |
| `know_common_errors` | Met | `bandit -ll` in CI; ruff `S` security rule family enabled |
| `crypto_published` | Met | HMAC-SHA-256 + sigstore (Fulcio + Rekor); no custom crypto |
| `crypto_call` | Met | uses `hashlib` + `cryptography` only |
| `crypto_floss` | Met | both Apache-2.0 |
| `crypto_keylength` | Met | SHA-256 minimum |
| `crypto_working` | Met | tested in CI |
| `crypto_pfs` | N/A | no transport-layer crypto in scope (it terminates at the reverse proxy / PyPI / sigstore) |
| `crypto_password_storage` | N/A | no user passwords stored |
| `crypto_random` | Met | `secrets` module for any token generation |
| `delivery_mitm` | Met | PyPI HTTPS + sigstore attestation verification on every wheel |
| `delivery_unsigned` | Met | every release wheel carries a PEP 740 sigstore attestation |

### Analysis

| Criterion | Answer | Evidence |
| :--- | :--- | :--- |
| `static_analysis` | Met | mypy strict + ruff |
| `static_analysis_common_vulnerabilities` | Met | bandit (CWE-78, CWE-89, CWE-94, etc.) |
| `static_analysis_fixed` | Met | CI rejects PRs that introduce new bandit findings |
| `dynamic_analysis` | Met | property tests via Hypothesis (`tests/test_property_based.py`) |

## Silver-tier answers (every project)

Silver adds the following Met / N/A criteria. Bronze must already pass.

### Quality (Silver)

| Criterion | Answer | Evidence |
| :--- | :--- | :--- |
| `repo_interim` | Met | repo carries multiple interim commits between releases; CI green at every merge |
| `coding_standards` | Met | `STYLEGUIDE.md` |
| `coding_standards_enforced` | Met | ruff + black in CI |
| `build_reproducible` | Met | `poetry build` with lockfile pinning produces deterministic dist |
| `installation_common` | Met | `pip install <project>` — works on every supported Python (3.10/3.11/3.12) |
| `installation_standard_variables` | Met | follows PEP 517 / 518 build metadata |
| `installation_development_quick` | Met | `pip install -e '.[dev]'` per `CONTRIBUTING.md` |
| `documentation_roadmap` | Met | `ROADMAP.md` |
| `documentation_architecture` | Met | `docs/` (Sphinx) including the API reference + the schema-version matrix |
| `documentation_security` | Met | `SECURITY.md` includes the NIST SSDF mapping table |
| `documentation_quick_start` | Met | `docs/quickstart.md` (10-minute install-to-first-use) |
| `documentation_current` | Met | every PR updates the relevant docs (enforced in PR review) |
| `documentation_examples` | Met | runnable scripts in `examples/` exercised in CI |
| `documentation_achievements` | Met | OpenSSF Scorecard badge + CI badge in `README.md` |
| `documentation_interface` | Met | `docs/api.rst` (Sphinx autodoc) — every public function, class, method |
| `accessibility_best_practices` | Met | docs use semantic Markdown headings; no critical UI surface |
| `internationalization` | N/A | text strings target operator-readable English; no UI surface |

### Security (Silver)

| Criterion | Answer | Evidence |
| :--- | :--- | :--- |
| `crypto_used_network` | N/A | no network communications in the library itself (sigstore + PyPI + GitHub use their own TLS) |
| `crypto_tls12` | N/A | as above |
| `crypto_certificate_verification` | N/A | as above |
| `crypto_verification_private` | N/A | as above |
| `crypto_credential_agility` | Met | every key reference is a parameter (HMAC key, sigstore identity) — no hardcoded credentials |
| `signed_releases` | Met | every release tag is signed (SSH ed25519); every wheel carries a SLSA Build L3 + PEP 740 sigstore attestation |
| `version_tags_signed` | Met | git tags are signed and verifiable via `git tag -v` |

### Analysis (Silver)

| Criterion | Answer | Evidence |
| :--- | :--- | :--- |
| `static_analysis_often` | Met | runs on every PR + on push to main |
| `dynamic_analysis_unsafe` | Met | bandit + ruff `S` cover the unsafe-API checks; defusedxml is used wherever XML is parsed |
| `dynamic_analysis_enable_assertions` | Met | pytest assertions are enabled in CI runs |
| `dynamic_analysis_fixed` | Met | CI fails on new Hypothesis property-test failures |

### Change Control (Silver)

| Criterion | Answer | Evidence |
| :--- | :--- | :--- |
| `previous_versions` | Met | every release is downloadable from GitHub Releases and PyPI; no release ever yanked |
| `bug_reporting_process` | Met | `SUPPORT.md` lists the bug-reporting channels |
| `bug_reporting_responses` | Met | last-quarter median response time visible in issue history (target < 7 days) |
| `enhancement_responses` | Met | as above for feature requests |

## Project-specific notes

### `camt053` (core)

- `interface_documentation`: `docs/api.rst` covers every public callable in `camt053.services`, `camt053.parse`, `camt053.compliance`, `camt053.audit`, `camt053.telemetry`, `camt053.profiles`, `camt053.schema_version`.
- `dynamic_analysis`: `tests/test_property_based.py` exercises the sum-of-entries / reversal-round-trip invariants with Hypothesis.
- `installation_common`: `pip install camt053` (PyPI).

### `camt053-mcp`

- `interface_documentation`: 15 tools + 2 resources + 4 prompts; each documented in `README.md` Tools / Resources / Prompts tables and the `docs/quickstart.md`.
- `installation_common`: `pip install camt053-mcp`.

### `camt053-lsp`

- `interface_documentation`: 7 LSP capabilities (diagnostics, completion, hover, code-actions, document-symbols, formatting, XML diagnostics) each backed by a pure helper documented in `README.md`.
- `installation_common`: `pip install camt053-lsp`.

## After submission

1. Once each badge is granted, copy the badge URL into the README's
   badge row, between the existing `OpenSSF Scorecard` and
   `Documentation` badges.
2. The badge URL pattern is
   `https://www.bestpractices.dev/projects/<ID>/badge` and the
   project page is
   `https://www.bestpractices.dev/projects/<ID>`. Track both in
   the corresponding `SECURITY.md` "Supply-chain" line.
3. Schedule the **Gold** application for v0.0.8+ — Gold needs the
   "two reviewers" change-control criterion which requires either
   a second project maintainer or a formal sign-off process.
