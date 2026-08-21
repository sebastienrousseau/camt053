#!/usr/bin/env python3
"""Check that the published camt053 suite agrees with its own policy.

The suite ships one version number across every package. That is easy to
state and easy to let slip, because nothing breaks when it does: a
satellite left a release behind still installs, still imports, still
passes its own tests. It just quietly means something different from
what it says.

Two failures this catches, both of which had already happened when it
was written:

* **A member left behind.** `camt053-mcp` and `camt053-lsp` carried
  0.0.15 on `main` while PyPI still had 0.0.14, and the three loaders
  and the writer were at 0.0.14 against a 0.0.15 core.
* **A floor nobody revisited.** Every satellite declared
  `camt053>=0.0.6` while the core was at 0.0.15 — resolvable, so nothing
  complained, and nine releases of drift accumulated behind it.

Exits non-zero when the suite disagrees with itself, so a schedule turns
into a notification rather than a report nobody opens.

Usage:
    python3 scripts/check_suite_consistency.py
    python3 scripts/check_suite_consistency.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any

# Imported at module scope on purpose. An earlier draft imported this
# inside core_floor() behind `except ImportError: return None`, which
# meant a missing `packaging` silently disabled the floor rule: the
# checker still ran, still printed a report, and simply never mentioned
# floors again. A check that quietly stops checking is worse than one
# that refuses to start.
from packaging.requirements import Requirement

from camt053.suite import CORE, SUITE

PYPI = "https://pypi.org/pypi/{dist}/json"
TIMEOUT = 15


def fetch_metadata(distribution: str) -> dict[str, Any] | None:
    """Return the PyPI metadata for ``distribution``, or None if absent.

    Args:
        distribution: The distribution name on PyPI.

    Returns:
        The parsed ``info`` block, or ``None`` when the package is not
        published or PyPI cannot be reached.
    """
    try:
        with urllib.request.urlopen(  # noqa: S310 - fixed https host
            PYPI.format(dist=distribution), timeout=TIMEOUT
        ) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
    info = payload.get("info") or {}
    return {
        "version": info.get("version"),
        "requires_dist": info.get("requires_dist") or [],
    }


def core_floor(requires_dist: list[str]) -> str | None:
    """Extract the declared minimum ``camt053`` version, if any.

    Args:
        requires_dist: The ``requires_dist`` list from PyPI metadata.

    Returns:
        The floor as a string, or ``None`` when the package does not
        depend on the core or declares no lower bound.
    """
    for raw in requires_dist:
        try:
            requirement = Requirement(raw)
        except Exception:  # noqa: BLE001 - malformed entries are skipped
            continue
        if requirement.name != CORE:
            continue
        for spec in requirement.specifier:
            if spec.operator in (">=", "==", "~="):
                return str(spec.version)
    return None


def _as_tuple(version: str) -> tuple[int, ...]:
    """Convert a version string to a comparable tuple.

    Stops at the first non-numeric component so pre-release suffixes do
    not corrupt the comparison: ``0.0.16rc1`` becomes ``(0, 0)`` rather
    than ``(0, 0, 161)``.

    Args:
        version: A version string.

    Returns:
        A tuple of the leading numeric components.
    """
    parts: list[int] = []
    for chunk in version.split("."):
        digits = ""
        for char in chunk:
            if not char.isdigit():
                break
            digits += char
        if not digits:
            break
        parts.append(int(digits))
        if digits != chunk:
            break
    return tuple(parts)


def audit() -> tuple[list[str], dict[str, Any]]:
    """Compare every published member against the suite policy.

    Returns:
        A ``(problems, report)`` pair. ``problems`` is empty when the
        suite is consistent.
    """
    problems: list[str] = []
    report: dict[str, Any] = {"core": None, "members": {}}

    core_info = fetch_metadata(CORE)
    if core_info is None or not core_info["version"]:
        return ([f"{CORE} is not published"], report)
    core_version = core_info["version"]
    report["core"] = core_version

    for member in SUITE.values():
        info = fetch_metadata(member.distribution)
        if info is None or not info["version"]:
            problems.append(f"{member.distribution} is not published")
            report["members"][member.distribution] = {"published": None}
            continue

        version = info["version"]
        floor = core_floor(info["requires_dist"])
        report["members"][member.distribution] = {
            "published": version,
            "role": member.role,
            "core_floor": floor,
        }

        if version != core_version:
            problems.append(
                f"{member.distribution} is {version}, but every suite "
                f"member must match the core ({core_version}). Release it."
            )

        # The floor must also be reachable. A member requiring a core
        # that was never published is uninstallable no matter how well
        # its own version matches.
        if floor and _as_tuple(floor) > _as_tuple(core_version):
            problems.append(
                f"{member.distribution} requires {CORE}>={floor}, but the "
                f"newest published {CORE} is {core_version}. Nobody can "
                f"install this combination."
            )

    return problems, report


def main(argv: list[str] | None = None) -> int:
    """Run the audit and report.

    Args:
        argv: Command-line arguments, for testing.

    Returns:
        ``0`` when the suite is consistent, ``1`` otherwise.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    args = parser.parse_args(argv)

    problems, report = audit()

    if args.json:
        # JSON only. Appending prose makes the output unparseable for
        # the thing that consumes it.
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1 if problems else 0

    print(f"core: {CORE} {report['core']}")
    for name, data in sorted(report["members"].items()):
        published = data.get("published") or "unpublished"
        floor = data.get("core_floor")
        role = data.get("role", "")
        suffix = f"  (needs {CORE}>={floor})" if floor else ""
        print(f"  {name:<26} {published:<10} {role:<8}{suffix}")

    if problems:
        print("\nSuite is inconsistent:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print("\nSuite is consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
