<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->

# Architecture

camt053 is one facade, `camt053.services`, with four surfaces in front of it
and five packages of logic behind it. Every interface (the Python API, the
Click CLI, the FastAPI REST API, and the companion MCP and LSP servers) calls
the facade, so they behave the same.

```text
 Click CLI    FastAPI REST API    camt053-mcp    camt053-lsp
     \               |                 |              /
      +--------------+-------+---------+-------------+
                             |
                     camt053.services
                             |
     +------------+----------+-----------+----------------+
     |            |                      |                |
  parse/      reversal/                xml/          validation/
  statement   reversal builder    template + the     IBAN, BIC, LEI,
  parser,                         official ISO XSD   JSON Schema
  reason codes
```

| Module | Responsibility |
| :--- | :--- |
| `camt053.parse` | Namespace-agnostic statement parser, return-reason helpers, de-duplication keys, lenient parse reports |
| `camt053.reversal` | Builds flat reversing-entry records from parsed entries, with deterministic references |
| `camt053.xml` | Renders the camt.053 and pacs.004 templates, re-serialises statements, validates against the ISO XSDs |
| `camt053.validation` | IBAN, BIC, LEI, ISO 4217 currency and JSON-Schema validators |
| `camt053.profiles` | Per-revision rules (`.001.02`, `.001.08`, `.001.13`, `.001.14`) on top of the namespace-agnostic parser |
| `camt053.compliance` | CBPR+ November 2026 readiness checks and SWIFT X charset cleansing |
| `camt053.security` | XXE-safe parsing guard and path-traversal-checked output |
| `camt053.services` | The shared facade backing every interface |
| `camt053.suite` | The suite's membership and versioning policy |

## The flow of one reversal

1. `services.generate_reversal(xml, reason_code="AC04")` parses the
   statement with `defusedxml` into a `ParsedDocument`. The REST API first
   passes every payload through `services.guard_xml` (`security.xml_guard`:
   byte cap, no inline DOCTYPE or ENTITY); library callers handling untrusted
   input call it themselves.
2. The entries carrying the reason code are selected, and
   `reversal.build_reversal_record` turns each into a flat record: the
   credit/debit indicator flipped, `RvslInd` set, the reason carried in
   `RtrInf`, and a reference derived from the original by
   `stable_reversal_reference`, so a retry produces the same reference.
3. `xml.generate_xml` renders the `camt.053.001.14` Jinja template and
   validates the result against the bundled XSD before returning it. A
   document that does not validate is never returned.

## Where the complexity is

`complexity-baseline.json` lists the functions and files over the per-function
ceilings. It may only shrink: `scripts/check_complexity.py` fails when an
entry gets worse and when one improves without the baseline being updated.
