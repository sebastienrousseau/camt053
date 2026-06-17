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

"""XML rendering and validation for the camt053 library."""

from camt053.xml.generate_xml import (
    generate_reversal_for_statement,
    generate_reversal_xml,
    write_reversal_xml,
)
from camt053.xml.validate_via_xsd import (
    validate_via_xsd,
    validate_xml_string_via_xsd,
)

__all__ = [
    "generate_reversal_xml",
    "generate_reversal_for_statement",
    "write_reversal_xml",
    "validate_via_xsd",
    "validate_xml_string_via_xsd",
]
