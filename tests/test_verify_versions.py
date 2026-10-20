# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""Every restatement of the version agrees with pyproject.toml."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "verify_versions", ROOT / "scripts" / "verify_versions.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def tree(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """A minimal checkout at 1.2.3 in ``tmp_path``, with the script on it."""
    module = _load()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    (tmp_path / "pkg").mkdir()
    files = {
        "pyproject.toml": 'version = "1.2.3"\n',
        "pkg/__init__.py": '__version__ = "1.2.3"\n',
        "CHANGELOG.md": "## [1.2.3] - 2026-10-20\n",
        "CITATION.cff": 'version: "1.2.3"\n',
        "README.md": "> **Latest release: v1.2.3**: notes\n",
    }
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    return module, tmp_path


def test_the_repository_agrees_with_itself(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert _load().main() == 0
    assert "OK: every source agrees" in capsys.readouterr().out


def test_a_consistent_tree_passes(tree) -> None:
    module, _ = tree
    assert module.main() == 0


@pytest.mark.parametrize(
    ("name", "text", "error"),
    [
        ("pkg/__init__.py", '__version__ = "1.2.2"\n', "__version__"),
        ("CHANGELOG.md", "## [1.2.2] - 2026-10-01\n", "CHANGELOG.md"),
        ("CITATION.cff", 'version: "1.2.2"\n', "CITATION.cff"),
        ("README.md", "**Latest release: v0.0.5**\n", "README latest"),
        ("constants.py", 'VERSION = "1.2.2"\n', "constants.VERSION"),
        ("glama.json", '{"version": "1.2.2"}', "glama.json"),
        ("server.json", '{"version": "1.2.3", "packages": [{}]}', "server"),
    ],
    ids=[
        "dunder",
        "changelog",
        "citation",
        "readme",
        "constants",
        "glama",
        "server",
    ],
)
def test_each_restatement_is_checked(
    tree, capsys: pytest.CaptureFixture[str], name: str, text: str, error: str
) -> None:
    module, root = tree
    if name == "constants.py":
        name = "camt053/constants.py"
        (root / "camt053").mkdir()
    (root / name).write_text(text, encoding="utf-8")
    assert module.main() == 1
    assert error in capsys.readouterr().out


def test_a_missing_version_field_stops_the_check(tree) -> None:
    module, root = tree
    (root / "pyproject.toml").write_text("[tool]\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        module.main()
