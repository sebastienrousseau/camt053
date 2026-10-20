<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->

# Scope comparison

The comparison that matters for camt053 is between the surfaces of its own
suite, which all call the same `camt053.services` facade. No competitor
ranking or comparative performance claim is made.

| Project | Reads camt.05x | Generates reversals | XSD validation | Interface | Other input |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **camt053** | camt.052, .053, .054 | Yes | Yes | Python, CLI, REST | |
| camt053-mcp | Through the core | Through the core | Through the core | MCP tools for agents | MT940 and MT942 migration |
| camt053-lsp | | | | LSP diagnostics in an editor | Reversing-entry data files |
| camt053-loader-mt940 | Produces camt.053 | Through the core | | Python | SWIFT MT940 |
| camt053-loader-mt942 | Produces camt.052 | Through the core | | Python | SWIFT MT942 |
| camt053-writer-xlsx | Reads parsed statements | | | Python | Writes `.xlsx` |

Sources: each package's `pyproject.toml` description and README, and
`camt053.suite`. A blank cell means the package does not offer it.

Choose the core when you process statements in Python or a shell; add the MCP
server when an agent does the work, a loader when the bank still sends MT940
or MT942, and the writer when someone needs a spreadsheet.
