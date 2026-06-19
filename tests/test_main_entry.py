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

"""Tests for the module entry point."""

import subprocess
import sys


def test_module_runs_as_main():
    """``python -m camt053 --version`` runs the console entry point."""
    result = subprocess.run(
        [sys.executable, "-m", "camt053", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "0.0.3" in result.stdout


def test_main_callable():
    """The package exposes a callable CLI entry point."""
    import camt053.__main__ as entry

    assert callable(entry.main)
