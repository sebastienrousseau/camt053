"""What the camt053 suite is, and how its versions move.

Users install more than one package -- `camt053`, `camt053-mcp`,
`camt053-lsp`, a loader, a writer -- and the failure they hit is a
version they cannot reason about: is `camt053-loader-mt940==0.0.14`
supposed to work with `camt053==0.0.15`?

The suite answers that with a single rule: **every member ships the same
version as the core.** One number describes the whole suite. If the core
is at ``0.0.16`` then so is every wrapper, loader and writer, and a user
reading two different numbers is reading a mistake rather than a
deliberate difference they need to understand.

Versions advance in ``0.0.1`` steps and stay on the ``0.0.x`` line;
``0.1.0`` follows ``0.0.999``, not ``0.0.16``.

Two rules follow, and both are checked by
``scripts/check_suite_consistency.py``:

1. Every member's published version must equal the core's.
2. Every member's declared ``camt053`` floor must be a version that
   actually exists, or the combination is uninstallable.

Rule 2 is not hypothetical here. Every satellite declared
``camt053>=0.0.6`` while the core was at ``0.0.15`` -- resolvable, but
nine releases of drift that nothing was watching.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Final, NamedTuple


class SuiteMember(NamedTuple):
    """One published package in the suite.

    Attributes:
        distribution: The name on PyPI.
        repository: The GitHub repository, ``owner/name``.
        role: What the package is, for the README table and messages.
        summary: One line describing it.
    """

    distribution: str
    repository: str
    role: str
    summary: str


#: The core distribution every other member depends on.
CORE: Final[str] = "camt053"

#: Every published member of the suite, keyed by distribution name.
#:
#: Read-only: this is reference data, and a caller reshaping it would
#: change what a consistency check believes about the world.
SUITE: Final[MappingProxyType[str, SuiteMember]] = MappingProxyType(
    {
        member.distribution: member
        for member in (
            SuiteMember(
                distribution="camt053",
                repository="sebastienrousseau/camt053",
                role="core",
                summary="Core library and CLI.",
            ),
            SuiteMember(
                distribution="camt053-mcp",
                repository="sebastienrousseau/camt053-mcp",
                role="wrapper",
                summary="Model Context Protocol server.",
            ),
            SuiteMember(
                distribution="camt053-lsp",
                repository="sebastienrousseau/camt053-lsp",
                role="wrapper",
                summary="Language server for statement files.",
            ),
            SuiteMember(
                distribution="camt053-loader-mt940",
                repository="sebastienrousseau/camt053-loader-mt940",
                role="loader",
                summary="SWIFT MT940 statement loader.",
            ),
            SuiteMember(
                distribution="camt053-loader-mt942",
                repository="sebastienrousseau/camt053-loader-mt942",
                role="loader",
                summary="SWIFT MT942 interim statement loader.",
            ),
            SuiteMember(
                distribution="camt053-writer-xlsx",
                repository="sebastienrousseau/camt053-writer-xlsx",
                role="writer",
                summary="Excel (.xlsx) statement writer.",
            ),
        )
    }
)


def members() -> tuple[SuiteMember, ...]:
    """Return every member of the suite, core first.

    Every member ships the core's version, so there is deliberately no
    accessor for a subset -- the absence of one is the policy.

    Returns:
        All suite members, core first.

    Example:
        >>> members()[0].distribution
        'camt053'
    """
    return tuple(SUITE.values())


def members_by_role(role: str) -> tuple[SuiteMember, ...]:
    """Return the members with a given ``role``.

    Roles describe what a package *is* -- core, wrapper, loader, writer
    -- not how it is versioned. They exist for documentation and error
    messages; they carry no versioning meaning.

    Args:
        role: One of ``core``, ``wrapper``, ``loader``, ``writer``.

    Returns:
        The matching members, in registry order.

    Example:
        >>> [m.distribution for m in members_by_role("writer")]
        ['camt053-writer-xlsx']
    """
    return tuple(m for m in SUITE.values() if m.role == role)
