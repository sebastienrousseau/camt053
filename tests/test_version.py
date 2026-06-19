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

"""Drift guard: pyproject version must match the in-code version strings.

The packaged 0.0.2 shipped with ``pyproject.toml`` at ``0.0.2`` while the
in-code strings stayed at ``0.0.1``, so ``camt053.__version__`` and
``camt053 --version`` under-reported the version. This test fails if those
sources ever drift apart again.

It parses ``pyproject.toml`` with a regex on the raw text rather than
``tomllib`` because Python 3.10 (part of the CI matrix) does not ship
``tomllib``.
"""

import re
from pathlib import Path

import camt053
from camt053.constants import VERSION

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"

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
