"""The suite policy that ``camt053.suite`` declares.

The camt053 suite ships one version number across every package. These
tests pin the declaration itself; the check that holds the published
packages to it is ``scripts/check_suite_consistency.py``, tested in
``tests/test_check_suite_consistency.py``.
"""

from __future__ import annotations

import pytest

from camt053.suite import CORE, SUITE, members, members_by_role


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
