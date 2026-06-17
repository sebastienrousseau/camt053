.. _dhf-verification-validation:

============================================
Verification and Validation Plan
============================================

.. list-table:: Document Control
   :widths: 25 75
   :stub-columns: 1

   * - Document ID
     - DHF-006
   * - Version
     - 1.0
   * - Date
     - 2026-03-22
   * - Author
     - camt053 Engineering
   * - Status
     - Released
   * - ISO 13485 Clauses
     - 7.3.5 (Verification), 7.3.6 (Validation), 7.3.7 (Design Transfer)

1. Test Strategy
----------------

The verification strategy follows a layered approach from unit tests through
system-level validation:

1. **Unit Tests** — Individual functions and classes tested in isolation
   (parser, reversal mapping, validators, reason codes, models)
2. **Integration Tests** — Module interactions and the parse → filter →
   reverse → validate pipeline
3. **System Tests** — End-to-end workflows from an inbound camt statement
   through the reversing entry and its XSD validation
4. **Conformance Tests** — Parsing of the official ISO 20022 business sample
   messages and XSD validation of generated reversals

All tests are automated and executed on every commit via GitHub Actions CI.

2. Test Categories and Markers
-------------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Marker
     - Category
     - Description
   * - ``smoke``
     - Smoke
     - Quick sanity checks confirming core functionality is operational.
       Run first in CI for fast feedback.
   * - ``integration``
     - Integration
     - End-to-end workflow tests spanning multiple modules. Verify that
       components work together correctly.
   * - ``security``
     - Security
     - XXE prevention, path traversal, injection attack, and log
       sanitization tests.
   * - ``message_compat``
     - Message Compatibility
     - Tests exercising the camt.052 / camt.053 / camt.054 message family across
       ISO versions. Verify namespace-agnostic parsing.
   * - ``perf``
     - Performance
     - Benchmark tests measuring parsing and reversal throughput.
   * - ``slow``
     - Slow
     - Tests taking more than 1 second. May be excluded from rapid
       development cycles.

**Running specific categories:**

.. code-block:: bash

   pytest -m smoke              # Quick sanity checks
   pytest -m integration        # End-to-end workflows
   pytest -m security           # Security-focused tests
   pytest -m message_compat     # camt.052/053/054 across ISO versions
   pytest -m perf               # Performance benchmarks

3. Test File Inventory
-----------------------

3.1 Parsing and Model Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - Test File
     - Purpose
     - Requirements
   * - ``test_parser.py``
     - ``parse_document()`` / ``parse_statement()``, namespace-agnostic
       camt.052/053/054 dispatch, XXE-safe parsing
     - FR-101, FR-102, FR-103, FR-703, NFR-101
   * - ``test_models.py``
     - Typed model: ``Statement``, ``Entry``, ``Account``, ``Balance``,
       ``Statement.entries_with_reason()``
     - FR-103, FR-203
   * - ``test_main_entry.py``
     - ``__main__.py`` entry point and ``main()`` function
     - FR-604
   * - ``test_exceptions.py``
     - Exception hierarchy and custom exception fields
     - FR-701, FR-702, FR-703, FR-704
   * - ``test_init_and_gold_master.py``
     - Package init, message-type allowlist, end-to-end conformance
     - FR-104, FR-404, NFR-503

3.2 Reason-Code and Reversal Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - Test File
     - Purpose
     - Requirements
   * - ``test_reason_codes.py``
     - ``describe_reason()``, ``is_known_reason()``,
       ``list_reason_codes()`` (ISO return reason codes, e.g. AC04)
     - FR-201, FR-202
   * - ``test_reversal.py``
     - ``build_reversal_record()`` / ``build_reversal_records()``:
       credit/debit flip, ``RvslInd=true``, reference carry-over
     - FR-301, FR-302

3.3 XML Generation and XSD Validation Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - Test File
     - Purpose
     - Requirements
   * - ``test_generate_xml.py``
     - ``generate_reversal_xml()``, ``generate_reversal_for_statement()``,
       ``write_reversal_xml()`` (camt.053.001.14 rendering)
     - FR-401, FR-402, FR-404, FR-702, NFR-104
   * - ``test_validate_via_xsd.py``
     - ``validate_via_xsd()``, ``validate_xml_string_via_xsd()`` against
       the official camt.053.001.14 XSD, XXE prevention, schema caching
     - FR-403, NFR-101, NFR-401
   * - ``test_business_samples.py``
     - Parsing of the official ISO 20022 business-sample messages
     - FR-101, FR-104, NFR-402

3.4 Identifier and Schema Validation Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - Test File
     - Purpose
     - Requirements
   * - ``test_validators.py``
     - BIC (ISO 9362), IBAN (ISO 7064 mod-97-10), LEI (ISO 17442
       check-digit) format and checksum validation
     - FR-501, FR-502, FR-503, FR-701
   * - ``test_schema_validator.py``
     - ``SchemaValidator`` and ``ValidationError`` against the bundled
       JSON schemas
     - FR-504, FR-704

3.5 Service Facade and Interface Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - Test File
     - Purpose
     - Requirements
   * - ``test_services.py``
     - ``services`` facade: ``parse_statement()``, ``list_entries()``,
       ``filter_entries()``, ``build_reversal()``, ``generate_reversal()``,
       ``validate_identifier()``, ``validate_records()``
     - FR-204, FR-303, FR-505, FR-601, NFR-501
   * - ``test_cli.py``
     - Click group: ``parse``, ``entries``, ``reverse``,
       ``message-types``, ``reasons``, ``validate-id``
     - FR-602
   * - ``test_api.py``
     - FastAPI endpoints: ``/health``, ``/message-types``, ``/reasons``,
       ``/parse``, ``/entries``, ``/reverse``, ``/validate-identifier``,
       ``/validate-records``
     - FR-603

3.6 Security Tests
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - Test File
     - Purpose
     - Requirements
   * - ``test_path_validator.py``
     - Path traversal protection: ``validate_path()``,
       ``PathValidationError``, ``SecurityError``, ``sanitize_for_log()``
     - NFR-102, NFR-103

4. Conformance Against Official ISO Business Samples
----------------------------------------------------

``test_business_samples.py`` and ``test_init_and_gold_master.py`` provide
end-to-end conformance testing against the official ISO 20022 business-sample
messages. For each sample:

1. Parse the inbound camt statement (namespace-agnostic, every ISO version)
2. Filter entries by ISO return reason code into the typed model
3. Build the reversing entry and render it as camt.053.001.14
4. Validate the generated reversal against the official ISO XSD

**Conformance fixtures** are stored in ``tests/gold_master/`` and include
``business_sample_camt.052.001.04.xml``, ``business_sample_camt.053.001.04.xml``,
``business_sample_camt.054.001.04.xml``, and ``statement_ac04.xml``.

5. Static Analysis Tools
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Tool
     - Type
     - Configuration
   * - mypy
     - Type checking
     - ``python_version=3.9``, ``strict=true``,
       ``disallow_untyped_defs=true``
   * - ruff
     - Linting
     - ``line-length=79``, ``target-version=py39``
   * - black
     - Formatting
     - ``line-length=79``, ``target-version=['py39']``
   * - bandit
     - SAST
     - ``bandit -r camt053/`` — zero findings required
   * - safety
     - Dependency audit
     - Checks pinned dependencies against known vulnerability database

6. CI Pipeline
--------------

The GitHub Actions CI pipeline (``.github/workflows/ci.yml``) runs on every
push and pull request:

.. list-table::
   :header-rows: 1
   :widths: 15 30 55

   * - Job
     - Matrix
     - Actions
   * - **test**
     - 3 OS (ubuntu, macos, windows) x 4 Python (3.9, 3.10, 3.11, 3.12)
     - Install dependencies, run full test suite with coverage, upload
       coverage to Codecov (Python 3.12 / ubuntu only)
   * - **smoke**
     - ubuntu-latest, Python 3.12
     - Run ``pytest -m smoke`` for quick sanity checks, verify example
       scripts
   * - **lint**
     - ubuntu-latest, Python 3.12
     - Run ``ruff check``, ``black --check``, ``mypy --strict``
   * - **security**
     - ubuntu-latest, Python 3.12
     - Run ``bandit -r camt053/`` for SAST scan

**Total CI matrix:** 14 configurations (12 test + 1 lint + 1 security)

7. Acceptance Criteria
-----------------------

The software release is accepted when **all** of the following are satisfied:

.. list-table::
   :header-rows: 1
   :widths: 10 60 30

   * - #
     - Criterion
     - Verification Method
   * - 1
     - The full pytest suite passes on all CI matrix configurations
     - GitHub Actions test job (12 configs)
   * - 2
     - Branch coverage >= 99% (actual: 100%)
     - ``--cov-fail-under=99`` in pytest
   * - 3
     - Zero bandit SAST findings
     - GitHub Actions security job
   * - 4
     - Zero mypy strict-mode errors
     - GitHub Actions lint job
   * - 5
     - Zero ruff/black formatting violations
     - GitHub Actions lint job
   * - 6
     - Parse + reversal conformance tests pass against the official ISO business samples
     - ``test_business_samples.py``, ``test_init_and_gold_master.py``
   * - 7
     - All pre-commit hooks pass
     - ``.pre-commit-config.yaml`` (13 hooks)
   * - 8
     - Generated reversals validate against the official ISO XSD
     - ``test_validate_via_xsd.py``, ``test_generate_xml.py``
   * - 9
     - All risk mitigations verified by tests
     - DHF-005 Risk Control Verification table
