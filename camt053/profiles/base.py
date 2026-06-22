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

"""Base classes for per-schema-version validation profiles."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class ProfileSeverity(str, Enum):
    """Severity buckets a profile finding can land in.

    The string values are stable and used as the wire format
    (``finding.severity == "error"`` is a fine alternative to the
    enum equality).
    """

    #: Will be rejected by the relevant clearing system / consumer.
    ERROR = "error"

    #: Will not be rejected today but is on a deprecation path.
    WARNING = "warning"

    #: Operator-grade note (e.g. "this revision is supported but the
    #: next one is preferred").
    INFO = "info"


@dataclass(frozen=True, slots=True)
class ProfileFinding:
    """One finding produced by a :class:`SchemaProfile`.

    Wire shape::

        {
            "severity": "error" | "warning" | "info",
            "code": "CAMT.CBPR.STRUCTURED_ADDRESS_REQUIRED",
            "message": "human-readable explanation",
            "element": "PstlAdr" | None,
            "location": "Stmt[0]/Ntry[3]/NtryDtls/TxDtls/RltdPties/Dbtr/PstlAdr" | None,
        }

    ``code`` is a stable, dotted identifier suitable for grep + alerting;
    ``message`` is the user-facing text; ``element`` and ``location`` are
    optional pointers into the payload.
    """

    severity: ProfileSeverity
    code: str
    message: str
    element: str | None = None
    location: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict view."""
        return {**asdict(self), "severity": self.severity.value}


class SchemaProfile(ABC):
    """The contract every schema profile implements.

    Concrete subclasses pin two class attributes:

    * ``version`` — the dotted version string this profile targets
      (e.g. ``"camt.053.001.13"``).
    * ``classification`` — the value the
      :mod:`camt053.schema_version` module would return for that
      version (``"current"`` / ``"deprecated"`` / ``"unknown"``).
      Used by the registry to surface deprecation warnings.

    Subclasses then implement :meth:`validate`, which is given the
    raw XML and returns zero or more :class:`ProfileFinding` objects.
    The profile is **deliberately stateless** — the same instance is
    safe to share across threads.
    """

    #: The dotted version string this profile targets.
    version: str = ""

    #: Classification bucket (``"current"`` / ``"deprecated"`` / ``"unknown"``).
    classification: str = ""

    @abstractmethod
    def validate(self, xml: str) -> list[ProfileFinding]:
        """Run the version-specific rules and return any findings.

        Implementations should be tolerant of malformed payloads: a
        parse failure should yield a single ``severity=error`` finding
        rather than raise.
        """

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"{type(self).__name__}(version={self.version!r})"
