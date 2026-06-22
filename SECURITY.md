# Security Policy

The camt053 maintainers take the security of this project seriously. This
document explains which versions receive security updates and how to report a
vulnerability responsibly.

## Supported Versions

Security fixes are applied to the latest released minor version. While the
project is in its `0.0.x` series, only the most recent release line receives
security updates.

| Version | Supported          |
| ------- | ------------------ |
| 0.0.x   | :white_check_mark: |
| < 0.0.1 | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues,
discussions, or pull requests.**

We support coordinated disclosure. To report a vulnerability, use either of the
following private channels:

- **GitHub Security Advisories** (preferred): open a private report via the
  repository's
  [Security tab → "Report a vulnerability"](https://github.com/sebastienrousseau/camt053/security/advisories/new).
- **Email**: contact the maintainer at
  [sebastian.rousseau@gmail.com](mailto:sebastian.rousseau@gmail.com).

When reporting, please include as much of the following as possible:

- A description of the vulnerability and its potential impact.
- Steps to reproduce, or a proof-of-concept.
- The affected version(s) and environment (Python version, OS).
- Any known mitigations or workarounds.

## Response Timeline

We aim to meet the following targets, on a best-effort basis:

| Stage                     | Target                          |
| ------------------------- | ------------------------------- |
| Acknowledge receipt       | Within 3 business days          |
| Initial assessment        | Within 7 business days          |
| Fix or mitigation plan    | Within 30 days of confirmation  |
| Public disclosure         | Coordinated, after a fix ships  |

We will keep you informed of progress throughout the process and will credit
reporters in the advisory unless anonymity is requested.

## Scope

The following are in scope:

- The `camt053` library and its command-line, REST API, MCP, and LSP
  interfaces as published in this repository.
- XML parsing and validation paths, including XXE / path-traversal handling.
- Input validation for IBAN, BIC, LEI, currency, and reason-code data.

The following are generally out of scope:

- Vulnerabilities in third-party dependencies (please report those upstream;
  we will track and update affected dependencies via Dependabot).
- Issues requiring a compromised host, malicious local configuration, or
  physical access.
- Denial of service caused by intentionally malformed, multi-gigabyte inputs
  beyond documented usage.

Thank you for helping keep camt053 and its users safe.

## NIST SSDF practice mapping

This repository follows the practices of the **NIST Secure Software
Development Framework (SP 800-218 Rev 1.1)**. The table below maps
each SSDF practice that applies to an open-source Python library to
the concrete control(s) that implement it in this repo. We update
this table whenever a referenced control changes.

| SSDF practice | How this repo addresses it |
| :--- | :--- |
| **PO.1** Define security requirements | This `SECURITY.md`, plus the in-scope/out-of-scope sections above. |
| **PO.3** Implement supporting toolchains | `pyproject.toml` (Poetry, ruff, black, mypy, pytest, interrogate); `.github/workflows/ci.yml`; `.github/workflows/scorecard.yml`. |
| **PO.4** Define and use criteria for software security checks | CI enforces 100% line + branch coverage (`--cov-fail-under=100`), 100% docstring coverage (`interrogate --fail-under=100`), strict mypy, ruff lint, bandit. |
| **PO.5** Implement and maintain secure environments | PyPI Trusted Publishing (OIDC, no long-lived tokens); branch protection + signed commits on `main`; GitHub Actions `permissions:` scoped per workflow. |
| **PS.1** Protect all forms of code from unauthorized access and tampering | Signed commits (SSH ed25519); branch protection; required PR reviews; `persist-credentials: false` on Scorecard checkout. |
| **PS.2** Provide a mechanism for verifying software release integrity | Signed git tags; `actions/attest-build-provenance@v3` SLSA L3 provenance attestations; PEP 740 sigstore attestations on PyPI uploads (`pypa/gh-action-pypi-publish` with `attestations: true`). |
| **PS.3** Archive and protect each software release | GitHub Releases pin the exact `dist/*` artifacts; CycloneDX 1.6 + SPDX 2.3 SBOMs and a pip-licenses manifest attached to every release; PyPI is the immutable archive. |
| **PW.1** Design software to mitigate security risks | XML parsing via `defusedxml` to defeat XXE / billion-laughs; bounded streaming via `iterparse`; dedicated identifier validators (IBAN / BIC / LEI). |
| **PW.4** Reuse well-secured software when feasible | Dependencies pinned via Poetry lockfile; Dependabot grouped weekly + separate security-update group; deps reviewed before bumps. |
| **PW.5** Adhere to secure coding practices | `ruff` (including `B`/`S` rule families), `bandit -ll`, strict `mypy`, code review on every PR. |
| **PW.6** Configure build processes to improve security | Reproducible builds via `poetry build` with locked dependencies; CI uses pinned action SHAs / version tags; minimum-required GH Actions permissions. |
| **PW.7** Review and analyze human-readable code | All changes go through PRs with required review; CodeQL static analysis runs on push/PR; ruff + mypy on every change. |
| **PW.8** Test executable code | pytest, Hypothesis property tests (`tests/test_property_based.py`), end-to-end example tests, performance regression guards. |
| **PW.9** Configure software with secure defaults | XSD validation on by default; XXE-safe parsing on by default; HMAC hash-chain audit log GENESIS_HASH constant; strict-mode parsing as the default. |
| **RV.1** Identify and confirm vulnerabilities on an ongoing basis | Dependabot daily; `bandit` in CI; OpenSSF Scorecard weekly; GitHub Security Advisories accept reports. |
| **RV.2** Assess, prioritise, and remediate vulnerabilities | Coordinated-disclosure timeline above (3-day ack / 7-day assessment / 30-day fix); CHANGELOG + advisory at fix publication. |
| **RV.3** Analyze root causes | Each security advisory captures root cause + remediation in the GitHub Security Advisory body; lessons feed back into added regression tests.

### Out-of-band practices

A few SSDF practices do not apply directly to a small OSS library:

- **PO.2** (Roles and Responsibilities), **PS.3** (Archive and Protect Each Release) at the organisational level are owned by the maintainer (see [`MAINTAINERS.md`](MAINTAINERS.md)).
