"""The suite policy, and the check that enforces it.

The camt053 suite ships one version number across every package. This
pins both halves: what `camt053.suite` declares, and what
`scripts/check_suite_consistency.py` does with it against PyPI.

Network access is stubbed throughout — a check that only works when
PyPI is reachable is not a check anyone can run.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

from camt053.suite import CORE, SUITE, members, members_by_role

_SPEC = importlib.util.spec_from_file_location(
    "check_suite_consistency",
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "check_suite_consistency.py",
)
assert _SPEC and _SPEC.loader
checker = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(checker)


def _member(version: str, floor: str | None = None) -> dict[str, Any]:
    """Build a stub PyPI metadata block."""
    requires = [f"{CORE}<1,>={floor}"] if floor else []
    return {"version": version, "requires_dist": requires}


def _stub(
    monkeypatch: pytest.MonkeyPatch, table: dict[str, dict[str, Any]]
) -> None:
    """Replace PyPI lookups with a fixed table."""
    monkeypatch.setattr(
        checker, "fetch_metadata", lambda dist: table.get(dist)
    )


class TestSuiteDeclaration:
    """What the suite says about itself."""

    def test_core_is_the_first_member(self) -> None:
        """The core sets the number every other member matches."""
        assert members()[0].distribution == CORE

    def test_members_covers_the_whole_suite(self) -> None:
        """There is no subset to pick: every member is lockstep."""
        assert len(members()) == len(SUITE)

    def test_every_satellite_is_present(self) -> None:
        """All six packages, including the writer."""
        names = {m.distribution for m in members()}
        assert names == {
            "camt053",
            "camt053-mcp",
            "camt053-lsp",
            "camt053-loader-mt940",
            "camt053-loader-mt942",
            "camt053-writer-xlsx",
        }

    def test_roles_describe_shape_not_versioning(self) -> None:
        """Roles are documentation; they carry no versioning meaning."""
        assert len(members_by_role("core")) == 1
        assert len(members_by_role("wrapper")) == 2
        assert len(members_by_role("loader")) == 2
        assert len(members_by_role("writer")) == 1

    def test_membership_table_is_read_only(self) -> None:
        """Reference data a check trusts must not be reshapable."""
        with pytest.raises(TypeError):
            SUITE["camt053-rogue"] = SUITE[CORE]  # type: ignore[index]


class TestFloorParsing:
    """Reading the declared camt053 floor out of PyPI metadata."""

    def test_it_reads_a_plain_lower_bound(self) -> None:
        """The shape every satellite actually publishes."""
        assert checker.core_floor(["camt053<1,>=0.0.6"]) == "0.0.6"

    def test_it_ignores_other_distributions(self) -> None:
        """A floor on a sibling is not a floor on the core."""
        assert checker.core_floor(["camt053-loader-mt940>=0.0.9"]) is None

    def test_it_survives_malformed_entries(self) -> None:
        """One unparseable requirement must not hide the rest."""
        assert (
            checker.core_floor(["not a requirement!!", "camt053>=0.0.9"])
            == "0.0.9"
        )

    def test_packaging_is_imported_at_module_scope(self) -> None:
        """A missing dependency must fail loudly, not disable a rule.

        An earlier draft imported `packaging` inside `core_floor` behind
        `except ImportError: return None`. With packaging absent the
        checker still ran, still printed a report, and simply never
        mentioned floors again — the rule was gone and nothing said so.
        """
        assert hasattr(checker, "Requirement")


class TestVersionTuples:
    """Comparing versions without tripping over pre-release suffixes."""

    def test_plain_versions_compare_numerically(self) -> None:
        """0.0.9 must sort below 0.0.15, not above it as a string would."""
        assert checker._as_tuple("0.0.9") < checker._as_tuple("0.0.15")

    def test_a_prerelease_suffix_does_not_inflate_the_number(self) -> None:
        """`0.0.16rc1` must not read as `(0, 0, 161)`."""
        assert checker._as_tuple("0.0.16rc1") == (0, 0, 16)


class TestAudit:
    """The check itself, against stubbed PyPI state."""

    def test_a_consistent_suite_reports_no_problems(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Every member on the core's number, floors reachable."""
        _stub(
            monkeypatch,
            {
                "camt053": _member("0.0.16"),
                "camt053-mcp": _member("0.0.16", "0.0.16"),
                "camt053-lsp": _member("0.0.16", "0.0.16"),
                "camt053-loader-mt940": _member("0.0.16", "0.0.16"),
                "camt053-loader-mt942": _member("0.0.16", "0.0.16"),
                "camt053-writer-xlsx": _member("0.0.16", "0.0.16"),
            },
        )

        problems, report = audit_result = checker.audit()

        assert problems == []
        assert report["core"] == "0.0.16"
        assert (
            audit_result[1]["members"]["camt053-writer-xlsx"]["published"]
            == "0.0.16"
        )

    def test_the_drift_that_actually_happened_is_reported(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Five satellites at 0.0.14 against a 0.0.15 core."""
        table = {"camt053": _member("0.0.15")}
        for name in SUITE:
            if name != CORE:
                table[name] = _member("0.0.14", "0.0.6")
        _stub(monkeypatch, table)

        problems, _ = checker.audit()

        assert len(problems) == 5
        assert all("must match the core (0.0.15)" in p for p in problems)

    def test_an_unreachable_floor_is_reported(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Requiring a core that was never published is uninstallable."""
        _stub(
            monkeypatch,
            {
                "camt053": _member("0.0.15"),
                "camt053-mcp": _member("0.0.15", "0.0.99"),
            },
        )

        problems, _ = checker.audit()

        assert any(
            "Nobody can install this combination" in p for p in problems
        )

    def test_an_unpublished_member_is_reported(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A member missing from PyPI is drift too."""
        _stub(monkeypatch, {"camt053": _member("0.0.15")})

        problems, _ = checker.audit()

        assert any("is not published" in p for p in problems)

    def test_an_unpublished_core_short_circuits(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without a core version there is nothing to compare against."""
        _stub(monkeypatch, {})

        problems, report = checker.audit()

        assert problems == [f"{CORE} is not published"]
        assert report["core"] is None


class TestMain:
    """Exit codes and output modes."""

    def test_it_exits_zero_when_consistent(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        """A clean suite is a silent success."""
        _stub(
            monkeypatch,
            {name: _member("0.0.16", "0.0.16") for name in SUITE},
        )

        assert checker.main([]) == 0
        assert "Suite is consistent." in capsys.readouterr().out

    def test_it_exits_nonzero_when_inconsistent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """So a schedule becomes a notification."""
        table = {name: _member("0.0.14", "0.0.6") for name in SUITE}
        table["camt053"] = _member("0.0.15")
        _stub(monkeypatch, table)

        assert checker.main([]) == 1

    def test_json_mode_emits_only_json(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        """Appending prose would make it unparseable for its consumer."""
        import json

        _stub(
            monkeypatch,
            {name: _member("0.0.16", "0.0.16") for name in SUITE},
        )

        checker.main(["--json"])

        parsed = json.loads(capsys.readouterr().out)
        assert parsed["core"] == "0.0.16"
        assert len(parsed["members"]) == len(SUITE)
