# Schema-version support matrix

Which ISO 20022 `camt.05x` schema revisions are supported by which
release of the `camt053` suite, with the **14–16 November 2026
CBPR+ cliff** annotated.

The library accepts (parses, validates, reverses) every revision in
the **Current** column; revisions in the **Deprecated** column still
parse and validate but emit a deprecation diagnostic; everything else
is refused by `validate_schema_version(..., strict=True)`.

## Current `camt053` (suite v0.0.6 / v0.0.7)

| Family | Revision | Status | CBPR+ Nov 2026 | T2S MR2026 | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `camt.052` (Account Report) | `.001.08` | **Current** | ✅ Accepted | — | CBPR+ producer lingua franca (BNY, JPM, Citi, GS, DB, BNP, SC). |
| `camt.052` | `.001.13` | **Current** | ✅ Accepted | ✅ T2S MR2026 target | The cross-border current set. |
| `camt.053` (Bank-to-Customer Statement) | `.001.08` | **Current** | ✅ Accepted | — | The cross-border current set on the producer side. |
| `camt.053` | `.001.13` | **Current** | ✅ Accepted | ✅ T2S MR2026 target | Default revision for new code. |
| `camt.053` | `.001.14` | **Current** | ✅ Accepted | — | Wider family kept current alongside `.13` (XSD shipped). |
| `camt.054` (Debit/Credit Notification) | `.001.08` | **Current** | ✅ Accepted | — | |
| `camt.054` | `.001.13` | **Current** | ✅ Accepted | ✅ T2S MR2026 target | |
| `camt.052/053/054` | `.001.02`–`.001.07` | **Deprecated** | ❌ Rejected post-cliff | — | Library still parses; emits a deprecation diagnostic. |
| Anything else (`camt.0xx.001.YY` outside the above, or non-camt namespace) | — | **Unsupported** | — | — | Refused by `validate_schema_version(strict=True)` with `UnsupportedSchemaError`. |

The authoritative version sets live in
[`camt053/schema_version.py`](../camt053/schema_version.py)
(`CURRENT_SCHEMA_VERSIONS`, `DEPRECATED_SCHEMA_VERSIONS`).

## Discovery API

```python
from camt053.schema_version import (
    classify_schema_version,
    detect_schema_version,
    validate_schema_version,
)

xml = open("bank-statement.xml").read()

# Quick: which revision is this payload?
detect_schema_version(xml)         # "camt.053.001.13"

# Bucketed: "current" / "deprecated" / "unknown" / "unsupported"
classify_schema_version(detect_schema_version(xml))  # "current"

# Strict gate (raises UnsupportedSchemaError on "unsupported"):
validate_schema_version(xml, strict=True)
```

The same surface is exposed through the
[`camt053-mcp`](https://github.com/sebastienrousseau/camt053-mcp)
`validate_statement` tool and the REST API's `/validate` endpoint, so
agents and HTTP clients reach the same classification.

## The 14–16 November 2026 cliff

A coordinated CBPR+ / Fedwire / CHAPS / T2 cutover lands across the
weekend of **14–16 November 2026**:

- **CBPR+** rejects payment instructions carrying unstructured-only
  postal addresses (TownName + Country must be structured siblings,
  not `AdrLine` lines). See `check_cbpr_readiness` for the rule.
- **`camt.110` / `camt.111`** become mandatory for exceptions and
  investigations, replacing legacy MT 19x flows on cross-border.
- **T2S R2026.NOV** upgrades the T2S RTGS and T2 RTGS systems to
  schema revision **MR2026**: `camt.053` / `camt.054` produced by T2
  RTGS move to the MR2026 variant; older variants are no longer
  accepted by the T2/T2S RTGS at receipt.

After the cliff, only the rows marked ✅ in the matrix above will be
accepted by the major clearing systems. Deprecated revisions
(`.02`–`.07`) and unstructured-only payloads will be rejected at
receive-time.

Practical cookbook:

```python
# Pre-flight a statement before forwarding it on:
from camt053.compliance import check_cbpr_readiness

report = check_cbpr_readiness(xml)
if not report["cbpr_ready"]:
    raise RuntimeError(
        f"payload not CBPR+ ready: {report['issues']}"
    )
```

## Backwards-compatibility policy

The `camt053` suite follows SemVer at the `0.0.x` series. Within a
minor release line the matrix above is stable: a revision marked
**Current** today will not be downgraded to **Deprecated** by a patch
release. Removal from **Current** to **Deprecated** is a minor-bump
event with a CHANGELOG entry; removal from the codebase entirely is
a major-bump event.

A revision can be promoted into the **Current** set in a patch release
when the XSD is bundled and the unit tests cover the round trip.

## Suite alignment

| Package | Reads camt.05x revisions covered by this matrix |
| :--- | :--- |
| [`camt053`](https://pypi.org/project/camt053/) (this repo) | All |
| [`camt053-mcp`](https://pypi.org/project/camt053-mcp/) | All (via `camt053.services`) |
| [`camt053-lsp`](https://pypi.org/project/camt053-lsp/) | All (via `camt053.services`) |
| [`camt053-writer-xlsx`](https://pypi.org/project/camt053-writer-xlsx/) | All (consumes `ParsedDocument` from any current revision) |
| [`camt053-loader-mt940`](https://pypi.org/project/camt053-loader-mt940/) | Emits a `ParsedDocument` shape downstream consumers can target as `camt.053.001.13` |
