.. _dhf-traceability-matrix:

============================================
Traceability Matrix
============================================

.. list-table:: Document Control
   :widths: 25 75
   :stub-columns: 1

   * - Document ID
     - DHF-007
   * - Version
     - 1.0
   * - Date
     - 2026-03-22
   * - Author
     - camt053 Engineering
   * - Status
     - Released
   * - ISO 13485 Clause
     - 7.3.10 (Design and Development Files)

1. Forward Traceability: Requirement to Implementation to Test
--------------------------------------------------------------

1.1 FR-100: Statement Parsing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - FR-101
     - ``parse/statement_parser.py``
     - ``parse_document()``, ``parse_statement()``
     - ``test_parser.py``, ``test_business_samples.py``
   * - FR-102
     - ``parse/statement_parser.py``
     - ``_message_type_for()`` (namespace-agnostic camt.052/053/054 dispatch)
     - ``test_parser.py``
   * - FR-103
     - ``models.py``
     - ``ParsedDocument``, ``Statement``, ``Entry``, ``Account``,
       ``Balance``, ``TransactionDetails``
     - ``test_models.py``, ``test_parser.py``
   * - FR-104
     - ``parse/statement_parser.py``
     - ``parse_document()`` (every ISO version via local-name matching)
     - ``test_business_samples.py``, ``test_init_and_gold_master.py``

1.2 FR-200: Reason-Code Filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - FR-201
     - ``parse/reason_codes.py``
     - ``describe_reason()``, ``is_known_reason()``
     - ``test_reason_codes.py``
   * - FR-202
     - ``parse/reason_codes.py``
     - ``list_reason_codes()``
     - ``test_reason_codes.py``
   * - FR-203
     - ``models.py``
     - ``Statement.entries_with_reason()`` (e.g. AC04 Closed Account)
     - ``test_models.py``
   * - FR-204
     - ``services.py``
     - ``filter_entries()`` (one-shot reason filtering)
     - ``test_services.py``

1.3 FR-300: Reversal Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - FR-301
     - ``reversal/reversal.py``
     - ``build_reversal_record()`` (flip ``CdtDbtInd``, set ``RvslInd=true``)
     - ``test_reversal.py``
   * - FR-302
     - ``reversal/reversal.py``
     - ``build_reversal_records()`` (carry refs/reason/counterparty)
     - ``test_reversal.py``
   * - FR-303
     - ``services.py``
     - ``build_reversal()``, ``generate_reversal()`` (parse → filter →
       reverse)
     - ``test_services.py``

1.4 FR-400: XSD Validation and XML Rendering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - FR-401
     - ``xml/generate_xml.py``
     - ``generate_reversal_xml()``,
       ``generate_reversal_for_statement()``
     - ``test_generate_xml.py``
   * - FR-402
     - ``xml/generate_xml.py``
     - ``write_reversal_xml()``
     - ``test_generate_xml.py``
   * - FR-403
     - ``xml/validate_via_xsd.py``
     - ``validate_xml_string_via_xsd()``, ``validate_via_xsd()``
       (official camt.053.001.14 XSD)
     - ``test_validate_via_xsd.py``, ``test_generate_xml.py``
   * - FR-404
     - ``xml/validate_via_xsd.py``
     - ``_render_and_validate()`` round-trip against bundled XSD
     - ``test_generate_xml.py``, ``test_init_and_gold_master.py``

1.5 FR-500: Identifier and Schema Validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - FR-501
     - ``validation/iban_validator.py``
     - ``validate_iban()``, ``validate_iban_format()``,
       ``validate_iban_checksum()``, ``validate_iban_safe()``
     - ``test_validators.py``
   * - FR-502
     - ``validation/bic_validator.py``
     - ``validate_bic()``, ``validate_bic_format()``,
       ``validate_bic_safe()``
     - ``test_validators.py``
   * - FR-503
     - ``validation/lei_validator.py``
     - ``validate_lei()``, ``validate_lei_format()``,
       ``validate_lei_checksum()``, ``validate_lei_safe()``
     - ``test_validators.py``
   * - FR-504
     - ``validation/schema_validator.py``
     - ``SchemaValidator``, ``ValidationError``
     - ``test_schema_validator.py``
   * - FR-505
     - ``services.py``
     - ``validate_identifier()``, ``validate_records()``,
       ``get_input_schema()``, ``get_required_fields()``
     - ``test_services.py``

1.6 FR-600: Interfaces
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - FR-601
     - ``services.py``, ``__init__.py``
     - ``parse_statement()``, ``list_entries()``, ``generate_reversal()``
       (Python facade)
     - ``test_services.py``, ``test_init_and_gold_master.py``
   * - FR-602
     - ``cli/cli.py``
     - Click group: ``parse``, ``entries``, ``reverse``,
       ``message-types``, ``reasons``, ``validate-id``
     - ``test_cli.py``
   * - FR-603
     - ``api/app.py``, ``api/models.py``
     - FastAPI endpoints: ``/health``, ``/message-types``, ``/reasons``,
       ``/parse``, ``/entries``, ``/reverse``, ``/validate-identifier``,
       ``/validate-records``
     - ``test_api.py``
   * - FR-604
     - ``__main__.py``
     - ``main()`` module entry point
     - ``test_main_entry.py``

1.7 FR-700: Error Handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - FR-701
     - ``exceptions.py``
     - ``AccountValidationError``, ``InvalidIBANError``,
       ``InvalidBICError``, ``InvalidLEIError``,
       ``MissingRequiredFieldError``
     - ``test_exceptions.py``, ``test_validators.py``
   * - FR-702
     - ``exceptions.py``
     - ``XMLGenerationError``, ``ReversalGenerationError``
     - ``test_exceptions.py``, ``test_generate_xml.py``
   * - FR-703
     - ``exceptions.py``
     - ``StatementParseError``
     - ``test_exceptions.py``, ``test_parser.py``
   * - FR-704
     - ``exceptions.py``
     - ``ConfigurationError``, ``SchemaValidationError``
     - ``test_exceptions.py``, ``test_schema_validator.py``

1.8 NFR-100: Security
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - NFR-101
     - ``parse/statement_parser.py``, ``xml/validate_via_xsd.py``
     - ``defusedxml.ElementTree`` parsing (XXE-safe)
     - ``test_parser.py``, ``test_validate_via_xsd.py``
   * - NFR-102
     - ``security/path_validator.py``
     - ``validate_path()``, ``_resolve_within_allowed_bases()``,
       ``_is_allowed_directory()``
     - ``test_path_validator.py``
   * - NFR-103
     - ``security/path_validator.py``
     - ``sanitize_for_log()`` (log-injection redaction)
     - ``test_path_validator.py``
   * - NFR-104
     - ``xml/generate_xml.py``
     - Jinja2 ``Environment(autoescape=True)``
     - ``test_generate_xml.py``
   * - NFR-105
     - ``Dockerfile``
     - ``USER appuser``
     - Dockerfile inspection (non-root user)

1.9 NFR-200: Quality
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - NFR-201
     - All test files
     - ``--cov-fail-under=99``
     - CI test job (pytest-cov)
   * - NFR-202
     - All source files
     - ``mypy --strict``
     - CI lint job
   * - NFR-203
     - All source files
     - ``bandit -r camt053/``
     - CI security job
   * - NFR-204
     - All source files
     - ``ruff check``, ``black --check``
     - CI lint job

1.10 NFR-300: Compatibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - NFR-301
     - ``pyproject.toml``
     - ``python = "^3.9.2"``
     - CI test matrix (3.9, 3.10, 3.11, 3.12)
   * - NFR-302
     - ``.github/workflows/ci.yml``
     - OS matrix: ubuntu, macos, windows
     - CI test job (3 OS configurations)
   * - NFR-303
     - ``pyproject.toml``
     - Poetry build configuration
     - CI smoke job (install verification)

1.11 NFR-400: Performance
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - NFR-401
     - ``xml/validate_via_xsd.py``
     - ``_get_cached_schema()`` (compiled-schema reuse)
     - ``test_validate_via_xsd.py``
   * - NFR-402
     - ``parse/statement_parser.py``
     - Single-pass element traversal of inbound statements
     - ``test_parser.py``, ``test_business_samples.py``

1.12 NFR-500: Maintainability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 25 30 35

   * - Req ID
     - Source Module
     - Source Function
     - Test File(s)
   * - NFR-501
     - ``services.py``
     - Single facade backing the Python API, CLI, REST API, MCP and LSP
       servers
     - ``test_services.py``
   * - NFR-502
     - ``exceptions.py``
     - ``Camt053Error`` base class hierarchy
     - ``test_exceptions.py``
   * - NFR-503
     - ``constants.py``
     - Message-type allowlist and bundled-asset paths
     - ``test_init_and_gold_master.py``

2. Reverse Traceability: Test File to Requirements
---------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Test File
     - Requirements Covered
   * - ``test_parser.py``
     - FR-101, FR-102, FR-103, FR-703, NFR-101, NFR-402
   * - ``test_reason_codes.py``
     - FR-201, FR-202
   * - ``test_models.py``
     - FR-103, FR-203
   * - ``test_reversal.py``
     - FR-301, FR-302
   * - ``test_generate_xml.py``
     - FR-401, FR-402, FR-403, FR-404, FR-702, NFR-104
   * - ``test_validate_via_xsd.py``
     - FR-403, NFR-101, NFR-401
   * - ``test_services.py``
     - FR-204, FR-303, FR-505, FR-601, NFR-501
   * - ``test_cli.py``
     - FR-602
   * - ``test_api.py``
     - FR-603
   * - ``test_validators.py``
     - FR-501, FR-502, FR-503, FR-701
   * - ``test_schema_validator.py``
     - FR-504, FR-704
   * - ``test_exceptions.py``
     - FR-701, FR-702, FR-703, FR-704, NFR-502
   * - ``test_path_validator.py``
     - NFR-102, NFR-103
   * - ``test_init_and_gold_master.py``
     - FR-104, FR-404, FR-601, NFR-503
   * - ``test_main_entry.py``
     - FR-604
   * - ``test_business_samples.py``
     - FR-101, FR-104, NFR-402

3. Risk Control Traceability
-----------------------------

.. list-table::
   :header-rows: 1
   :widths: 10 30 30 30

   * - Risk ID
     - Mitigation
     - Source Module
     - Verification Test(s)
   * - R-001
     - XSD validation of all generated reversals
     - ``xml/validate_via_xsd.py``
     - ``test_validate_via_xsd.py``, ``test_generate_xml.py``
   * - R-002
     - defusedxml for all XML parsing (XXE-safe)
     - ``parse/statement_parser.py``, ``xml/validate_via_xsd.py``
     - ``test_parser.py``, ``test_validate_via_xsd.py``
   * - R-003
     - Path validation with directory jail
     - ``security/path_validator.py``
     - ``test_path_validator.py``
   * - R-004
     - Namespace-agnostic parsing across every ISO version
     - ``parse/statement_parser.py``
     - ``test_parser.py``, ``test_business_samples.py``
   * - R-005
     - BIC + IBAN + LEI validators
     - ``validation/bic_validator.py``,
       ``validation/iban_validator.py``,
       ``validation/lei_validator.py``
     - ``test_validators.py``
   * - R-006
     - JSON-schema validation of input records
     - ``validation/schema_validator.py``
     - ``test_schema_validator.py``
   * - R-007
     - Correct credit/debit flip and ``RvslInd`` on reversal
     - ``reversal/reversal.py``
     - ``test_reversal.py``
   * - R-008
     - Message-type allowlist
     - ``constants.py``
     - ``test_init_and_gold_master.py``
   * - R-009
     - Log sanitization
     - ``security/path_validator.py``
     - ``test_path_validator.py``
   * - R-010
     - Dependency pinning + safety scanner
     - ``pyproject.toml``, CI ``security`` job
     - CI pipeline verification
   * - R-011
     - Conformance against official ISO business samples
     - ``tests/gold_master/`` and ``camt053/xsd/``
     - ``test_business_samples.py``, ``test_init_and_gold_master.py``
   * - R-012
     - Jinja2 autoescape=True
     - ``xml/generate_xml.py``
     - ``test_generate_xml.py``
