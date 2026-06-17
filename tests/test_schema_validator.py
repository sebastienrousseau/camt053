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

"""Tests for the JSON Schema validator."""

import json

import pytest

from camt053.validation.schema_validator import (
    SchemaValidator,
    ValidationError,
)


def test_invalid_message_type_raises():
    """An unsupported message type is rejected (no path traversal)."""
    with pytest.raises(ValueError, match="Invalid message type"):
        SchemaValidator("../../etc/passwd")


def test_required_fields_present():
    """Required fields are read from the schema."""
    validator = SchemaValidator("camt.053.001.14")
    assert "reason_code" in validator.get_required_fields()


def test_validate_valid_record(reversal_record):
    """A valid record produces no validation errors."""
    validator = SchemaValidator("camt.053.001.14")
    assert validator.validate_data(reversal_record) == []


def test_validate_missing_required():
    """A missing required field produces an error."""
    validator = SchemaValidator("camt.053.001.14")
    errors = validator.validate_data({"statement_msg_id": "X"})
    assert errors
    assert isinstance(errors[0], ValidationError)


def test_validate_batch(reversal_record):
    """A batch reports per-row validity."""
    validator = SchemaValidator("camt.053.001.14")
    total, valid, errors = validator.validate_batch(
        [reversal_record, {"statement_msg_id": "X"}]
    )
    assert total == 2
    assert valid == 1
    assert len(errors) == 1


def test_field_schema_and_description():
    """Field schema and description accessors work."""
    validator = SchemaValidator("camt.053.001.14")
    field = validator.get_field_schema("reason_code")
    assert field["maxLength"] == 4
    assert (
        "return reason"
        in validator.get_field_description("reason_code").lower()
    )
    assert validator.get_field_schema("nope") is None
    assert validator.get_field_description("nope") is None


def test_validate_row(reversal_record):
    """``validate_row`` returns a (bool, errors) pair."""
    validator = SchemaValidator("camt.053.001.14")
    ok, errors = validator.validate_row(reversal_record)
    assert ok is True
    assert errors == []
    bad_ok, bad_errors = validator.validate_row({"statement_msg_id": "X"})
    assert bad_ok is False
    assert bad_errors


def test_validation_error_repr():
    """ValidationError has readable str/repr forms."""
    err = ValidationError("bad", "$.reason_code", "x", "required")
    assert "$.reason_code" in str(err)
    assert "required" in repr(err)


def test_custom_schema_dir_and_bad_json(tmp_path):
    """A schema dir with malformed JSON raises a JSONDecodeError."""
    schema_dir = tmp_path
    (schema_dir / "camt.053.001.14.schema.json").write_text("{not json")
    with pytest.raises(json.JSONDecodeError):
        SchemaValidator("camt.053.001.14", schema_dir=schema_dir)


def test_missing_schema_file_raises(tmp_path):
    """A supported type with no schema file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        SchemaValidator("camt.053.001.14", schema_dir=tmp_path / "empty")


def test_invalid_jsonschema_raises_valueerror(tmp_path):
    """Validating against a structurally invalid JSON Schema raises."""
    (tmp_path / "camt.053.001.14.schema.json").write_text(
        json.dumps({"type": "object", "properties": {"x": {"type": 123}}})
    )
    validator = SchemaValidator("camt.053.001.14", schema_dir=tmp_path)
    with pytest.raises(ValueError, match="Invalid schema"):
        validator.validate_data({"x": "y"})
