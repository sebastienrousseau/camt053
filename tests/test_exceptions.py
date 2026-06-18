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
    ConfigurationError,
    DataSourceError,
    InvalidBICError,
    InvalidIBANError,
    InvalidLEIError,
    MissingRequiredFieldError,
    ReversalGenerationError,
    SchemaValidationError,
    StatementParseError,
    XMLGenerationError,
    XSDValidationError,
)

_ALL_EXCEPTIONS = [
    Camt053Error,
    AccountValidationError,
    XMLGenerationError,
    ConfigurationError,
    DataSourceError,
    SchemaValidationError,
    InvalidIBANError,
    InvalidBICError,
    InvalidLEIError,
    MissingRequiredFieldError,
    StatementParseError,
    ReversalGenerationError,
]


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


def test_every_exception_exposes_a_code():
    """Each exception class exposes a non-empty, upper-snake ``code`` (#30)."""
    for exc_type in _ALL_EXCEPTIONS:
        code = exc_type.code
        assert isinstance(code, str)
        assert code
        assert code == code.upper()


def test_error_codes_are_unique():
    """No two exception classes share an error code (#30)."""
    codes = [exc_type.code for exc_type in _ALL_EXCEPTIONS]
    assert len(codes) == len(set(codes))


def test_known_error_codes_are_stable():
    """The documented codes match the class-level constants (#30)."""
    assert Camt053Error.code == "CAMT053_ERROR"
    assert StatementParseError.code == "STATEMENT_PARSE_ERROR"
    assert ReversalGenerationError.code == "REVERSAL_GENERATION_ERROR"
    assert SchemaValidationError.code == "SCHEMA_VALIDATION_ERROR"
    # The XSD alias inherits the schema-validation code.
    assert XSDValidationError.code == "SCHEMA_VALIDATION_ERROR"
    # Instances inherit the class-level code.
    assert StatementParseError("bad").code == "STATEMENT_PARSE_ERROR"
    assert InvalidIBANError("bad", iban="XX").code == "INVALID_IBAN_ERROR"
