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

"""Validation module for Camt053.

This module provides centralized validation for financial identifiers
(IBAN, BIC, LEI) and JSON Schema validation of flat reversing-entry records.
"""

from camt053.validation.bic_validator import (
    validate_bic,
    validate_bic_format,
    validate_bic_safe,
)
from camt053.validation.iban_validator import (
    validate_iban,
    validate_iban_checksum,
    validate_iban_format,
    validate_iban_safe,
)
from camt053.validation.lei_validator import (
    validate_lei,
    validate_lei_checksum,
    validate_lei_format,
    validate_lei_safe,
)
from camt053.validation.schema_validator import (
    SchemaValidator,
    ValidationError,
)

__all__ = [
    # Schema validation
    "SchemaValidator",
    "ValidationError",
    # IBAN validation
    "validate_iban",
    "validate_iban_format",
    "validate_iban_checksum",
    "validate_iban_safe",
    # BIC validation
    "validate_bic",
    "validate_bic_format",
    "validate_bic_safe",
    # LEI validation
    "validate_lei",
    "validate_lei_format",
    "validate_lei_checksum",
    "validate_lei_safe",
]
