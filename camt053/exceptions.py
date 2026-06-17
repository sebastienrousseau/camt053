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

"""Custom exception hierarchy for Camt053.

This module provides granular exception types to enable precise error handling
in banking integrations. Instead of catching generic ValueError or TypeError,
consuming applications can distinguish between data validation errors,
configuration errors, and XML generation failures.

Example:
    >>> try:
    ...     process_files(...)
    ... except AccountValidationError as e:
    ...     # Handle invalid IBAN/BIC/LEI - notify user
    ...     log.error(f"Account data invalid: {e}")
    ... except XMLGenerationError as e:
    ...     # Handle XML generation failure - check templates
    ...     log.error(f"XML generation failed: {e}")
    ... except ConfigurationError as e:
    ...     # Handle config issues - check setup
    ...     log.error(f"Configuration error: {e}")
"""


__all__ = [
    "Camt053Error",
    "AccountValidationError",
    "XMLGenerationError",
    "ConfigurationError",
    "DataSourceError",
    "SchemaValidationError",
    "XSDValidationError",
    "InvalidIBANError",
    "InvalidBICError",
    "InvalidLEIError",
    "MissingRequiredFieldError",
    "StatementParseError",
    "ReversalGenerationError",
]


class Camt053Error(Exception):
    """Base exception for all Camt053 errors.

    All custom exceptions in this library inherit from this base class,
    allowing consumers to catch any Camt053-specific error with a single
    except clause if needed.

    Example:
        >>> try:
        ...     process_files(...)
        ... except Camt053Error:
        ...     # Catch any Camt053-specific error
        ...     log.error("Camt053 operation failed")
    """


class AccountValidationError(Camt053Error):
    """Raised when account data validation fails.

    This exception indicates issues with input data such as:
    - Invalid IBAN format
    - Invalid BIC/SWIFT code
    - Invalid LEI (Legal Entity Identifier)
    - Missing required fields (account owner, account servicer, etc.)
    - Invalid date or currency formats

    Example:
        >>> try:
        ...     validate_account_data(data)
        ... except AccountValidationError as e:
        ...     # User-facing error - show validation message
        ...     return {"error": str(e), "field": e.field}
    """

    def __init__(self, message: str, field: str | None = None):
        """Initialize validation error with optional field name.

        Args:
            message: Human-readable error message.
            field: Optional field name that caused the validation error.
        """
        super().__init__(message)
        self.field = field


class XMLGenerationError(Camt053Error):
    """Raised when XML generation or validation fails.

    This exception indicates issues with:
    - Jinja2 template rendering failures
    - XSD schema validation errors
    - XML namespace issues
    - Missing or corrupted template files
    - Invalid XML structure

    Example:
        >>> try:
        ...     generate_xml(data, template, schema)
        ... except XMLGenerationError as e:
        ...     # System error - check templates and schemas
        ...     log.error(f"XML generation failed: {e}")
        ...     alert_ops_team()
    """


class ConfigurationError(Camt053Error):
    """Raised when configuration or setup is invalid.

    This exception indicates issues with:
    - Missing or invalid setup.cfg
    - Invalid CLI arguments
    - Missing required environment variables
    - Invalid file paths
    - Unsupported ISO 20022 version

    Example:
        >>> try:
        ...     load_config("acmt.001.001.99")
        ... except ConfigurationError as e:
        ...     # Config error - show usage help
        ...     print(f"Configuration error: {e}")
        ...     print_usage_help()
    """


class DataSourceError(Camt053Error):
    """Raised when data source access fails.

    This exception indicates issues with:
    - File not found (CSV, SQLite)
    - Database connection errors
    - Corrupted data files
    - Unsupported file formats
    - Empty data sources

    Example:
        >>> try:
        ...     load_account_data("accounts.csv")
        ... except DataSourceError as e:
        ...     # Data access error - check file exists
        ...     log.error(f"Cannot access data source: {e}")
    """


class SchemaValidationError(Camt053Error):
    """Raised when XSD schema validation fails.

    This exception indicates issues with:
    - Generated XML does not conform to ISO 20022 schema
    - Missing required XML elements
    - Invalid XML element values
    - Namespace mismatches

    Example:
        >>> try:
        ...     validate_xml_against_schema(xml, xsd)
        ... except SchemaValidationError as e:
        ...     # Schema validation error - check data mapping
        ...     log.error(f"XML schema validation failed: {e}")
        ...     log.debug(f"Validation errors: {e.errors}")
    """

    def __init__(self, message: str, errors: list[str] | None = None):
        """Initialize schema validation error with optional error list.

        Args:
            message: Human-readable error message.
            errors: Optional list of detailed validation errors.
        """
        super().__init__(message)
        self.errors = errors or []


# Alias for backward compatibility and API clarity
XSDValidationError = SchemaValidationError


class InvalidIBANError(AccountValidationError):
    """Raised when IBAN validation fails.

    This exception indicates issues with:
    - Invalid IBAN format (wrong structure)
    - Failed ISO 7064 mod-97-10 checksum validation
    - Unsupported country code
    - IBAN length mismatch for country

    Example:
        >>> try:
        ...     validate_iban("AT68123456")  # Too short
        ... except InvalidIBANError as e:
        ...     # IBAN validation failed - prompt user to correct
        ...     print(f"Invalid IBAN: {e}")
        ...     print(f"Field: {e.field}, Value: {e.iban}")
    """

    def __init__(
        self,
        message: str,
        iban: str,
        field: str | None = None,
        reason: str | None = None,
    ):
        """Initialize IBAN validation error with IBAN value.

        Args:
            message: Human-readable error message.
            iban: The invalid IBAN value.
            field: Optional field name (e.g., "account_id").
            reason: Optional specific reason for failure.
        """
        super().__init__(message, field=field)
        self.iban = iban
        self.reason = reason


class InvalidBICError(AccountValidationError):
    """Raised when BIC/SWIFT validation fails.

    This exception indicates issues with:
    - Invalid BIC format (must be 8 or 11 characters)
    - Invalid BIC structure (ISO 9362)
    - Invalid country code in BIC
    - Invalid bank/branch code characters

    Example:
        >>> try:
        ...     validate_bic("INVALID123")
        ... except InvalidBICError as e:
        ...     # BIC validation failed - prompt user to correct
        ...     print(f"Invalid BIC: {e}")
        ...     print(f"Field: {e.field}, Value: {e.bic}")
    """

    def __init__(
        self,
        message: str,
        bic: str,
        field: str | None = None,
        reason: str | None = None,
    ):
        """Initialize BIC validation error with BIC value.

        Args:
            message: Human-readable error message.
            bic: The invalid BIC value.
            field: Optional field name (e.g., "account_servicer_bic").
            reason: Optional specific reason for failure.
        """
        super().__init__(message, field=field)
        self.bic = bic
        self.reason = reason


class InvalidLEIError(AccountValidationError):
    """Raised when LEI (Legal Entity Identifier) validation fails.

    This exception indicates issues with:
    - Invalid LEI format (must be 20 alphanumeric characters)
    - Failed ISO 17442 mod-97-10 checksum validation
    - Invalid structure (ISO 17442)

    Example:
        >>> try:
        ...     validate_lei("INVALIDLEI")
        ... except InvalidLEIError as e:
        ...     # LEI validation failed - prompt user to correct
        ...     print(f"Invalid LEI: {e}")
        ...     print(f"Field: {e.field}, Value: {e.lei}")
    """

    def __init__(
        self,
        message: str,
        lei: str,
        field: str | None = None,
        reason: str | None = None,
    ):
        """Initialize LEI validation error with LEI value.

        Args:
            message: Human-readable error message.
            lei: The invalid LEI value.
            field: Optional field name (e.g., "account_owner_lei").
            reason: Optional specific reason for failure.
        """
        super().__init__(message, field=field)
        self.lei = lei
        self.reason = reason


class MissingRequiredFieldError(AccountValidationError):
    """Raised when a required field is missing from account data.

    This exception indicates issues with:
    - Missing mandatory fields (account_owner_name, account_servicer_bic, etc.)
    - Empty/null values for required fields
    - Missing fields in CSV rows
    - Missing dictionary keys

    Example:
        >>> try:
        ...     validate_required_fields(data, ["account_owner_name", "msg_id"])
        ... except MissingRequiredFieldError as e:
        ...     # Required field missing - show user what's needed
        ...     print(f"Missing field: {e.field}")
        ...     print(f"Row: {e.row_number}, Expected fields: {e.required_fields}")
    """

    def __init__(
        self,
        message: str,
        field: str,
        row_number: int | None = None,
        required_fields: list[str] | None = None,
    ):
        """Initialize missing field error with field details.

        Args:
            message: Human-readable error message.
            field: The missing field name.
            row_number: Optional row/line number where field is missing.
            required_fields: Optional list of all required fields.
        """
        super().__init__(message, field=field)
        self.row_number = row_number
        self.required_fields = required_fields or []


class StatementParseError(Camt053Error):
    """Raised when an incoming camt.05x statement cannot be parsed.

    This exception indicates issues with:
    - Malformed or non-well-formed statement XML
    - A document whose root is not a recognised camt.05x message
    - Missing mandatory statement structure (group header, statement, entries)

    Example:
        >>> try:
        ...     parse_document(xml)
        ... except StatementParseError as e:
        ...     # Bad inbound file - quarantine and alert operations
        ...     log.error(f"Cannot parse statement: {e}")
    """

    def __init__(self, message: str, line: int | None = None):
        """Initialize statement parse error with optional source line.

        Args:
            message: Human-readable error message.
            line: Optional 1-based line number where parsing failed.
        """
        super().__init__(message)
        self.line = line


class ReversalGenerationError(XMLGenerationError):
    """Raised when a reversing entry cannot be generated.

    This exception indicates issues with:
    - No statement entries matched the requested return/reason code
    - A booked entry missing the fields required to reverse it
    - Rendering or XSD validation failure of the reversal document

    Example:
        >>> try:
        ...     generate_reversal(xml, reason_code="AC04")
        ... except ReversalGenerationError as e:
        ...     # Nothing to reverse, or reversal failed validation
        ...     log.error(f"Reversal generation failed: {e}")
    """
