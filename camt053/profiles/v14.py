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

"""Profile for the latest ``camt.053.001.14`` family.

``.001.14`` is the wider-family revision kept current alongside
``.001.13`` (XSD bundled). The strict rules from
:class:`Profile_v13` carry across; this subclass exists so the
registry can target ``.14`` directly.
"""

from __future__ import annotations

from camt053.profiles.v13 import Profile_v13


class Profile_v14(Profile_v13):
    """Profile for any ``camt.053.001.14`` payload."""

    version = "camt.053.001.14"
    classification = "current"
