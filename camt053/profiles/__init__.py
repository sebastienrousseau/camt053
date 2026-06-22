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

"""Per-schema-version validation profiles.

A *profile* encapsulates the rules a single camt.05x schema minor
revision is expected to enforce, **on top of** the namespace-agnostic
parser. The parser stays simple (one element-by-local-name walk for
every revision); the profile says "and on top of that, for ``.001.13``
the postal addresses must be structured".

Pick a profile via :func:`get_profile` (looks up by version string) or
:func:`profile_for_xml` (detects the version from the payload first):

    >>> from camt053.profiles import profile_for_xml
    >>> profile = profile_for_xml(xml)
    >>> findings = profile.validate(xml)
    >>> errors = [f for f in findings if f.severity == ProfileSeverity.ERROR]

The :class:`SchemaProfile` API is intentionally minimal so a profile
for a new revision is one file: subclass, set ``version`` and
``classification``, implement ``validate``.

The profile machinery is **opt-in** and never invoked by the bare
parser; the parser and validator remain backwards-compatible.
"""

from camt053.profiles.base import (
    ProfileFinding,
    ProfileSeverity,
    SchemaProfile,
)
from camt053.profiles.registry import (
    get_profile,
    list_profiles,
    profile_for_xml,
)
from camt053.profiles.v02 import Profile_v02
from camt053.profiles.v08 import Profile_v08
from camt053.profiles.v13 import Profile_v13
from camt053.profiles.v14 import Profile_v14

__all__ = [
    "Profile_v02",
    "Profile_v08",
    "Profile_v13",
    "Profile_v14",
    "ProfileFinding",
    "ProfileSeverity",
    "SchemaProfile",
    "get_profile",
    "list_profiles",
    "profile_for_xml",
]
