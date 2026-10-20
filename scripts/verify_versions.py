#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""Fail when the release version is restated differently anywhere.

Single source of truth: ``version`` in ``pyproject.toml``. The same string
must appear in the package's ``__version__`` (when the package defines
one), as a ``## [X.Y.Z]`` heading in ``CHANGELOG.md``, in ``glama.json``
(``version`` and the Docker tag of ``installation.docker`` when present),
in ``server.json`` (``version`` and every ``packages[].version``), and
in ``CITATION.cff`` (``version``). In the core it must also appear as
``VERSION`` in ``camt053/constants.py`` (what the CLI reports) and in
the README's "Latest release" line when it has one.

The Glama directory and the MCP registry read those two manifests; before
this check they sat several releases behind the package on every server
in the suite. Standard library only, so the workflow needs no install.

Usage: python3 scripts/verify_versions.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("pyproject.toml has no version field")
    return match.group(1)


def _package_version() -> str | None:
    for init in ROOT.glob("*/__init__.py"):
        if init.parent.name.startswith(
            (".", "_", "tests", "docs", "examples")
        ):
            continue
        match = re.search(
            r'^__version__\s*=\s*"([^"]+)"',
            init.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        if match:
            return match.group(1)
    return None


def _changelog_versions() -> set[str]:
    path = ROOT / "CHANGELOG.md"
    if not path.exists():
        return set()
    return set(
        re.findall(
            r"^## \[(\d+\.\d+\.\d+)\]",
            path.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    )


def _json(name: str) -> dict[str, Any] | None:
    path = ROOT / name
    return (
        json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    )


Check = tuple[list[str], list[str]]


def _check_package(expected: str) -> Check:
    pkg = _package_version()
    if pkg is None:
        return [], []
    line = f"  __version__            = {pkg}"
    ok = pkg == expected
    return [line], [] if ok else ["__version__ differs from pyproject.toml"]


def _check_changelog(expected: str) -> Check:
    changelog = _changelog_versions()
    if changelog and expected not in changelog:
        return [], [f"CHANGELOG.md has no [{expected}] heading"]
    return [], []


def _check_glama(expected: str) -> Check:
    glama = _json("glama.json")
    if glama is None:
        return [], []
    docker = str((glama.get("installation") or {}).get("docker", ""))
    tag = docker.rsplit(":", 1)[-1] if ":" in docker else expected
    line = (
        f"  glama.json             = {glama.get('version')} (docker tag {tag})"
    )
    ok = glama.get("version") == expected and tag == expected
    return [line], [] if ok else ["glama.json version or Docker tag differs"]


def _check_server(expected: str) -> Check:
    server = _json("server.json")
    if server is None:
        return [], []
    versions = [p.get("version") for p in server.get("packages", [])]
    line = f"  server.json            = {server.get('version')} (packages {versions})"
    ok = server.get("version") == expected and all(
        v == expected for v in versions
    )
    return [line], [] if ok else ["server.json version differs"]


def _check_citation(expected: str) -> Check:
    path = ROOT / "CITATION.cff"
    if not path.exists():
        return [], []
    match = re.search(
        r'^version:\s*"?([^"\s]+)"?\s*$',
        path.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    found = match.group(1) if match else None
    line = f"  CITATION.cff           = {found}"
    return [line], (
        [] if found == expected else ["CITATION.cff version differs"]
    )


def _check_constants(expected: str) -> Check:
    """``camt053/constants.py`` restates the version the CLI prints."""
    path = ROOT / "camt053" / "constants.py"
    if not path.exists():
        return [], []
    match = re.search(
        r'^VERSION\s*=\s*"([^"]+)"',
        path.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    found = match.group(1) if match else None
    line = f"  constants.VERSION      = {found}"
    return [line], ([] if found == expected else ["constants.VERSION differs"])


def _check_readme(expected: str) -> Check:
    """A "Latest release: vX.Y.Z" line in the README names this one."""
    path = ROOT / "README.md"
    if not path.exists():
        return [], []
    found = re.findall(
        r"Latest release: v(\d+\.\d+\.\d+)",
        path.read_text(encoding="utf-8"),
    )
    if not found:
        return [], []
    line = f"  README latest release  = {', '.join(found)}"
    ok = all(v == expected for v in found)
    return [line], [] if ok else ["README latest release differs"]


CHECKS = (
    _check_package,
    _check_constants,
    _check_readme,
    _check_changelog,
    _check_glama,
    _check_server,
    _check_citation,
)


def main() -> int:
    """Compare every restatement of the version and report."""
    expected = _pyproject_version()
    problems: list[str] = []
    print(f"  pyproject.toml version = {expected}")
    for check in CHECKS:
        lines, found = check(expected)
        for line in lines:
            print(line)
        problems.extend(found)
    for problem in problems:
        print(f"ERROR: {problem}")
    if problems:
        return 1
    print("OK: every source agrees on", expected)
    return 0


if __name__ == "__main__":
    sys.exit(main())
