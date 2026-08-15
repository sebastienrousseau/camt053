# Copyright (C) 2023-2026 Sebastien Rousseau.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Drift guards: the version must agree everywhere it is written down.

The packaged 0.0.2 shipped with ``pyproject.toml`` at ``0.0.2`` while the
in-code strings stayed at ``0.0.1``, so ``camt053.__version__`` and
``camt053 --version`` under-reported the version. This test fails if those
sources ever drift apart again.

It parses ``pyproject.toml`` with a regex on the raw text rather than
``tomllib`` because Python 3.10 (part of the CI matrix) does not ship
``tomllib``.

The CHANGELOG guard was added after 0.0.14 and 0.0.15 both shipped
without an entry: the file jumped straight from 0.0.13 to the previous
release, so the published history silently omitted two versions. A
release with no changelog entry is not a release anyone can read.
"""

import re
from pathlib import Path

import camt053
from camt053.constants import VERSION

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"

_VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)


def _pyproject_version() -> str:
    """Extract the project version from ``pyproject.toml`` via regex."""
    text = PYPROJECT.read_text(encoding="utf-8")
    match = _VERSION_RE.search(text)
    assert match is not None, "version not found in pyproject.toml"
    return match.group(1)


def test_versions_are_consistent():
    """pyproject, ``__version__``, and ``constants.VERSION`` must all agree."""
    pyproject_version = _pyproject_version()
    assert camt053.__version__ == pyproject_version
    assert VERSION == pyproject_version


def test_changelog_documents_the_current_version():
    """The version being shipped must have a CHANGELOG entry.

    Guards the release, not the code: it is easy to bump ``pyproject``
    and forget the changelog, and the omission is invisible until
    someone goes looking for what changed.
    """
    version = _pyproject_version()
    text = CHANGELOG.read_text(encoding="utf-8")
    heading = f"## [{version}]"
    assert heading in text, (
        f"CHANGELOG.md has no `{heading}` section. Every released "
        f"version needs an entry — add one before tagging {version}."
    )


def test_changelog_entries_are_ordered_newest_first():
    """The current version must be the first entry in the file.

    Catches an entry appended in the wrong place, which reads as though
    an older release were the latest.
    """
    version = _pyproject_version()
    text = CHANGELOG.read_text(encoding="utf-8")
    headings = re.findall(r"^## \[([^\]]+)\]", text, re.MULTILINE)
    assert headings, "CHANGELOG.md has no version headings"
    assert headings[0] == version, (
        f"first CHANGELOG entry is [{headings[0]}] but the project is at "
        f"{version}; the newest release must come first"
    )
