.. _dhf-software-requirements:

============================================
Software Requirements Specification
============================================

.. list-table:: Document Control
   :widths: 25 75
   :stub-columns: 1

   * - Document ID
     - DHF-003
   * - Version
     - 1.0
   * - Date
     - 2026-03-22
   * - Author
     - camt053 Engineering
   * - Status
     - Released
   * - ISO 13485 Clause
     - 7.3.3 (Design and Development Outputs)

1. Functional Requirements
--------------------------

1.1 FR-100: Statement Parsing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 60 25

   * - ID
     - Requirement
     - Priority
   * - FR-101
     - The system shall parse incoming ISO 20022 camt Bank-to-Customer Cash
       Management statements into a typed model (group header → statements →
       account, balances, entries → transaction details) via
       ``parse/statement_parser.py``.
     - Essential
   * - FR-102
     - The system shall read the camt.052 (Account Report), camt.053
       (Bank to Customer Statement), and camt.054 (Debit Credit Notification)
       message families, identified by the document container local name
       (``constants.STATEMENT_CONTAINERS``).
     - Essential
   * - FR-103
     - Parsing shall be namespace-agnostic: every published ISO version
       (``.001.01`` through ``.001.14``) of a supported message shall be read
       by matching elements on local name rather than a fixed namespace URI.
     - Essential
   * - FR-104
     - The system shall expose the parsed document as JSON-serialisable plain
       data via ``ParsedDocument.to_dict()`` and ``services.parse_statement()``.
     - Essential
   * - FR-105
     - The system shall enumerate every entry across all statements of a
       document via ``ParsedDocument.all_entries()`` and
       ``services.list_entries()``.
     - Important

1.2 FR-200: Reason Filtering and Reversing-Entry Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 60 25

   * - ID
     - Requirement
     - Priority
   * - FR-201
     - The system shall filter statement entries by ISO external return reason
       code (case-insensitive), matching both the entry-level reason and every
       transaction detail, via ``services.filter_entries()`` and
       ``Statement.entries_with_reason()``.
     - Essential
   * - FR-202
     - The system shall expose the known ISO external return reason codes
       (AC01, AC04, AC06, AG01, AM04, MD07, RR01, RR04) with their
       human-readable names via ``parse/reason_codes.py``; AC04 (Closed
       Account) is the default and headline case.
     - Essential
   * - FR-203
     - The system shall build flat reversing-entry records from the matching
       entries via ``reversal/reversal.py``, flipping the credit/debit
       indicator (``CRDT`` ⇄ ``DBIT``) and setting ``RvslInd`` to ``true``.
     - Essential
   * - FR-204
     - Each reversing entry shall carry the original references (``InstrId`` /
       ``EndToEndId`` / ``TxId``), the return reason in ``RtrInf`` (code plus
       a human-readable ``AddtlInf``), and the counterparty (``RltdPties``).
     - Essential
   * - FR-205
     - The system shall render the reversing entries as a camt.053.001.14
       statement via the bundled Jinja2 template
       (``xml/generate_xml.py``, ``constants.REVERSAL_MESSAGE_TYPE``).
     - Essential
   * - FR-206
     - The system shall provide a one-shot workflow
       (``services.generate_reversal()``) that parses an incoming statement,
       selects the entries for a reason code, and returns the validated
       reversing-entry document.
     - Essential
   * - FR-207
     - The system shall raise ``ReversalGenerationError`` when no statement
       entry matches the requested return reason, so that an empty reversal is
       never silently emitted.
     - Essential
   * - FR-208
     - The system shall render flat reversing-entry records supplied directly
       by a caller (e.g. built elsewhere or loaded from a data file) via
       ``services.generate()`` / ``generate_reversal_xml()``.
     - Important

1.3 FR-300: Validation
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 60 25

   * - ID
     - Requirement
     - Priority
   * - FR-301
     - The system shall validate every generated reversing-entry document
       against the official ISO 20022 camt.053.001.14 XSD bundled in
       ``camt053/templates/`` before returning it; generation shall fail if
       validation fails (``xml/validate_via_xsd.py``).
     - Essential
   * - FR-302
     - The system shall validate BIC codes against ISO 9362 format rules via
       ``validate_bic()`` / ``validate_bic_safe()``.
     - Essential
   * - FR-303
     - The system shall validate IBAN codes against ISO 13616 structure using
       ISO 7064 mod-97-10 checksum verification via ``validate_iban()`` /
       ``validate_iban_safe()``.
     - Essential
   * - FR-304
     - The system shall validate LEI codes against ISO 17442 format and ISO
       7064 check-digit rules via ``validate_lei()`` / ``validate_lei_safe()``.
     - Essential
   * - FR-305
     - The system shall validate flat reversing-entry records against a message
       type's JSON Schema via ``SchemaValidator`` (``validate_records()``),
       returning a structured report of row, path, and message for each error.
     - Essential
   * - FR-306
     - The system shall expose the input JSON Schema and the required field
       names for a supported message type via ``get_input_schema()`` and
       ``get_required_fields()``.
     - Important

1.4 FR-400: Reference Data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 60 25

   * - ID
     - Requirement
     - Priority
   * - FR-401
     - The system shall enumerate every supported cash-management message type
       with its human-readable name via ``services.list_message_types()``.
     - Essential
   * - FR-402
     - The system shall enumerate every known ISO external return reason code
       with its name via ``services.list_return_reasons()``.
     - Essential
   * - FR-403
     - The system shall validate a financial identifier of kind ``iban``,
       ``bic``, or ``lei`` via ``services.validate_identifier()``.
     - Essential
   * - FR-404
     - The system shall reject an unsupported identifier kind or message type
       with a clear ``ValueError``.
     - Important

1.5 FR-500: Reversing-Entry Mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 60 25

   * - ID
     - Requirement
     - Priority
   * - FR-501
     - The reversing entry shall preserve the source account context (IBAN or
       proprietary identifier, currency, owner name, servicer BIC) from the
       parsed statement's account.
     - Essential
   * - FR-502
     - The camt.053 schema requires at least one balance; the reversal shall
       carry the source statement's first balance, or synthesise a closing
       booked balance (``CLBD``) when none is present.
     - Essential
   * - FR-503
     - The reversing entry shall record a booked status and derive its entry
       reference, original reference, amount, currency, booking date, and value
       date from the original booked entry.
     - Essential
   * - FR-504
     - The return reason carried on the reversing entry shall be described in
       human-readable terms via ``describe_reason()`` for the ``AddtlInf``
       element.
     - Essential
   * - FR-505
     - Field values mapped onto the reversal shall be truncated to the lengths
       permitted by the camt.053.001.14 schema (e.g. references to 35
       characters, additional information to 105 characters).
     - Important
   * - FR-506
     - The reversal group-header message id, statement id, and creation
       timestamp shall default to values derived from the source statement and
       be overridable by the caller.
     - Important

1.6 FR-600: Interfaces
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 60 25

   * - ID
     - Requirement
     - Priority
   * - FR-601
     - The system shall expose a Python API through the ``camt053.services``
       facade (``parse_statement``, ``filter_entries``, ``generate_reversal``,
       and the reference and validation functions) as the single shared backend
       for all interfaces.
     - Essential
   * - FR-602
     - The system shall provide a Click + Rich CLI (``camt053``) with the
       ``parse``, ``entries``, ``reverse``, ``message-types``, ``reasons``, and
       ``validate-id`` commands, accepting ``-i -`` to read statement XML from
       stdin.
     - Essential
   * - FR-603
     - The system shall provide a FastAPI REST API (``camt053.api.app``) with
       endpoints for ``GET /health``, ``GET /message-types``, ``GET /reasons``,
       schema and required-field lookup, ``GET /validate-identifier``,
       ``POST /validate-records``, ``POST /parse``, ``POST /entries``, and
       ``POST /reverse`` (returning ``application/xml``).
     - Essential
   * - FR-604
     - Companion packages shall expose the same ``services`` facade as an MCP
       server (``camt053-mcp``) and a Language Server (``camt053-lsp``), so all
       four interfaces behave identically.
     - Important

1.7 FR-700: Error Handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 60 25

   * - ID
     - Requirement
     - Priority
   * - FR-701
     - The system shall raise ``StatementParseError`` for empty, malformed, or
       unrecognised statement XML (including a non-``<Document>`` root or an
       unsupported message container), reporting the offending line where
       available.
     - Essential
   * - FR-702
     - The system shall raise ``ReversalGenerationError`` (a subtype of
       ``XMLGenerationError``) when no entry matches the reason code or when the
       rendered reversal fails XSD validation.
     - Essential
   * - FR-703
     - The system shall raise ``AccountValidationError`` (with sub-types
       ``InvalidIBANError``, ``InvalidBICError``, ``InvalidLEIError``,
       ``MissingRequiredFieldError``) for identifier and record validation
       failures.
     - Essential
   * - FR-704
     - The system shall raise ``ConfigurationError`` for invalid or unsupported
       message-type strings; all exceptions shall inherit from ``Camt053Error``.
     - Essential

2. Non-Functional Requirements
------------------------------

2.1 NFR-100: Security
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 60 25

   * - ID
     - Requirement
     - Priority
   * - NFR-101
     - The system shall use ``defusedxml`` for all XML parsing to prevent
       XXE (XML External Entity) injection attacks.
     - Essential
   * - NFR-102
     - The system shall validate all file paths via ``validate_path()`` to
       prevent path traversal attacks, restricting access to the current
       working directory, system temp directory, and ``/var/tmp``.
     - Essential
   * - NFR-103
     - The system shall sanitize all user-supplied values before including
       them in log output via ``sanitize_for_log()``.
     - Essential
   * - NFR-104
     - The system shall use ``autoescape=True`` in the Jinja2 template
       environment to prevent template injection.
     - Essential
   * - NFR-105
     - The system shall run under a non-root user (``appuser``) when
       deployed in Docker.
     - Essential

2.2 NFR-200: Quality
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 60 25

   * - ID
     - Requirement
     - Priority
   * - NFR-201
     - The test suite shall achieve >= 99% branch coverage as enforced by
       ``--cov-fail-under=99``.
     - Essential
   * - NFR-202
     - The codebase shall pass ``mypy --strict`` with zero errors.
     - Essential
   * - NFR-203
     - The codebase shall pass ``bandit -r camt053/`` with zero findings.
     - Essential
   * - NFR-204
     - The codebase shall pass ``ruff check`` and ``black --check`` with
       zero findings.
     - Essential

2.3 NFR-300: Compatibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 60 25

   * - ID
     - Requirement
     - Priority
   * - NFR-301
     - The system shall support Python 3.10, 3.11, and 3.12.
     - Essential
   * - NFR-302
     - The system shall pass CI on Linux (Ubuntu), macOS, and Windows.
     - Essential
   * - NFR-303
     - The system shall be installable via ``pip install`` and
       ``poetry install``.
     - Essential

2.4 NFR-400: Performance
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 60 25

   * - ID
     - Requirement
     - Priority
   * - NFR-401
     - XSD schema parsing shall be cached (LRU cache, maxsize=16) to avoid
       redundant parsing on repeated validations.
     - Important
   * - NFR-402
     - The parser shall stream the document with a single defusedxml pass and
       match elements by local name, so large statements are read without
       building per-version namespace maps.
     - Important
   * - NFR-403
     - The system shall return plain, JSON-serialisable data from every service
       function, so interfaces add no per-call serialisation cost.
     - Desirable

2.5 NFR-500: Maintainability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 60 25

   * - ID
     - Requirement
     - Priority
   * - NFR-501
     - All interfaces (Python API, CLI, REST API, MCP, LSP) shall be thin
       wrappers over the single ``camt053.services`` facade, so they behave
       identically.
     - Important
   * - NFR-502
     - All exceptions shall inherit from ``Camt053Error`` to enable
       catch-all handling and maintain a consistent exception hierarchy.
     - Important
   * - NFR-503
     - The set of supported message types shall be defined once in
       ``constants.valid_xml_types`` (with ``message_names`` and
       ``STATEMENT_CONTAINERS``), so new versions are added without modifying
       the parser.
     - Important
