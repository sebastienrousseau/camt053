<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->

# `camt053` governance

This document describes how `camt053` (and the four sibling packages in the
suite — `camt053-mcp`, `camt053-lsp`, `camt053-writer-xlsx`,
`camt053-loader-mt940`) is run, how decisions are made, and how to take on
responsibility for it. It exists to make the project legible and sustainable
— and, candidly, to reduce its dependence on any single person.

## Mission and scope

`camt053` parses, validates, and reverses ISO 20022 `camt.05x` cash-management
messages (account reports, statements, debit/credit notifications), with a
small well-tested core and first-class CLI, REST, MCP, and LSP surfaces.
Companion packages cover the ecosystem (Excel writer, MT940 loader). Changes
are weighed against this scope: **correctness, security, and clarity over
feature breadth**.

A change is in-scope if it makes parsing more accurate, validation more
complete against the official ISO 20022 XSDs and the major scheme rulebooks
(CBPR+, HVPS+, T2/T2S), or reversing-entry generation more reliable. A
change is out-of-scope if it grows the dependency graph for marginal
benefit or duplicates functionality that lives more naturally in a
companion package.

## Roles

| Role | Who | Can |
| :--- | :--- | :--- |
| **Maintainer** | Listed in [`MAINTAINERS.md`](MAINTAINERS.md) | Merge PRs, cut releases, triage, set direction |
| **Contributor** | Anyone with a merged PR | Propose changes, review, discuss |
| **User** | Everyone | File issues, ask questions, request features |

Maintainers are also listed as code owners in `.github/CODEOWNERS` (when
present) for review routing.

## Decision making

- **Day-to-day changes** (fixes, docs, tests, additive features within scope)
  land via a PR with a maintainer's approval. The conventional-commits style
  + signed commits + branch-protection policy described in
  [`STYLEGUIDE.md`](STYLEGUIDE.md) is the binding rulebook.
- **Larger or contentious changes** (new public API surface, dependency
  additions, breaking changes within `0.0.x`) require a tracking GitHub
  Issue with the proposed design, a 72-hour comment window, and maintainer
  agreement to merge. Substantial work may be split across multiple PRs
  under a v0.0.X milestone for visibility.
- **Releases** are cut against a v0.0.X milestone. The lead maintainer signs
  the git tag and runs the release script; PyPI publishing happens via
  OIDC Trusted Publishing + PEP 740 attestations.
- **Security disclosures** follow the timeline in
  [`SECURITY.md`](SECURITY.md): 3-day acknowledgement, 7-day assessment,
  30-day fix target.

## Suite-wide consistency

All packages in the suite share:

- The same CI floor (100% line + branch coverage, 100% docstring coverage
  via `interrogate`, strict mypy, ruff, black, bandit, OpenSSF Scorecard).
- The same release pipeline (signed tags, SLSA Build L3 provenance via
  `actions/attest-build-provenance@v3`, PEP 740 sigstore attestations on
  PyPI, CycloneDX + SPDX + pip-licenses SBOMs on every GitHub release).
- The same governance documents (this file, `MAINTAINERS.md`,
  `SECURITY.md`, `STYLEGUIDE.md`, `SUPPORT.md`,
  [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)).
- The same branch policy (no direct commits to `main` or
  `feat/v0.0.X` release branches; every change via PR; signed commits
  required on every branch).

Cross-suite policy changes (e.g. tightening the SSDF mapping, bumping the
SLSA tier) land in this repo first, then propagate via mirror PRs to the
sibling repos. The mirror PRs cite this repo's commit so the audit trail
stays one-hop.

## Becoming a maintainer

See the path in [`MAINTAINERS.md`](MAINTAINERS.md). Two weeks of public
nomination is the minimum; the lead maintainer reserves the right to
extend on a case-by-case basis if the comment thread surfaces material
concerns.

## Disagreements

If contributors disagree on a change, the discussion happens in the PR or
its tracking issue, in public. If consensus does not emerge in a reasonable
time, the lead maintainer makes the call and records the reasoning on the
issue. Lazy consensus applies to small day-to-day changes; rough consensus
applies to anything touching the public API.

## Forks

The project is Apache-2.0 licensed; forks are explicitly welcome. The
governance and naming requirements:

- Do not market a fork as the upstream `camt053` (`pip install camt053`
  should always reach this project).
- Do not use the suite's logo without permission.
- Do file bugs upstream as well as in your fork, where the upstream issue
  is applicable.

## Funding and ownership

`camt053` and its suite are currently unfunded volunteer work. The lead
maintainer holds copyright on the original code; contributions are licensed
under Apache-2.0 per the inbound = outbound rule (no CLA, no DCO required
today, though both may be added if the project grows).

## Updating this document

Updates to `GOVERNANCE.md` are themselves governed by this document: they
land via PR, with the 72-hour comment window for anything material. The
lead maintainer has final say but is expected to engage with substantive
feedback before merging.
