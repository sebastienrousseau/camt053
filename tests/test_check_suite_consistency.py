# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""The scheduled suite check holds the camt053 suite to one version.

Every member ships the core's number, in the same release, so a member
published ahead of the core fails exactly like one left behind. This is
the core, so the tree is compared with ``camt053``'s own release. PyPI
is never reached; the published versions are substituted.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from camt053.suite import SUITE

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "check_suite_consistency.py"
)

MEMBERS = (
    "camt053",
    "camt053-lsp",
    "camt053-mcp",
    "camt053-loader-mt940",
    "camt053-loader-mt942",
    "camt053-writer-xlsx",
)


def _load():
    spec = importlib.util.spec_from_file_location("suite_check", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def module(monkeypatch):
    """The script as a module, with PyPI and the tree substituted."""
    loaded = _load()

    def use(tree: str, published: dict[str, str | None]):
        monkeypatch.setattr(loaded, "tree_version", lambda: tree)
        monkeypatch.setattr(loaded, "published_version", published.get)
        return loaded

    return use


@pytest.fixture
def script(module):
    """Run the check and return its problems."""
    return lambda tree, published: module(tree, published).check()[0]


def _suite(version: str, **members: str) -> dict[str, str | None]:
    versions: dict[str, str | None] = dict.fromkeys(MEMBERS, version)
    versions.update({k.replace("_", "-"): v for k, v in members.items()})
    return versions


def test_this_is_the_core():
    """In the core the checkout and ``MEMBERS[0]`` are one package."""
    loaded = _load()
    assert loaded.THIS == loaded.MEMBERS[0] == "camt053"


def test_members_match_the_suite_module():
    """The shared copy lists exactly what ``camt053.suite`` declares."""
    assert set(_load().MEMBERS) == set(SUITE)


def test_a_suite_on_one_version_is_clean(script):
    assert script("0.0.23", _suite("0.0.23")) == []


def test_a_member_ahead_of_the_core_fails(script):
    """The state main was in: camt053-mcp 0.0.22, every other member 0.0.20."""
    problems = script("0.0.20", _suite("0.0.20", camt053_mcp="0.0.22"))
    assert problems == [
        "camt053-mcp: published 0.0.22, but the suite is at 0.0.20"
    ]


def test_a_member_left_behind_fails(script):
    problems = script("0.0.23", _suite("0.0.23", camt053_lsp="0.0.20"))
    assert problems == [
        "camt053-lsp: published 0.0.20, but the suite is at 0.0.23"
    ]


def test_unreleased_bump_names_the_core(script):
    """A bump that never reached PyPI is reported against camt053."""
    problems = script("0.0.23", _suite("0.0.22"))
    assert problems == [
        "camt053: tree is 0.0.23 but PyPI has 0.0.22. Either the "
        "release was never tagged, or the tree is behind."
    ]


def test_unreadable_index_is_reported(script):
    """A member PyPI cannot answer for is a problem, never a pass."""
    versions = _suite("0.0.23")
    del versions["camt053-writer-xlsx"]
    assert script("0.0.23", versions) == [
        "camt053-writer-xlsx: could not read PyPI"
    ]


def test_main_exits_zero_and_says_so(module, monkeypatch, capsys):
    loaded = module("0.0.23", _suite("0.0.23"))
    monkeypatch.setattr("sys.argv", ["check"])
    assert loaded.main() == 0
    assert "the suite agrees with itself" in capsys.readouterr().out


def test_main_json_lists_problems(module, monkeypatch, capsys):
    loaded = module("0.0.23", _suite("0.0.23", camt053_lsp="0.0.20"))
    monkeypatch.setattr("sys.argv", ["check", "--json"])
    assert loaded.main() == 1
    report = json.loads(capsys.readouterr().out)
    assert report["published"]["camt053-lsp"] == "0.0.20"
    assert len(report["problems"]) == 1


def test_tree_version_reads_this_checkout():
    """Without substitution the tree version comes from pyproject."""
    import camt053

    assert _load().tree_version() == camt053.__version__
