# `camt053` suite — style guide

This is the cross-package style guide for everything in the
[`camt053`](https://github.com/sebastienrousseau/camt053) suite
(`camt053`, `camt053-mcp`, `camt053-lsp`,
`camt053-writer-xlsx`, `camt053-loader-mt940`).

The intent is **consistency-by-default** so a contributor familiar
with one package can navigate any of them without re-learning
conventions. Every cross-suite document — README, CHANGELOG,
SECURITY, SUPPORT, CONTRIBUTING — should match the structures
defined here.

Linked from every package README's *Documentation* section.

## Why this exists

The 5-package suite shares a single `camt053.services` layer and
a single release cadence. To make that consistency visible to
operators and procurement teams, the suite-level documents are
all shaped the same way. A `SECURITY.md` in one package answers
the same question in the same place as the `SECURITY.md` in any
other package; a `README.md` reads with the same flow.

## Voice

- **Operator-oriented.** Every section answers "what do I do with
  this?" before "what is this?".
- **Active voice.** "The tool returns…" not "is returned by".
- **British spelling** in long-form prose (organisation, behaviour,
  centre); American spelling in code and inline identifiers
  (`color`, `analyze`).
- **No em-dashes** anywhere. Use a single dash with spaces
  (`option A - option B`) or a sentence break instead.
- **No emojis** anywhere outside the OSS-standard `:white_check_mark:`
  / `:x:` cells in the *Supported Versions* table.

## README structure

Every package's `README.md` lays out the same sections in the same
order:

```
1.  H1 title
2.  Logo image (centred, 128px)
3.  Badge row (PyPI, Python versions, License, Tests, Quality,
    OpenSSF Scorecard, Documentation)
4.  Latest-release callout (one-line "what's new" + link to the
    release notes)
5.  ## Contents (anchor list)
6.  ## Overview
7.  ## Install
8.  ## Quick Start (links to docs/quickstart.md for the long form)
9.  Package-specific feature sections (Tools, Resources, Prompts,
    Features, Usage, ...)
10. ## The camt053 suite (cross-link to siblings)
11. ## When not to use ...
12. ## Development
13. ## Security
14. ## News / Releases (linked blog posts)
15. ## Documentation (links to repo docs)
16. ## License
17. ## Contributing
18. ## Acknowledgements
```

The badge row is consistent: PyPI Version, Python Versions,
License, Tests, Quality, OpenSSF Scorecard, Documentation, in
that order. Glama badge optional (MCP packages only).

## CHANGELOG structure

Strict [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) +
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

```
# Changelog
... preamble ...
## [X.Y.Z] - YYYY-MM-DD
### Added
### Changed
### Deprecated
### Removed
### Fixed
### Security
### Requirements
### Quality gates
### Suite alignment
```

The trailing **Quality gates** table and **Suite alignment** table
are camt053-specific additions (always present, even when nothing
changed in them) so anybody auditing a release at a single glance
can confirm the CI floor and the version pinning.

## SECURITY.md structure

Every package's `SECURITY.md` covers the same six sections:

```
1.  ## Supported Versions
2.  ## Reporting a Vulnerability
3.  ## Response timeline
4.  ## Scope (in-scope + out-of-scope, plain language)
5.  ## NIST SSDF practice mapping (table mapping each shipped
    control to its NIST SP 800-218 Rev 1.1 practice ID)
6.  ## (cross-reference) Cross-suite practices owned by the
    upstream camt053 SECURITY.md
```

The *NIST SSDF practice mapping* table is the procurement-ready
section. Update it whenever a referenced control changes; treat
this as a SemVer minor event.

## SUPPORT.md structure

The "how do I get help?" landing page, organised by need:

```
1.  ## I want to ask a question
2.  ## I think I found a bug
3.  ## I want to request a feature
4.  ## I need a security disclosure channel
5.  ## I want commercial support
```

Each section is 2-3 lines max and points at the right channel
(GitHub Discussions, GitHub Issues, GitHub Security Advisories,
or the maintainer's email).

## CONTRIBUTING.md structure

```
1.  ## Code of Conduct (link to root CoC)
2.  ## Repository layout
3.  ## Setting up your development environment
4.  ## Running tests
5.  ## Submission process (fork, branch naming, PR template,
    signed commits, "make CI green before requesting review")
6.  ## Style (link to this STYLEGUIDE.md)
```

## CI floor (every package)

Every package in the suite enforces the same CI minimum in
`.github/workflows/ci.yml`:

| Gate | Tool | Threshold |
| :--- | :--- | :--- |
| Tests | `pytest` | green on Python 3.10, 3.11, 3.12 |
| Line + branch coverage | `pytest-cov` | `--cov-fail-under=100` |
| Docstring coverage | `interrogate` | `--fail-under=100` |
| Lint | `ruff` | clean |
| Format | `black` | clean |
| Type-check | `mypy` | strict |
| Security scan | `bandit` | `-ll` clean |
| Supply-chain | `ossf/scorecard-action` | weekly + on push |

Plus on every tag-driven release (`release.yml`):

- `actions/attest-build-provenance@v3` (SLSA Build L3)
- `pypa/gh-action-pypi-publish@release/v1` with `attestations: true`
  (PEP 740 sigstore)
- CycloneDX 1.6 SBOM + SPDX 2.3 SBOM + pip-licenses manifest
  attached to the GitHub release
- Signed git tag (SSH ed25519)

## Pull request style

- Conventional commits (`feat(scope): ...`, `fix(scope): ...`,
  `docs(scope): ...`, `chore(scope): ...`, `ci(scope): ...`,
  `style(scope): ...`).
- One concern per PR; large work is split into a series of
  reviewable PRs, not one big one.
- PR body has *Summary*, *Changes*, *Test plan*, *Closes*
  sections.
- Signed commits required on every branch; no direct commits to
  `main` or `feat/v0.0.X` release branches, even for trivial CI
  hotfixes.

## Branch naming

```
feat/v0.0.X-<scope>     # feature / docs work scoped to a release
fix/<short-handle>      # bug fixes off main
chore/<short-handle>    # repo housekeeping
```

`feat/v0.0.X` (no scope suffix) is the umbrella release branch and
gets the same no-direct-commits policy as `main`.

## Filing issues

Use the issue templates in `.github/ISSUE_TEMPLATE/`. Bug reports
need a minimal reproducer (an XML payload or the smallest record
list that triggers the issue). Feature requests need a *Why*
section linking to the rule, RFC, or scheme document that
motivates the ask.

Cross-suite-spanning work goes on the
[`camt053`](https://github.com/sebastienrousseau/camt053) repo
(this one) with the relevant package as an in-body link.
Package-specific work goes on the package repo.

## Naming conventions

- Module names: snake_case (`schema_version`, `hash_chain`).
- Public function / method names: snake_case (`parse_statement`,
  `compute_dedupe_key`).
- MCP tool names: snake_case verbNoun (`list_message_types`,
  `cite_rulebook`, `check_cbpr_readiness`) — matches the Stripe
  MCP pattern.
- Class names: PascalCase (`ParsedDocument`, `HashChain`).
- Constants: SCREAMING_SNAKE_CASE
  (`CURRENT_SCHEMA_VERSIONS`, `CBPR_CUTOVER_DATE`).
- Identifier types in docstrings: backtick-quoted code style
  (`IBAN`, `BIC`, `LEI`, `UETR`).

## When in doubt

When this guide is silent on a question, default to the
convention used by the
[`pain001`](https://github.com/sebastienrousseau/pain001) sibling
suite — they share the same maintainer and design philosophy.

When that is also silent, default to the conventions in
[PEP 8](https://peps.python.org/pep-0008/),
[PEP 257](https://peps.python.org/pep-0257/),
and the Python community at large.
