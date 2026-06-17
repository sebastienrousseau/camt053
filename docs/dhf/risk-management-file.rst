.. _dhf-risk-management:

============================================
Risk Management File
============================================

.. list-table:: Document Control
   :widths: 25 75
   :stub-columns: 1

   * - Document ID
     - DHF-005
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
   * - Additional Standards
     - ISO 14971:2019 (Risk Management), IEC 62304:2006+A1 (Software Lifecycle)

1. IEC 62304 Safety Classification
-----------------------------------

**Classification: Class A** (no contribution to hazardous situation)

The camt053 library is a data transformation tool that reads ISO 20022 camt
statements and generates reversing-entry XML. It does not control physical
processes, medical devices, or safety-critical systems. Under IEC 62304, it is
classified as **Class A**.

However, the project voluntarily applies **Class C-level processes** to
demonstrate the highest level of software engineering rigor:

- High branch coverage (99%+ gate)
- Formal risk analysis with mitigations
- Static analysis (mypy strict, bandit SAST)
- Signed commits with full traceability
- Structured design documentation (this DHF)

This voluntary elevation provides audit readiness for deployment in regulated
financial environments and institutional settings, including Banking-as-a-Service
(BaaS) and embedded-finance platforms.

2. Risk Analysis Methodology
-----------------------------

Risks are assessed using an ISO 14971-style framework:

- **Severity:** Impact if the risk is realized (Low / Medium / High / Critical)
- **Probability:** Likelihood of occurrence given normal use (Rare / Unlikely /
  Possible / Likely)
- **Risk Level:** Combination of severity and probability (Low / Medium / High)
- **Mitigation:** Engineering control implemented to reduce risk
- **Residual Risk:** Risk level after mitigation is applied and verified

3. Risk Register
-----------------

.. list-table::
   :header-rows: 1
   :widths: 8 20 12 12 12 36

   * - ID
     - Risk Description
     - Severity
     - Probability
     - Initial Risk
     - Mitigation
   * - R-001
     - Generated reversing entry is XSD-invalid and rejected by the receiving
       financial institution
     - High
     - Possible
     - High
     - Every generated reversal is validated against the official ISO 20022
       camt.053.001.14 XSD via ``validate_xml_string_via_xsd()`` before output.
       ``ReversalGenerationError`` is raised if validation fails.
   * - R-002
     - XML External Entity (XXE) / billion-laughs injection via an untrusted
       incoming bank statement
     - Critical
     - Unlikely
     - High
     - All statement parsing uses ``defusedxml.ElementTree`` instead of stdlib.
       Entity expansion, external entities, and DTD processing are disabled.
   * - R-003
     - Path traversal attack reads or writes files outside intended
       directories when an output path is supplied
     - Critical
     - Unlikely
     - High
     - ``validate_path()`` resolves all paths with ``os.path.realpath()``,
       rejects ``..`` components, and enforces an allowlist of base
       directories (cwd, tempdir, ``/var/tmp``).
   * - R-004
     - A statement is mis-parsed — entries, reasons, or counterparties are
       dropped or misread — so the wrong entries are reversed
     - High
     - Possible
     - High
     - The namespace-agnostic parser matches by local name across every ISO
       version and is exercised against the official ISO 20022 business sample
       messages (``test_business_samples.py``, ``test_parser.py``).
   * - R-005
     - Invalid BIC, IBAN, or LEI on the reversal produces a non-compliant
       message
     - High
     - Possible
     - High
     - ``validate_bic()`` checks ISO 9362 format. ``validate_iban()`` verifies
       ISO 13616 structure and ISO 7064 mod-97-10 checksum. ``validate_lei()``
       verifies ISO 17442 format and check digits.
   * - R-006
     - The reversing entry is booked in the wrong direction (credit/debit
       indicator not flipped), so the reversal does not offset the original
     - Critical
     - Unlikely
     - High
     - ``reverse_credit_debit()`` deterministically maps ``CRDT`` ⇄ ``DBIT``
       and sets ``RvslInd=true``; verified by ``test_reversal.py`` and
       ``test_generate_xml.py``.
   * - R-007
     - An unknown or wrong return reason code selects the wrong entries or
       emits an empty reversal
     - Medium
     - Possible
     - Medium
     - Filtering is case-insensitive over both the entry reason and every
       transaction detail; ``ReversalGenerationError`` is raised when no entry
       matches, so an empty reversal is never silently emitted.
   * - R-008
     - Invalid or unsupported message-type string causes unexpected behaviour
     - Medium
     - Unlikely
     - Low
     - ``valid_xml_types`` and ``STATEMENT_CONTAINERS`` in ``constants.py``
       define the accepted message containers; ``StatementParseError`` is
       raised for any unrecognised container.
   * - R-009
     - Log injection via crafted user input embeds malicious content in
       log files
     - Medium
     - Unlikely
     - Low
     - ``sanitize_for_log(user_input, max_length=100)`` strips control
       characters (newlines, carriage returns, null bytes) and truncates
       before log emission.
   * - R-010
     - Dependency vulnerability in third-party package introduces security
       flaw
     - High
     - Unlikely
     - Medium
     - Dependencies pinned to specific versions in ``pyproject.toml``.
       ``safety`` scanner in dev dependencies. Dependabot / automated
       alerts on GitHub.
   * - R-011
     - Schema drift between the Jinja2 reversal template and the official XSD
       causes silent data loss or generation of non-conformant XML
     - High
     - Rare
     - Medium
     - The reversal template and the official camt.053.001.14 XSD are bundled
       together under ``templates/``; every rendered reversal is validated
       against that XSD and verified end-to-end by ``test_generate_xml.py``.
   * - R-012
     - Server-side template injection (SSTI) via crafted statement field
       values flowing into the reversal
     - Critical
     - Unlikely
     - High
     - Jinja2 ``Environment`` created with ``autoescape=True``. All
       template variables are automatically escaped before rendering.

4. Risk Control Verification
-----------------------------

.. list-table::
   :header-rows: 1
   :widths: 10 30 30 30

   * - Risk ID
     - Mitigation Control
     - Verification Test File(s)
     - Result
   * - R-001
     - XSD validation of every generated reversal
     - ``test_validate_via_xsd.py``, ``test_generate_xml.py``,
       ``test_services.py``
     - Pass
   * - R-002
     - defusedxml for all statement parsing
     - ``test_parser.py`` (malformed / XXE cases),
       ``test_validate_via_xsd.py``
     - Pass
   * - R-003
     - Path validation with directory jail
     - ``test_path_validator.py``
     - Pass
   * - R-004
     - Namespace-agnostic parsing of official business samples
     - ``test_parser.py``, ``test_business_samples.py``
     - Pass
   * - R-005
     - BIC + IBAN + LEI format and checksum validation
     - ``test_validators.py``
     - Pass
   * - R-006
     - Credit/debit indicator flip and ``RvslInd``
     - ``test_reversal.py``, ``test_generate_xml.py``
     - Pass
   * - R-007
     - Reason-code filtering and empty-reversal guard
     - ``test_reversal.py``, ``test_services.py``, ``test_reason_codes.py``
     - Pass
   * - R-008
     - Message-container allowlist
     - ``test_parser.py``
     - Pass
   * - R-009
     - Log sanitization
     - ``test_path_validator.py``
     - Pass
   * - R-010
     - Dependency pinning + safety scanner
     - CI pipeline ``security`` job (Bandit + safety)
     - Pass
   * - R-011
     - Reversal template / XSD validated together
     - ``test_generate_xml.py``, ``test_services.py``
     - Pass
   * - R-012
     - Jinja2 autoescape=True
     - ``test_generate_xml.py``
     - Pass

5. Residual Risk Assessment
----------------------------

.. list-table::
   :header-rows: 1
   :widths: 10 25 25 20 20

   * - Risk ID
     - Initial Risk
     - Mitigation Effectiveness
     - Residual Risk
     - Acceptable?
   * - R-001
     - High
     - XSD validation is deterministic and comprehensive
     - Low
     - Yes
   * - R-002
     - High
     - defusedxml completely disables XXE attack surface
     - Low
     - Yes
   * - R-003
     - High
     - Path jail with realpath resolution eliminates traversal
     - Low
     - Yes
   * - R-004
     - High
     - Verified against the official ISO 20022 business samples
     - Low
     - Yes
   * - R-005
     - High
     - ISO-standard validation algorithms are well-proven
     - Low
     - Yes
   * - R-006
     - High
     - Deterministic indicator flip, covered by tests
     - Low
     - Yes
   * - R-007
     - Medium
     - Empty-reversal guard prevents silent no-op output
     - Low
     - Yes
   * - R-008
     - Low
     - Container allowlist rejects unrecognised messages
     - Low
     - Yes
   * - R-009
     - Low
     - Control character stripping + truncation
     - Low
     - Yes
   * - R-010
     - Medium
     - Pinning + scanning reduces window of exposure
     - Low
     - Yes
   * - R-011
     - Medium
     - Gold master tests catch any schema drift
     - Low
     - Yes
   * - R-012
     - High
     - Autoescape is a framework-level guarantee
     - Low
     - Yes

**Overall residual risk: Low.** All identified risks have been mitigated to an
acceptable level through engineering controls that are verified by automated
tests and CI pipeline checks.
