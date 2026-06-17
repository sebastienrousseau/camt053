.. _dhf-design-development-plan:

======================================
Design and Development Plan
======================================

.. list-table:: Document Control
   :widths: 25 75
   :stub-columns: 1

   * - Document ID
     - DHF-002
   * - Version
     - 1.0
   * - Date
     - 2026-03-22
   * - Author
     - camt053 Engineering
   * - Status
     - Released
   * - ISO 13485 Clauses
     - 7.3.1 (Design and Development Planning), 7.3.2 (Design and Development Inputs)

1. Scope
--------

The **camt053** library reads incoming ISO 20022 camt Bank-to-Customer Cash
Management messages, extracts booked entries by ISO external return reason code,
and generates validated reversing entries. It parses statements into a typed
model, filters entries (e.g. AC04 Closed Account), and renders a reversing
camt.053.001.14 statement that is validated against the official ISO 20022 XSD
before it is returned.

The library reads the camt.052 (Bank To Customer Account Report), camt.053 (Bank
To Customer Statement), and camt.054 (Bank To Customer Debit Credit Notification)
message families. Parsing is namespace-agnostic, so every ISO version
(``.001.01`` through ``.001.14``) is read; reversing entries are emitted as
camt.053.001.14. A single ``services`` facade backs four interfaces (Python API,
CLI, REST API, and companion MCP/LSP servers) for Banking-as-a-Service (BaaS)
and embedded-finance platforms.

2. Applicable Standards
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Standard
     - Application
   * - ISO 20022
     - Financial message schema (camt Bank-to-Customer Cash Management message
       types: camt.052 / camt.053 / camt.054)
   * - ISO 13616
     - IBAN (International Bank Account Number) structure
   * - ISO 9362
     - BIC (Business Identifier Code) format and validation
   * - ISO 7064
     - IBAN check-digit algorithm (mod-97-10)
   * - ISO 17442
     - LEI (Legal Entity Identifier) format and check-digit validation
   * - ISO 4217
     - Currency code set
   * - ISO 13485:2016
     - Quality management system (DHF structure)
   * - ISO 14971:2019
     - Risk management (applied to software risks)
   * - IEC 62304:2006+A1
     - Medical device software lifecycle (process framework)

3. Development Methodology
--------------------------

The project follows an **iterative, test-driven, CI-gated** methodology:

- **Test-Driven Development (TDD):** Tests are written alongside or before
  implementation. No code merges without passing tests.
- **Continuous Integration:** Every commit triggers automated lint, type-check,
  security scan, and full test suite execution.
- **Quality Gates:** All gates must pass before any change is accepted into the
  main branch.
- **Signed Commits:** All commits are cryptographically signed for traceability.

4. Development Phases
---------------------

.. list-table::
   :header-rows: 1
   :widths: 10 25 65

   * - Phase
     - Name
     - Deliverables
   * - 1
     - Statement Parsing
     - Namespace-agnostic parser (``parse/statement_parser.py``) reading
       camt.052 / camt.053 / camt.054 into the typed model
       (``models.py``); defusedxml-safe XML parsing
   * - 2
     - Reason Filtering
     - ISO external return reason code table (``parse/reason_codes.py``),
       entry filtering by reason (``services.filter_entries``,
       ``Statement.entries_with_reason``)
   * - 3
     - Reversing-Entry Generation
     - Reversal builder (``reversal/reversal.py``) that flips the credit/debit
       indicator, sets ``RvslInd``, carries original references and the return
       reason; Jinja2 rendering of camt.053.001.14 (``xml/generate_xml.py``)
   * - 4
     - Validation Framework
     - Official ISO 20022 XSD validation of generated reversals
       (``xml/validate_via_xsd.py``), JSON-Schema validation of flat
       reversing-entry records (``validation/schema_validator.py``), BIC
       (ISO 9362), IBAN (ISO 13616 / 7064 mod-97-10), and LEI (ISO 17442)
       identifier validators
   * - 5
     - Interface Layer
     - Shared ``services`` facade; Click + Rich CLI (parse / entries / reverse
       / message-types / reasons / validate-id), FastAPI REST API, and
       companion MCP and LSP servers
   * - 6
     - Security Hardening
     - defusedxml for XXE / billion-laughs prevention, path traversal jail,
       log sanitization, Jinja2 autoescape
   * - 7
     - Verification & Release
     - pytest suite with 99%+ branch coverage gate, XSD validation of generated
       reversals, parsing of the official ISO 20022 business sample messages,
       cross-platform CI

5. Tools and Environment
------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Category
     - Tool
     - Purpose
   * - Language
     - Python 3.10+
     - Runtime (3.10, 3.11, 3.12 supported)
   * - Package Manager
     - Poetry
     - Dependency management and build
   * - Testing
     - pytest
     - Test runner with markers, fixtures, parametrize
   * - Coverage
     - pytest-cov
     - Branch coverage reporting (99% minimum gate)
   * - Type Checking
     - mypy (strict)
     - Static type analysis, ``disallow_untyped_defs=true``
   * - Linting
     - ruff, black
     - Code style enforcement (line-length=79)
   * - Security
     - Bandit
     - Static application security testing (SAST)
   * - CI
     - GitHub Actions
     - Automated pipeline (test, lint, security, smoke)
   * - Documentation
     - Sphinx + RTD theme
     - ReStructuredText documentation
   * - Containers
     - Docker
     - ``python:3.12-slim`` with non-root user
   * - Pre-commit
     - pre-commit
     - 13 hooks (trailing whitespace, YAML/JSON/TOML check, ruff, black, mypy,
       detect-private-key, etc.)

6. Quality Gates
----------------

Every commit must pass all of the following before merge:

1. **Lint & Format:** ``ruff check`` and ``black --check`` pass with zero findings
2. **Type Check:** ``mypy --strict`` passes with zero errors
3. **Security Scan:** ``bandit -r camt053/`` reports zero issues
4. **Unit Tests:** The full pytest suite passes
5. **Branch Coverage:** >= 99% (enforced via ``--cov-fail-under=99``)
6. **Smoke Tests:** Quick sanity checks pass
7. **Pre-commit Hooks:** All hooks pass

7. Deliverables
---------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Deliverable
     - Description
   * - Source Code
     - ``camt053/`` package (parse, reversal, xml, validation, security, cli,
       api packages plus the ``services`` facade)
   * - Test Suite
     - ``tests/`` directory (parser, reversal, generate_xml, services, business
       samples, validators, and interface tests)
   * - Documentation
     - Sphinx docs including this DHF document set
   * - CI Pipeline
     - ``.github/workflows/ci.yml`` with test, lint, security, and smoke jobs
   * - Docker Image
     - ``Dockerfile`` for containerized deployment of the REST API
   * - PyPI Package
     - Distributable package via ``poetry build``
   * - Schemas & Templates
     - Official ISO 20022 XSDs under ``camt053/xsd/`` (camt.052/053/054,
       versions ``.001.01``–``.001.14``); the camt.053.001.14 reversal template
       and XSD under ``camt053/templates/``; JSON Schemas under
       ``camt053/schemas/``
