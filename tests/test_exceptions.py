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

"""Tests for the custom exception hierarchy."""

from camt053.exceptions import (
    AccountValidationError,
    Camt053Error,
    InvalidIBANError,
    MissingRequiredFieldError,
    ReversalGenerationError,
    SchemaValidationError,
    StatementParseError,
    XMLGenerationError,
    XSDValidationError,
)


def test_base_hierarchy():
    """Specific errors inherit from the base error."""
    assert issubclass(StatementParseError, Camt053Error)
    assert issubclass(ReversalGenerationError, XMLGenerationError)
    assert issubclass(InvalidIBANError, AccountValidationError)
    assert XSDValidationError is SchemaValidationError


def test_statement_parse_error_line():
    """StatementParseError carries an optional source line."""
    err = StatementParseError("bad", line=12)
    assert err.line == 12
    assert str(err) == "bad"


def test_account_validation_error_field():
    """AccountValidationError carries an optional field name."""
    assert AccountValidationError("bad", field="account_id").field == (
        "account_id"
    )


def test_iban_error_attributes():
    """InvalidIBANError exposes the offending value and reason."""
    err = InvalidIBANError("bad", iban="XX00", field="f", reason="why")
    assert err.iban == "XX00"
    assert err.reason == "why"


def test_missing_required_field_error():
    """MissingRequiredFieldError tracks the field and row."""
    err = MissingRequiredFieldError("missing", field="x", row_number=3)
    assert err.field == "x"
    assert err.row_number == 3


def test_schema_validation_error_errors():
    """SchemaValidationError aggregates a list of detail errors."""
    err = SchemaValidationError("bad", errors=["a", "b"])
    assert err.errors == ["a", "b"]


def test_reversal_generation_error_is_catchable_as_base():
    """A ReversalGenerationError is catchable as the base error."""
    try:
        raise ReversalGenerationError("nothing to reverse")
    except Camt053Error as exc:
        assert "nothing to reverse" in str(exc)
