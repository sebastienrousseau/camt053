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

"""Profile registry: resolve a schema version to a :class:`SchemaProfile`.

The registry is fixed at import time (built from the four shipped
profiles) and treated as read-only. New revisions land by adding a
profile module and an entry here.
"""

from __future__ import annotations

from camt053.profiles.base import SchemaProfile
from camt053.profiles.v02 import Profile_v02
from camt053.profiles.v08 import Profile_v08
from camt053.profiles.v13 import Profile_v13
from camt053.profiles.v14 import Profile_v14
from camt053.schema_version import (
    detect_schema_version,
)

# Singleton per profile - profiles are stateless so this is safe and lets
# ``list_profiles`` dedupe by instance identity below.
_V02_SINGLETON: SchemaProfile = Profile_v02()
_V08_SINGLETON: SchemaProfile = Profile_v08()
_V13_SINGLETON: SchemaProfile = Profile_v13()
_V14_SINGLETON: SchemaProfile = Profile_v14()

_PROFILES_BY_MINOR: dict[str, SchemaProfile] = {
    "02": _V02_SINGLETON,
    "03": _V02_SINGLETON,
    "04": _V02_SINGLETON,
    "05": _V02_SINGLETON,
    "06": _V02_SINGLETON,
    "07": _V02_SINGLETON,
    "08": _V08_SINGLETON,
    "13": _V13_SINGLETON,
    "14": _V14_SINGLETON,
}


def _minor_of(version: str) -> str | None:
    """Return the ``.001.NN`` minor suffix from a dotted version string."""
    parts = version.split(".")
    return parts[-1] if len(parts) >= 4 else None


def get_profile(version: str) -> SchemaProfile | None:
    """Return the profile for ``version`` or ``None`` if no profile fits.

    Lookup is by the minor revision suffix (``.001.NN``), so
    ``camt.052.001.13``, ``camt.053.001.13``, and ``camt.054.001.13``
    all resolve to the same profile instance.

    Args:
        version: A dotted version string like ``"camt.053.001.13"``.
    """
    minor = _minor_of(version)
    if minor is None:
        return None
    return _PROFILES_BY_MINOR.get(minor)


def list_profiles() -> list[SchemaProfile]:
    """Return one representative profile per supported minor revision."""
    seen: set[int] = set()
    out: list[SchemaProfile] = []
    for profile in _PROFILES_BY_MINOR.values():
        if id(profile) in seen:
            continue
        seen.add(id(profile))
        out.append(profile)
    return out


def profile_for_xml(xml: str) -> SchemaProfile | None:
    """Detect ``xml`` 's version and return its profile.

    Returns ``None`` when the namespace cannot be detected, or the
    detected version has no registered profile.
    """
    version = detect_schema_version(xml)
    if version is None:
        return None
    return get_profile(version)
