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

"""Profile for the T2S MR2026 ``camt.0{52,53,54}.001.13`` family.

``.001.13`` is the T2S R2026.NOV / MR2026 target revision. The rules
are stricter than ``.001.08`` on the same payloads: postal addresses
MUST be structured (TownName + Country at minimum), and any reference
to deprecated identification fields is an error.
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


def _is_missing_country(pstl_adr: Any) -> bool:
    """Return ``True`` iff ``PstlAdr`` has any structured field but no ``Ctry``."""
    has_anything_structured = any(
        has_child(pstl_adr, tag)
        for tag in (
            "TwnNm",
            "StrtNm",
            "PstCd",
            "BldgNb",
            "BldgNm",
        )
    )
    return has_anything_structured and not has_child(pstl_adr, "Ctry")


class Profile_v13(SchemaProfile):
    """Profile for any ``camt.0{52,53,54}.001.13`` payload."""

    version = "camt.053.001.13"
    classification = "current"

    def validate(self, xml: str) -> list[ProfileFinding]:
        """Surface the strict-address + missing-country rules."""
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
                        severity=ProfileSeverity.ERROR,
                        code="CAMT.MR2026.UNSTRUCTURED_ADDRESS",
                        message=(
                            "PstlAdr carries only AdrLine without "
                            "structured siblings. .001.13 / T2S MR2026 "
                            "requires structured addresses (TwnNm + Ctry "
                            "at minimum)."
                        ),
                        element="PstlAdr",
                        location=f"PstlAdr[{idx}]",
                    )
                )
            elif _is_missing_country(pstl_adr):
                findings.append(
                    ProfileFinding(
                        severity=ProfileSeverity.ERROR,
                        code="CAMT.MR2026.MISSING_COUNTRY",
                        message=(
                            "PstlAdr is partly structured but missing "
                            "<Ctry>. .001.13 / T2S MR2026 requires "
                            "every structured PstlAdr to carry a Ctry."
                        ),
                        element="PstlAdr",
                        location=f"PstlAdr[{idx}]",
                    )
                )
        return findings
