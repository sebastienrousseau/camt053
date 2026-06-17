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

"""ISO 20022 external return reason codes.

A thin helper over the ``return_reason_names`` table in
:mod:`camt053.constants`. Used to classify statement entries and to describe a
reason code in human-readable terms when building a reversing entry.

Example:
    >>> from camt053.parse.reason_codes import describe_reason, is_known_reason
    >>> describe_reason("AC04")
    'Closed Account Number'
    >>> is_known_reason("ac04")
    True
"""

from camt053.constants import return_reason_names

__all__ = ["describe_reason", "is_known_reason", "list_reason_codes"]


def describe_reason(code: str) -> str:
    """Return the human-readable name for a return reason code.

    Args:
        code: An ISO external return reason code (case-insensitive).

    Returns:
        The reason name, or ``"Unknown reason code"`` if unrecognised.
    """
    return return_reason_names.get((code or "").upper(), "Unknown reason code")


def is_known_reason(code: str) -> bool:
    """Return ``True`` if ``code`` is a recognised return reason code."""
    return (code or "").upper() in return_reason_names


def list_reason_codes() -> list[dict[str, str]]:
    """Return every known reason code with its name.

    Returns:
        A list of ``{"code": ..., "name": ...}`` dictionaries.
    """
    return [
        {"code": code, "name": name}
        for code, name in return_reason_names.items()
    ]
