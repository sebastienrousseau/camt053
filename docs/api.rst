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

Exceptions
==========

Every exception inherits from :class:`~camt053.exceptions.Camt053Error` and
carries a stable, machine-readable ``code``.

.. automodule:: camt053.exceptions
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:
