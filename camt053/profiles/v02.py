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

"""Profile for the deprecated ``camt.05x.001.02`` family.

The ``.02`` family is the lingua franca of ERP consumers (SAP, Oracle,
Workday) and is still emitted in volume by legacy producers. It still
parses and validates today but **will be rejected by the major
clearing systems** after the 14-16 November 2026 CBPR+ cutover, so
this profile's job is to surface that one big "you must migrate"
warning, plus a stricter post-cutover error.

The profile is intentionally light: the ``.02`` schema is wide and
permissive; the differentiated rules belong on the ``.08`` / ``.13``
profiles.
"""

from __future__ import annotations

from datetime import datetime, timezone

from camt053.compliance.cbpr_readiness import CBPR_CUTOVER_DATE
from camt053.profiles._xml import parse_xml
from camt053.profiles.base import (
    ProfileFinding,
    ProfileSeverity,
    SchemaProfile,
)


class Profile_v02(SchemaProfile):
    """Profile for any ``camt.0{52,53,54}.001.02`` payload."""

    version = "camt.053.001.02"  # representative; v02 family covers .02-.07
    classification = "deprecated"

    def validate(self, xml: str) -> list[ProfileFinding]:
        """Surface the deprecation warning (and post-cutover error)."""
        if parse_xml(xml) is None:
            return [
                ProfileFinding(
                    severity=ProfileSeverity.ERROR,
                    code="CAMT.PROFILE.PARSE_FAILED",
                    message="Payload could not be parsed.",
                )
            ]

        findings: list[ProfileFinding] = [
            ProfileFinding(
                severity=ProfileSeverity.WARNING,
                code="CAMT.SCHEMA.DEPRECATED",
                message=(
                    "Schema revision is deprecated and will be rejected "
                    "by the major clearing systems after the CBPR+ Nov "
                    f"2026 cutover ({CBPR_CUTOVER_DATE}). Migrate to "
                    "`.001.08` (CBPR+) or `.001.13` (T2S MR2026)."
                ),
            )
        ]

        today = datetime.now(timezone.utc).date().isoformat()
        if today >= CBPR_CUTOVER_DATE:
            findings.append(
                ProfileFinding(
                    severity=ProfileSeverity.ERROR,
                    code="CAMT.SCHEMA.POST_CUTOVER",
                    message=(
                        "Deprecated schema revision presented after the "
                        "CBPR+ Nov 2026 cutover - this payload will be "
                        "rejected by the receiving clearing system."
                    ),
                )
            )

        return findings
