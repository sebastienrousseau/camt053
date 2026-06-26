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

"""Profile for the CBPR+ ``camt.0{52,53,54}.001.08`` family.

``.001.08`` is the CBPR+ cross-border current set on the producer
side: Goldman Sachs, JPMorgan, Citi, BNP, Standard Chartered,
Deutsche Bank, BNY Mellon all emit it. It accepts **hybrid** postal
addresses (some structured fields, some `AdrLine`); the rules
tighten further on ``.001.13``. After the Nov 14-16 2026 cutover
*unstructured-only* postal addresses are rejected even on ``.08``.
"""

from __future__ import annotations

from typing import Any

from camt053.profiles._xml import (
    has_child,
    iter_descendants,
    parse_xml,
)
from camt053.profiles.base import (
    ProfileFinding,
    ProfileSeverity,
    SchemaProfile,
)


def _is_unstructured_only(pstl_adr: Any) -> bool:
    """Return ``True`` iff ``PstlAdr`` has only ``AdrLine`` children."""
    has_adr_line = has_child(pstl_adr, "AdrLine")
    has_structured = any(
        has_child(pstl_adr, tag)
        for tag in (
            "TwnNm",
            "Ctry",
            "StrtNm",
            "PstCd",
            "BldgNb",
            "BldgNm",
            "Flr",
            "Room",
            "PstBx",
            "Dept",
            "SubDept",
            "TwnLctnNm",
            "DstrctNm",
            "CtrySubDvsn",
        )
    )
    return has_adr_line and not has_structured


class Profile_v08(SchemaProfile):
    """Profile for any ``camt.0{52,53,54}.001.08`` payload."""

    version = "camt.053.001.08"
    classification = "current"

    def validate(self, xml: str) -> list[ProfileFinding]:
        """Surface the unstructured-postal-address warning."""
        root = parse_xml(xml)
        if root is None:
            return [
                ProfileFinding(
                    severity=ProfileSeverity.ERROR,
                    code="CAMT.PROFILE.PARSE_FAILED",
                    message="Payload could not be parsed.",
                )
            ]

        findings: list[ProfileFinding] = []
        for idx, pstl_adr in enumerate(iter_descendants(root, "PstlAdr")):
            if _is_unstructured_only(pstl_adr):
                findings.append(
                    ProfileFinding(
                        severity=ProfileSeverity.WARNING,
                        code="CAMT.CBPR.UNSTRUCTURED_ADDRESS",
                        message=(
                            "PstlAdr carries only AdrLine without "
                            "structured siblings (TwnNm + Ctry). This "
                            "is accepted on .001.08 today but rejected "
                            "by CBPR+ after the Nov 14-16 2026 cutover."
                        ),
                        element="PstlAdr",
                        location=f"PstlAdr[{idx}]",
                    )
                )
        return findings
