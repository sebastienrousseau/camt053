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

"""Tests for path-validation security helpers."""

from pathlib import Path

import pytest

from camt053.security import sanitize_for_log, validate_path
from camt053.security.path_validator import (
    PathValidationError,
    SecurityError,
    _is_allowed_directory,
)


def test_validate_path_in_cwd(tmp_path, monkeypatch):
    """A path inside the working directory validates."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "ok.xml"
    target.write_text("x")
    assert validate_path(str(target)).endswith("ok.xml")


def test_validate_path_traversal_rejected():
    """A traversal sequence is rejected."""
    with pytest.raises(PathValidationError):
        validate_path("../../etc/passwd")


def test_validate_path_empty_rejected():
    """An empty path is rejected."""
    with pytest.raises(PathValidationError):
        validate_path("")


def test_validate_path_outside_base(tmp_path):
    """A path outside an explicit base directory is rejected."""
    with pytest.raises(SecurityError):
        validate_path("/etc/hosts", base_dir=str(tmp_path))


def test_must_exist(tmp_path, monkeypatch):
    """``must_exist`` enforces presence."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        validate_path(str(tmp_path / "ghost.xml"), must_exist=True)


def test_validate_path_outside_allowed_no_base():
    """With no base dir, a path outside the allowed roots is rejected."""
    with pytest.raises(SecurityError):
        validate_path("/etc/hosts")


def test_is_allowed_directory():
    """The pathlib allow-list helper accepts cwd and rejects /etc."""
    assert _is_allowed_directory(Path.cwd()) is True
    assert _is_allowed_directory(Path("/etc")) is False


def test_sanitize_for_log():
    """Log sanitisation strips control characters and truncates."""
    assert sanitize_for_log("a\nb\rc") == "abc"
    assert sanitize_for_log("") == ""
    assert sanitize_for_log("x" * 200).endswith("...")
