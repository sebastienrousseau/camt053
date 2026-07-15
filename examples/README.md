# camt053 examples

Runnable, self-contained examples for the camt053 library. Run any of them from
the repository root:

```sh
python examples/<name>.py
```

Every script here is executed in CI by `tests/test_examples.py`, which fails
if any example exits non-zero, so the examples cannot silently rot.

## The headline workflow

| Example | Demonstrates |
|---------|--------------|
| [`reverse_ac04.py`](reverse_ac04.py) | The headline workflow: read a statement, find the AC04 (Closed Account) entries, and generate a validated reversing entry |
| [`generate_reversal_documents.py`](generate_reversal_documents.py) | Every reversal output knob: camt.053.001.14 (default), camt.053.001.08, pacs.004 PaymentReturn, and rendering pre-built records |
| [`build_reversal_records.py`](build_reversal_records.py) | The reversal primitives: flat reversing-entry records and stable (idempotent) reversal references, without rendering XML |
| [`write_reversal_file.py`](write_reversal_file.py) | Writing a reversal to disk, validating files/strings against the bundled ISO XSDs, and the bundled Jinja templates |
| [`generate_batch.py`](generate_batch.py) | Batch mode: reverse a directory of statements with per-file error isolation |

## Parsing and the typed model

| Example | Demonstrates |
|---------|--------------|
| [`parse_statement.py`](parse_statement.py) | Parsing a camt.053 statement into the typed model (account, balances, entries, return reasons) |
| [`parse_statement_lenient.py`](parse_statement_lenient.py) | Lenient parsing: surface the good entries plus diagnostics for the corrupt ones |
| [`serialize_roundtrip.py`](serialize_roundtrip.py) | Parse -> typed model -> re-serialised, XSD-validated XML, and back |
| [`stream_entries.py`](stream_entries.py) | Memory-bounded entry streaming and reason / status / date / amount filtering |
| [`compute_dedupe_keys.py`](compute_dedupe_keys.py) | Exactly-once dedupe keys for statement replays |

## Validation and compliance

| Example | Demonstrates |
|---------|--------------|
| [`validate_identifiers.py`](validate_identifiers.py) | IBAN / BIC / LEI validation (ISO 13616 / 9362 / 17442) |
| [`validate_currencies.py`](validate_currencies.py) | ISO 4217 currency validation and minor-unit lookup |
| [`validate_records_schema.py`](validate_records_schema.py) | JSON Schema validation of flat reversing-entry records, with field introspection |
| [`validate_against_profile.py`](validate_against_profile.py) | Per-schema-version profile validation (.02 deprecated, .08 CBPR+, .13 T2S strict) |
| [`schema_version_preflight.py`](schema_version_preflight.py) | Schema-version detection / classification, the profile registry, and XSD pre-flight |
| [`check_cbpr_readiness.py`](check_cbpr_readiness.py) | The Nov 14-16 2026 CBPR+ cliff pre-flight |
| [`swift_charset_cleansing.py`](swift_charset_cleansing.py) | SWIFT X charset cleansing of names and narratives |
| [`reason_code_policies.py`](reason_code_policies.py) | The ISO return-reason catalogue and return / retry / ignore handling policies |
| [`exceptions_taxonomy.py`](exceptions_taxonomy.py) | The typed exception hierarchy and the strict (raising) validator variants |

## Services, API, and operations

| Example | Demonstrates |
|---------|--------------|
| [`services_facade.py`](services_facade.py) | The shared `camt053.services` facade: message types, return reasons, required fields, identifier validation |
| [`cli_workflows.py`](cli_workflows.py) | The `camt053` CLI end to end: reference lookups, validation, parse, reverse |
| [`rest_api_client.py`](rest_api_client.py) | Driving the FastAPI REST API in-process (parse, entries, reverse) |
| [`rest_api_reference.py`](rest_api_reference.py) | The remaining REST endpoints (health, reference, validation, CBPR+) and the OpenAPI document |
| [`security_guards.py`](security_guards.py) | The XML / path / log-injection security guards |
| [`structured_logging.py`](structured_logging.py) | Structured JSON logging with automatic IBAN / BIC / name redaction |
| [`telemetry_hooks.py`](telemetry_hooks.py) | OpenTelemetry spans and RED metrics with graceful no-op degradation |
| [`audit_hashchain.py`](audit_hashchain.py) | The tamper-evident HMAC-SHA-256 hash-chain audit log |

Install the package first:

```sh
pip install camt053   # Python 3.10+
```
