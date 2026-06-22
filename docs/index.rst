camt053 Documentation
=====================

**camt053** is a Python library for the modern, AI-assisted treasury stack:
read ISO 20022 camt Bank-to-Customer Cash Management messages (camt.053 / 052 /
054), extract booked entries by return reason code, and generate validated
reversing entries. Generated reversals are validated against the official ISO
20022 ``camt.053.001.14`` schema.

The headline workflow
---------------------

   *"Read this incoming bank statement XML, parse out the transactions with
   error code AC04, and automatically generate the reversing entry."*

.. code-block:: python

   from camt053 import services

   reversal_xml = services.generate_reversal(statement_xml, reason_code="AC04")

Interfaces
----------

Four developer-facing surfaces sit on top of one shared service layer
(``camt053.services``), so they all behave identically:

* **Python API** — ``parse_statement`` / ``generate_reversal_for_statement`` /
  ``camt053.services``.
* **Command-line interface** — the ``camt053`` console command
  (``parse``, ``entries``, ``reverse``, ``message-types``, ``reasons``,
  ``validate-id``).
* **REST API** — a FastAPI application (``camt053.api.app:app``).
* **MCP server** — a Model Context Protocol server (``camt053-mcp``) exposing
  the library as tools for AI agents.
* **LSP server** — a Language Server (``camt053-lsp``) providing diagnostics,
  completion, and hover for reversing-entry data files in editors.

The MCP and LSP servers ship as companion packages (Python 3.10+):

.. code-block:: sh

   pip install camt053-mcp camt053-lsp

Runnable, self-contained examples for every feature live in the ``examples/``
directory (see ``examples/README.md``).

Quick Start
-----------

.. code-block:: python

   from camt053 import parse_statement, services

   stmt = parse_statement(incoming_xml)
   print(stmt.account.identifier(), len(stmt.entries), "entries")

   ac04 = services.filter_entries(incoming_xml, "AC04")
   reversal = services.generate_reversal(incoming_xml, reason_code="AC04")

API Reference
-------------

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api

Schema-version support matrix
-----------------------------

.. toctree::
   :maxdepth: 2
   :caption: Supported camt.05x revisions

   version-matrix

Posts
-----

.. toctree::
   :maxdepth: 1
   :caption: Release announcements

   posts/2026-06-22-shipping-camt053-v006-for-the-november-2026-cliff

Design History File
-------------------

.. toctree::
   :maxdepth: 2
   :caption: Design History File (DHF)

   dhf/index

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
