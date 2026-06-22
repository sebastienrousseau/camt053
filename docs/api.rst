.. _api-reference:

=============
API Reference
=============

This page documents the public Python API of **camt053**. Every developer
surface (CLI, REST API, MCP, and LSP) is built on the shared
:mod:`camt053.services` facade, so the functions documented here behave
identically across interfaces.

Top-level package
=================

.. automodule:: camt053
   :members:
   :undoc-members:
   :show-inheritance:

Services facade
===============

.. automodule:: camt053.services
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: AuditEvent, ChainVerification, HashChain,
                     SchemaClassification, UnsupportedSchemaError

The dataclasses and exception types re-exported through this facade
(``AuditEvent``, ``ChainVerification``, ``HashChain``,
``SchemaClassification``, ``UnsupportedSchemaError``) have their
canonical documentation in :mod:`camt053.audit` and
:mod:`camt053.schema_version`. They are intentionally excluded here
so Sphinx does not emit duplicate-object-description warnings; the
facade convenience (``services.HashChain`` etc.) still works at
runtime.

Audit log + schema-version negotiation
======================================

The append-only HMAC hash-chain audit primitives
(:class:`~camt053.audit.HashChain`, :class:`~camt053.audit.AuditEvent`,
:class:`~camt053.audit.ChainVerification`,
:func:`~camt053.audit.verify_chain`,
:func:`~camt053.audit.compute_event_hmac`) live in
:mod:`camt053.audit`. Schema-version detection and classification
(:class:`~camt053.schema_version.SchemaClassification`,
:exc:`~camt053.schema_version.UnsupportedSchemaError`,
:func:`~camt053.schema_version.detect_schema_version`,
:func:`~camt053.schema_version.classify_schema_version`,
:func:`~camt053.schema_version.validate_schema_version`) lives in
:mod:`camt053.schema_version`.

Both modules are re-exported through :mod:`camt053.services` for the
facade convenience; the docstrings on the source modules carry the
full reference text. Cross-references resolve to the canonical home.

Exceptions
==========

Every exception inherits from :class:`~camt053.exceptions.Camt053Error` and
carries a stable, machine-readable ``code``.

.. automodule:: camt053.exceptions
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:
