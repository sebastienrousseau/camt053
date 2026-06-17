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

"""LEI (Legal Entity Identifier) validator.

This module implements ISO 17442 format validation and ISO 7064
mod-97-10 checksum validation for LEIs. It validates both format and
checksum integrity before XML generation, significantly reducing
account-management message rejection rates.

Example:
    >>> from camt053.validation.lei_validator import validate_lei
    >>>
    >>> # Valid LEI
    >>> is_valid, error = validate_lei("5493001KJTIIGC8Y1R12")
    >>> assert is_valid
    >>>
    >>> # Invalid checksum
    >>> is_valid, error = validate_lei("5493001KJTIIGC8Y1R99")
    >>> assert not is_valid
    >>> assert "checksum" in error.lower()

Standards:
    - ISO 17442:2020 - Legal Entity Identifier (LEI)
    - ISO 7064 - Check digit mod-97-10 algorithm
"""

from camt053.exceptions import InvalidLEIError

# ISO 17442 LEI length (18 alphanumeric identifier + 2 check digits)
LEI_LENGTH = 20


def validate_lei_format(
    lei: str,
) -> tuple[bool, str]:
    """Validate LEI format structure.

    Checks:
    - Exactly 20 characters (ISO 17442)
    - First 18 characters are alphanumeric (A-Z or 0-9)
    - Last 2 characters are digits (check digits)

    Args:
        lei: LEI string to validate (with or without spaces).

    Returns:
        Tuple of (is_valid, error_message).

    Example:
        >>> is_valid, error = validate_lei_format("5493001KJTIIGC8Y1R12")
        >>> assert is_valid
    """
    if not lei:
        return False, "LEI cannot be empty"

    # Remove spaces for validation
    lei_clean = lei.replace(" ", "").replace("-", "").upper()
    lei_len = len(lei_clean)

    # Check length (must be exactly 20)
    if lei_len != LEI_LENGTH:
        return (
            False,
            f"LEI length must be {LEI_LENGTH} characters (got {lei_len})",
        )

    # Check all format requirements together
    identifier_ok = lei_clean[:18].isalnum()
    checkdigit_ok = lei_clean[18:20].isdigit()

    if not (identifier_ok and checkdigit_ok):
        errors = []
        if not identifier_ok:
            errors.append(
                "first 18 characters must be alphanumeric (A-Z, 0-9)"
            )
        if not checkdigit_ok:
            errors.append("characters 19-20 must be check digits (00-99)")
        return False, f"LEI format invalid: {'; '.join(errors)}"

    return True, ""


def validate_lei_checksum(lei: str) -> tuple[bool, str]:
    """Validate LEI checksum using ISO 7064 mod-97-10 algorithm.

    Algorithm:
    1. Take the full 20-character LEI (no rearrangement; the 2 check
       digits already occupy the final positions).
    2. Replace letters with numbers (A=10, B=11, ..., Z=35)
    3. Calculate mod 97 of resulting number
    4. Valid LEI has mod 97 = 1

    Args:
        lei: LEI string to validate (with or without spaces).

    Returns:
        Tuple of (is_valid, error_message).

    Example:
        >>> is_valid, error = validate_lei_checksum("5493001KJTIIGC8Y1R12")
        >>> assert is_valid
    """
    # Remove spaces
    lei_clean = lei.replace(" ", "").replace("-", "").upper()

    # Replace letters with numbers (A=10, B=11, ..., Z=35)
    numeric_lei = ""
    for char in lei_clean:
        if char.isdigit():
            numeric_lei += char
        elif char.isalpha():
            # A=10, B=11, ..., Z=35
            numeric_lei += str(ord(char) - ord("A") + 10)
        else:
            return False, f"Invalid character in LEI: {char}"

    # Calculate mod 97
    try:
        remainder = int(numeric_lei) % 97
    except ValueError as e:  # pragma: no cover
        return False, f"Invalid numeric LEI representation: {e}"

    if remainder != 1:
        return (
            False,
            f"LEI checksum validation failed (mod 97 = {remainder}, expected 1)",
        )

    return True, ""


def validate_lei(
    lei: str, field: str | None = None, strict: bool = True
) -> tuple[bool, str]:
    """Validate LEI format and checksum.

    This is the main entry point for LEI validation. It performs both
    format validation and ISO 7064 mod-97-10 checksum verification.

    Args:
        lei: LEI string to validate.
        field: Optional field name for error reporting.
        strict: If True, raise InvalidLEIError on failure. If False, return tuple.

    Returns:
        Tuple of (is_valid, error_message). If strict=True and invalid, raises exception.

    Raises:
        InvalidLEIError: If strict=True and LEI is invalid.

    Example:
        >>> # Non-strict mode (returns tuple)
        >>> is_valid, error = validate_lei("5493001KJTIIGC8Y1R12", strict=False)
        >>> assert is_valid
        >>>
        >>> # Strict mode (raises exception on error)
        >>> try:
        ...     validate_lei("5493001KJTIIGC8Y1R99", field="account_owner_lei")
        ... except InvalidLEIError as e:
        ...     print(f"Invalid: {e}")
    """
    # Format validation
    is_valid, error = validate_lei_format(lei)
    if not is_valid:
        if strict:
            raise InvalidLEIError(
                message=error,
                lei=lei,
                field=field,
                reason="Invalid LEI format",
            )
        return False, error

    # Checksum validation
    is_valid, error = validate_lei_checksum(lei)
    if not is_valid:
        if strict:
            raise InvalidLEIError(
                message=error,
                lei=lei,
                field=field,
                reason="Invalid LEI checksum (ISO 7064 mod-97-10)",
            )
        return False, error

    return True, ""


def validate_lei_safe(lei: str, field: str | None = None) -> bool:
    """Validate LEI and return True/False (never raises exceptions).

    This is a convenience wrapper for validate_lei with strict=False.
    Useful when you only need a boolean result without error details.

    Args:
        lei: LEI string to validate.
        field: Optional field name (unused, for API compatibility).

    Returns:
        True if LEI is valid, False otherwise.

    Example:
        >>> if validate_lei_safe("5493001KJTIIGC8Y1R12"):
        ...     print("Valid LEI")
    """
    is_valid, _ = validate_lei(lei, field=field, strict=False)
    return is_valid
