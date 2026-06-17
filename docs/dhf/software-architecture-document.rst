.. _dhf-software-architecture:

============================================
Software Architecture Document
============================================

.. list-table:: Document Control
   :widths: 25 75
   :stub-columns: 1

   * - Document ID
     - DHF-004
   * - Version
     - 1.0
   * - Date
     - 2026-03-22
   * - Author
     - camt053 Engineering
   * - Status
     - Released
   * - ISO 13485 Clause
     - 7.3.4 (Design and Development Review)

1. Module Architecture
----------------------

The camt053 library is organized into focused packages, each with a single
responsibility, all backed by one shared service facade:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Package
     - Responsibility
   * - ``services.py``
     - The single shared facade. Exposes the core capabilities as plain
       functions returning plain data (``parse_statement``, ``list_entries``,
       ``filter_entries``, ``build_reversal``, ``generate_reversal``,
       ``generate``, and the reference/validation helpers). Backs the CLI,
       REST API, and companion MCP and LSP servers.
   * - ``parse/``
     - Namespace-agnostic statement parser (``statement_parser.py``) reading
       camt.052 / camt.053 / camt.054 into the typed model; ISO external return
       reason code helpers (``reason_codes.py``)
   * - ``reversal/``
     - Business mapping from a parsed statement entry to a flat reversing-entry
       record (``reversal.py``): flips the credit/debit indicator, sets
       ``RvslInd``, carries original references and the return reason
   * - ``xml/``
     - Reversing-entry rendering via the bundled Jinja2 template
       (``generate_xml.py``) and validation of the rendered document against the
       official ISO 20022 XSD (``validate_via_xsd.py``)
   * - ``validation/``
     - BIC validation (``bic_validator.py``), IBAN validation
       (``iban_validator.py``), LEI validation (``lei_validator.py``), and
       JSON-Schema validation of flat reversing-entry records
       (``schema_validator.py``)
   * - ``security/``
     - Path traversal protection (``validate_path()``), log sanitization
       (``sanitize_for_log()``), ``PathValidationError``, ``SecurityError``
       (``path_validator.py``)
   * - ``api/``
     - FastAPI REST API application (``app.py``) and Pydantic request/response
       models (``models.py``)
   * - ``cli/``
     - Click + Rich command-line interface (``cli.py``) with the ``parse``,
       ``entries``, ``reverse``, ``message-types``, ``reasons``, and
       ``validate-id`` commands
   * - ``templates/``
     - The camt.053.001.14 reversal directory, containing the Jinja2 template
       (``template.xml``) and the official ISO 20022 XSD
       (``camt.053.001.14.xsd``)
   * - ``schemas/``
     - JSON Schemas for the flat reversing-entry records of each supported
       message type (``camt.05x.001.14.schema.json``)
   * - ``xsd/``
     - The official ISO 20022 XSD reference schemas for every supported message
       and version (camt.052 / camt.053 / camt.054, ``.001.01``–``.001.14``)

Top-level modules:

- ``__init__.py`` — Public API exports (``services``, ``parse_statement``,
  the typed model, and ``__version__``)
- ``__main__.py`` — ``main()`` entry point for ``python -m camt053``
- ``constants.py`` — ``valid_xml_types`` list, ``message_names`` map,
  ``STATEMENT_CONTAINERS``, ``return_reason_names``, ``REVERSAL_MESSAGE_TYPE``,
  ``reverse_credit_debit()``, ``BASE_DIR``, ``SCHEMAS_DIR``, ``TEMPLATES_DIR``
- ``models.py`` — Typed dataclasses (``Account``, ``Balance``,
  ``TransactionDetails``, ``Entry``, ``Statement``, ``ParsedDocument``)
- ``exceptions.py`` — Exception hierarchy rooted at ``Camt053Error``

2. Data Flow
------------

The primary data flow is the one-shot reversing-entry workflow: inbound camt
XML → typed model → reason filter → reversal builder → rendered + XSD-validated
camt.053.001.14::

    Inbound camt.05x statement XML
        │
        ▼
    services.generate_reversal(xml, reason_code="AC04")
        │
        ├─▶ parse_document(xml)              # parse/statement_parser.py
        │       │
        │       ├─▶ defusedxml.parse()       # XXE / billion-laughs safe
        │       ├─▶ local-name matching      # namespace-agnostic (.001.01–.14)
        │       └─▶ ParsedDocument           # group header → statements →
        │                                    #   account, balances, entries →
        │                                    #   transaction details
        │
        ├─▶ build_reversal_records(stmt, reason_code)   # reversal/reversal.py
        │       │
        │       ├─▶ entries_with_reason()    # filter by return reason code
        │       ├─▶ reverse_credit_debit()   # CRDT ⇄ DBIT
        │       └─▶ flat records             # RvslInd=true, refs, RtrInf,
        │                                    #   counterparty (RltdPties)
        │
        └─▶ generate_reversal_xml(records)   # xml/generate_xml.py
                │
                ├─▶ Environment(autoescape=True)        # Jinja2 rendering
                ├─▶ template.render(...)                # camt.053.001.14 XML
                └─▶ validate_xml_string_via_xsd()       # official ISO 20022 XSD
                        │
                        └─▶ Validated reversal document returned

The read-only paths (``parse_statement``, ``list_entries``, ``filter_entries``)
share the same parser and stop at the typed model, returning JSON-serialisable
data. ``build_reversal`` and ``generate`` expose the mapping and rendering
stages independently for callers that already hold records.

3. Parsing and Reversal Strategy
--------------------------------

3.1 Namespace-agnostic parsing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Real-world statements arrive in many ISO versions, so the parser
(``parse/statement_parser.py``) matches elements by **local name** rather than
by a fixed namespace URI. The supported message is resolved from the document
container's local name (``constants.STATEMENT_CONTAINERS``), and the exact
version is recovered from the namespace URI when present:

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Container element
     - Message type
     - Name
   * - ``BkToCstmrAcctRpt``
     - camt.052.001.14
     - Bank To Customer Account Report
   * - ``BkToCstmrStmt``
     - camt.053.001.14
     - Bank To Customer Statement
   * - ``BkToCstmrDbtCdtNtfctn``
     - camt.054.001.14
     - Bank To Customer Debit Credit Notification

Each repeated ``Stmt`` / ``Rpt`` / ``Ntfctn`` becomes a ``Statement``; each
``Ntry`` becomes an ``Entry`` carrying its amount, credit/debit indicator,
status, dates, reversal indicator, and per-transaction ``TransactionDetails``
(references, return reason, counterparty).

3.2 Return reason codes
~~~~~~~~~~~~~~~~~~~~~~~~~

Entries are selected for reversal by ISO external return reason code. The codes
the library recognises are defined once in ``constants.return_reason_names`` and
surfaced through ``parse/reason_codes.py``:

.. code-block:: python

   return_reason_names = {
       "AC01": "Incorrect Account Number",
       "AC04": "Closed Account Number",        # headline / default case
       "AC06": "Blocked Account",
       "AG01": "Transaction Forbidden",
       "AM04": "Insufficient Funds",
       "MD07": "End Customer Deceased",
       "RR01": "Missing Debtor Account Or Identification",
       "RR04": "Regulatory Reason",
   }

3.3 Reversing-entry mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For each selected booked entry, ``reversal/reversal.py`` builds a flat record
that the camt.053.001.14 template renders. The mapping:

1. flips the credit/debit indicator (``reverse_credit_debit()``: ``CRDT`` ⇄
   ``DBIT``),
2. sets ``reversal_indicator`` (``RvslInd``) to ``true``,
3. carries the original references (``InstrId`` / ``EndToEndId`` / ``TxId``),
4. records the return reason in ``RtrInf`` with a human-readable ``AddtlInf``
   (via ``describe_reason()``),
5. preserves the counterparty (``RltdPties``) and the source account context,
   and synthesises a closing booked balance where the source carries none.

Adding support for a future ISO version requires only adding the message-type
string to ``valid_xml_types`` (with its ``message_names`` and
``STATEMENT_CONTAINERS`` entries) and bundling its official XSD under ``xsd/``.

4. Exception Hierarchy
----------------------

::

    Camt053Error (base)
    ├── StatementParseError
    │       (empty/malformed/unrecognised statement XML; optional line)
    ├── AccountValidationError
    │   ├── InvalidIBANError
    │   │       (fields: message, iban, field, reason)
    │   ├── InvalidBICError
    │   │       (fields: message, bic, field, reason)
    │   ├── InvalidLEIError
    │   │       (fields: message, lei, field, reason)
    │   └── MissingRequiredFieldError
    │           (fields: message, field, row_number, required_fields)
    ├── XMLGenerationError
    │   │       (Jinja2 rendering failures, XSD validation failures)
    │   └── ReversalGenerationError
    │           (no matching entry, or reversal fails XSD validation)
    ├── ConfigurationError
    │       (invalid / unsupported message-type strings)
    ├── DataSourceError
    │       (file not found, unsupported input)
    └── SchemaValidationError (alias: XSDValidationError)
            (fields: message, errors: list)

All exceptions inherit from ``Camt053Error`` to enable catch-all handling at
API and CLI boundaries.

5. Security Architecture
------------------------

5.1 XML External Entity (XXE) Prevention
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Module:** ``camt053/parse/statement_parser.py``,
  ``camt053/xml/validate_via_xsd.py``
- **Control:** All XML parsing of untrusted bank files uses
  ``defusedxml.ElementTree`` instead of the standard library's
  ``xml.etree.ElementTree``
- **Protection:** Prevents XML bombs (billion-laughs), entity expansion
  attacks, and external entity injection
- **Requirement:** NFR-101

5.2 Path Traversal Protection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Module:** ``camt053/security/path_validator.py``
- **Control:** ``validate_path(untrusted_path, must_exist, base_dir)``
  resolves paths with ``os.path.realpath()`` and rejects any path containing
  ``..`` or resolving outside allowed directories
- **Allowed directories:** current working directory, ``tempfile.gettempdir()``,
  ``/var/tmp`` (Unix only)
- **Requirement:** NFR-102

5.3 Log Sanitization
~~~~~~~~~~~~~~~~~~~~~~

- **Module:** ``camt053/security/path_validator.py``
- **Control:** ``sanitize_for_log(user_input, max_length=100)`` strips control
  characters (newlines, carriage returns, null bytes) and truncates input
  before log emission
- **Requirement:** NFR-103

5.4 Template Injection Prevention
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Module:** ``camt053/xml/generate_xml.py``
- **Control:** ``Environment(loader=FileSystemLoader(...), autoescape=True)``
- **Protection:** All template variables are auto-escaped when rendering the
  reversal, preventing server-side template injection (SSTI)
- **Requirement:** NFR-104

5.5 Container Security
~~~~~~~~~~~~~~~~~~~~~~~~

- **Module:** ``Dockerfile``
- **Control:** REST API runs as ``appuser`` (non-root), slim base image,
  health check endpoint
- **Requirement:** NFR-105

6. Interface Specifications
---------------------------

6.1 Python API (services facade)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from camt053 import services

   # Headline one-shot workflow — returns validated camt.053.001.14 XML
   services.generate_reversal(
       xml: str,                       # incoming statement XML
       reason_code: str = "AC04",      # ISO external return reason
       msg_id: str | None = None,
       creation_date_time: str | None = None,
   ) -> str

   # Read-only paths — return JSON-serialisable plain data
   services.parse_statement(xml: str) -> dict
   services.list_entries(xml: str) -> list[dict]
   services.filter_entries(xml: str, reason_code: str = "AC04") -> list[dict]

   # Records-in entry points and reference/validation helpers
   services.build_reversal(xml, reason_code) -> list[dict]
   services.generate(records: list[dict]) -> str
   services.list_message_types() / services.list_return_reasons()
   services.validate_identifier(kind, value) / services.validate_records(...)

6.2 CLI
~~~~~~~~

::

   camt053 parse        -i <statement.xml | ->
   camt053 entries      -i <statement.xml | -> [-r <reason>]
   camt053 reverse      -i <statement.xml | -> [-r <reason>] [-o <output>]
   camt053 message-types
   camt053 reasons
   camt053 validate-id  -k <iban|bic|lei> -v <value>

The ``parse``, ``entries``, and ``reverse`` commands accept ``-i -`` to read
from stdin, so they compose in a pipeline. **Exit codes:** 0 (success),
1 (parse / reversal / validation error).

6.3 REST API
~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 40 50

   * - Method
     - Endpoint
     - Purpose
   * - GET
     - ``/health``
     - Liveness probe
   * - GET
     - ``/message-types``
     - List supported message types
   * - GET
     - ``/reasons``
     - List known return reason codes
   * - GET
     - ``/message-types/{type}/schema``
     - Reversing-entry input JSON Schema
   * - GET
     - ``/message-types/{type}/required-fields``
     - Required reversing-entry fields
   * - GET
     - ``/validate-identifier``
     - Validate an IBAN, BIC, or LEI
   * - POST
     - ``/validate-records``
     - Validate flat reversing-entry records
   * - POST
     - ``/parse``
     - Parse an incoming statement into structured data
   * - POST
     - ``/entries``
     - List statement entries (optionally filtered by reason)
   * - POST
     - ``/reverse``
     - Generate a reversing entry (returns ``application/xml``)

6.4 Companion servers
~~~~~~~~~~~~~~~~~~~~~~~

The ``camt053-mcp`` (Model Context Protocol) and ``camt053-lsp`` (Language
Server) packages call the same ``services`` facade, so the MCP tools and the
editor diagnostics behave identically to the CLI and REST API.

7. Design Decisions and Rationale
---------------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Decision
     - Choice
     - Rationale
   * - Template engine
     - Jinja2
     - Mature, well-documented, supports autoescape; separates the
       camt.053.001.14 XML structure from the reversal data
   * - XML parser
     - defusedxml
     - Drop-in replacement for stdlib with XXE protection; essential for
       parsing untrusted bank files
   * - Parsing strategy
     - Namespace-agnostic, local-name matching
     - Reads every ISO version (``.001.01``–``.001.14``) of a message, so
       real-world bank files Just Work
   * - Shared facade
     - One ``services`` layer
     - CLI, REST API, MCP, and LSP all call the same backend, so every
       interface behaves identically
   * - Validation library
     - xmlschema + jsonschema
     - Official XSD / JSON Schema implementations; comprehensive error reporting
   * - CLI framework
     - Click + Rich
     - Declarative option syntax, automatic help text, readable tabular output
   * - REST framework
     - FastAPI
     - Automatic OpenAPI docs, Pydantic validation, type hints
   * - Typed model
     - Dependency-free dataclasses
     - Light, JSON-serialisable model that the parser returns and the reversal
       builder consumes; trivially testable
   * - Output validation
     - Mandatory XSD check
     - Every generated reversal is validated against the official ISO 20022 XSD
       before return; generation fails if validation fails
   * - Exception hierarchy
     - Single base class
     - Enables catch-all at boundaries while preserving specific error context
   * - Path security
     - Allowlist directories
     - Defense-in-depth; even if application logic is wrong, path jail prevents
       traversal
