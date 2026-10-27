<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->

# Development

The single entry point for working on camt053: set up, reproduce every CI
gate locally, find your way around the tests, and see how a release is cut.
Contribution rules (branches, signing, PR shape) are in
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Set up

```bash
git clone https://github.com/sebastienrousseau/camt053.git && cd camt053
poetry install            # runtime + dev dependencies from poetry.lock
```

Python 3.11 or newer ([toolchain policy](docs/POLICIES.md)). CI installs
Poetry itself from the hash-pinned `requirements/build.txt`.

## Reproduce CI locally

| CI job | Local command |
| :--- | :--- |
| Lockfile matches pyproject, version sources agree | `poetry check --lock && make verify-versions` |
| Test matrix (100% line and branch coverage) | `make test` |
| Smoke and examples | `make smoke && make examples` |
| Lint & type check | `make lint && make type-check` |
| Security scan | `make security` |
| Complexity ceilings | `make complexity` |
| Dependency audit | `poetry run pip-audit` and `pip-audit --require-hashes --disable-pip -r requirements/<set>.txt` |
| Benchmarks (smoke) | `python benches/bench_statement_pipeline.py --quick` |
| Docs | `make docs` |
| Docker build | `make docker` |

`make check` runs the version check, lint, types, security, complexity,
tests and examples in one go.

## Tests

`tests/` holds one module per area (parser, reversal, services, CLI, API,
validators, profiles, telemetry). `tests/gold_master/` holds the official
ISO 20022 business samples and the AC04 statement the demo uses.
`tests/test_suite_conformance.py` is a vendored copy shared across the suite
and checksummed; do not edit it here. Benchmarks (`-m perf`) and stress tests
(`-m stress`) are outside the coverage gate.

## Dependencies

Runtime and dev dependencies live in `pyproject.toml` and `poetry.lock`. The
tool sets CI installs (`requirements/*.in`) are compiled with hashes by
`make pip-compile`. A dependency with an advisory is floored so no affected
version resolves, with the advisory named in a comment beside the floor.

## Complexity

`scripts/check_complexity.py` holds every function to cyclomatic 10,
cognitive 15, Halstead difficulty 30 and 60 lines, and every file to 500
lines. Existing offenders are in `complexity-baseline.json`. After you bring
one under a ceiling, run `poetry run python scripts/check_complexity.py
--update` and commit the smaller baseline; the script refuses to update while
anything is new or worse.

## Releases

The camt053 suite releases together at one version, core first, then the
satellites. A release is a `feat/v<version>` branch merged by squash into
`main`, then a signed annotated tag `v<version>` with the message
`camt053 v<version>`. Pushing the tag runs `release.yml`: build, `twine
check`, SLSA provenance, PyPI Trusted Publishing, sigstore signatures, and
SBOMs attached to the GitHub release titled `camt053 <version>`.
`scripts/preflight_release.py` checks the tree before a tag, and
`scripts/check_suite_consistency.py` checks PyPI daily afterwards.
