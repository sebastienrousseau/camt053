"""The declared runtime ranges admit no release with a known advisory.

The lock file only proves what *this* repository resolves. Anyone who
installs camt053 resolves the ranges in ``pyproject.toml`` instead, so a
range whose floor sits below a fixed release still lets an affected
version in, even while pip-audit and Dependabot report nothing here.
That happened twice before 0.0.23: ``cryptography >=48.0.1`` still
admitted the 48.x and 49.x releases behind GHSA-g6cj-pr64-35w5, and the
web stack (``fastapi >=0.95``) let starlette and h11 resolve below their
fixes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised only on the 3.10 floor
    import tomli as tomllib

ROOT = Path(__file__).resolve().parent.parent

# (package, last affected release, first fixed release, advisories)
FLOORS = (
    ("cryptography", "49.0.2", "50.0.0", "GHSA-g6cj-pr64-35w5"),
    ("cryptography", "48.0.1", "50.0.0", "GHSA-jwv3-5hgf-82ww"),
    ("starlette", "1.3.0", "1.3.1", "GHSA-82w8-qh3p-5jfq"),
    ("h11", "0.15.0", "0.16.0", "GHSA-vqfr-h8mv-ghfj"),
    ("anyio", "4.14.1", "4.14.2", "GHSA-82r6-8w77-94w6"),
    ("fastapi", "0.109.0", "0.109.1", "PYSEC-2024-38"),
    ("pydantic", "2.3.0", "2.4.0", "GHSA-mr82-8j83-vxmv"),
    ("pydantic", "1.10.12", "2.4.0", "GHSA-mr82-8j83-vxmv"),
    ("idna", "3.14", "3.15", "GHSA-65pc-fj4g-8rjx"),
    ("python-dotenv", "1.2.1", "1.2.2", "GHSA-mf9w-mj56-hr94"),
    ("pyyaml", "5.3.1", "5.4", "GHSA-8q59-q68h-6hv4"),
    ("certifi", "2024.6.2", "2026.10.19", "GHSA-248v-346w-9cwc"),
    ("certifi", "2026.6.17", "2026.10.19", "GHSA-6q48-6c7w-9gw2"),
    ("lxml", "6.0.2", "6.1.0", "GHSA-vfmq-68hx-4jfw"),
)
# certifi is calendar-versioned and has to stay current, so a ceiling
# would only stop the root store from updating.
UNBOUNDED_BY_DESIGN = frozenset({"certifi"})


def _declared() -> dict[str, SpecifierSet]:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        deps = tomllib.load(handle)["tool"]["poetry"]["dependencies"]
    declared: dict[str, SpecifierSet] = {}
    for name, value in deps.items():
        if name == "python":
            continue
        raw = value["version"] if isinstance(value, dict) else value
        if raw[0].isdigit():
            raw = f"=={raw}"
        declared[canonicalize_name(name)] = SpecifierSet(raw)
    return declared


@pytest.mark.parametrize(("name", "affected", "fixed", "advisory"), FLOORS)
def test_no_affected_release_resolves(
    name: str, affected: str, fixed: str, advisory: str
) -> None:
    """The range is declared, excludes the affected release, keeps the fix."""
    spec = _declared().get(name)
    assert spec is not None, f"{name} has no floor for {advisory}"
    assert affected not in spec, f"{name} {spec} admits {affected}"
    assert fixed in spec, f"{name} {spec} excludes the fix {fixed}"


def test_every_runtime_range_has_an_upper_bound() -> None:
    """docs/POLICIES.md and the README promise bounded runtime ranges."""
    unbounded = sorted(
        name
        for name, spec in _declared().items()
        if name not in UNBOUNDED_BY_DESIGN
        and not any(s.operator in ("<", "<=", "==", "~=") for s in spec)
    )
    assert unbounded == []
