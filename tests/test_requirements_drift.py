"""The hash-pinned requirement sets agree with what the package declares.

``requirements/docs.txt`` and ``requirements/fuzz.txt`` pin camt053's
own runtime dependencies so the docs build and the ClusterFuzzLite build
can import the package without an unpinnable ``pip install .``. Those
pins are written by hand in the ``.in`` files, so nothing stops them
falling behind ``pyproject.toml``: when the package moved to xmlschema 4
(#159), both sets stayed on xmlschema 3.4.5, and the fuzzer and the API
docs ran against a version the package no longer supports.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import Version

ROOT = Path(__file__).resolve().parent.parent
PINNED = ("docs.txt", "fuzz.txt")
_PIN = re.compile(r"^([A-Za-z0-9._-]+)==([^\s\\;]+)", re.MULTILINE)


def _runtime_constraints() -> dict[str, SpecifierSet]:
    """Every runtime dependency's range, as a PEP 440 specifier set."""
    with (ROOT / "pyproject.toml").open("rb") as handle:
        deps = tomllib.load(handle)["tool"]["poetry"]["dependencies"]
    constraints: dict[str, SpecifierSet] = {}
    for name, value in deps.items():
        if name == "python":
            continue
        raw = value["version"] if isinstance(value, dict) else value
        if raw[0].isdigit():
            raw = f"=={raw}"
        constraints[canonicalize_name(name)] = SpecifierSet(raw)
    return constraints


def _pins(filename: str) -> dict[str, Version]:
    text = (ROOT / "requirements" / filename).read_text(encoding="utf-8")
    return {
        canonicalize_name(name): Version(version)
        for name, version in _PIN.findall(text)
    }


@pytest.mark.parametrize("filename", PINNED)
def test_pins_satisfy_the_runtime_ranges(filename: str) -> None:
    """A pinned runtime dependency lies inside the declared range."""
    constraints = _runtime_constraints()
    outside = {
        name: f"{version} not in {constraints[name]}"
        for name, version in _pins(filename).items()
        if name in constraints and version not in constraints[name]
    }
    assert outside == {}, f"requirements/{filename}: {outside}"


def test_exact_poetry_pins_become_equality() -> None:
    """A bare Poetry version such as ``0.7.1`` means ``==0.7.1``."""
    assert str(_runtime_constraints()["defusedxml"]) == "==0.7.1"
