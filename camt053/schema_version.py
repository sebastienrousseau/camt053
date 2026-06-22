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

"""ISO 20022 camt.05x schema-version detection + classification.

Real-world camt.05x statements arrive in a wide range of schema
versions: ERPs that haven't migrated still consume ``.02``; major
producing banks have largely standardised on ``.001.08`` (the CBPR+
target); the T2S R2026.NOV release will move ``.053`` / ``.054`` to
``.001.13``. Different versions add and remove fields, so consumer
applications often need to **classify** an incoming payload's
version before deciding how to handle it.

This module provides three public helpers:

* :func:`detect_schema_version` — extract the version string from
  an XML payload's root ``xmlns``.
* :func:`classify_schema_version` — bucket a version string into
  ``current`` / ``deprecated`` / ``unknown`` / ``unsupported``.
* :func:`validate_schema_version` — pre-flight a payload and return
  a structured report (the helper :mod:`camt053.compliance.cbpr_readiness`
  reaches for when CBPR+ readiness needs the same answer).

A ``strict`` mode is offered (raises :class:`UnsupportedSchemaError`)
for consumers that want to refuse unsupported majors at the API
boundary, rather than handling the classification themselves.

Why this lives outside the parser
---------------------------------
The parser is intentionally **namespace-agnostic** — it matches
elements by local name, so a statement parses identically whether
it arrives in ``.02`` or ``.13``. Consumers that need to make
*business* decisions based on version (refuse, warn, dispatch to a
profile-specific validator) need a separate, opt-in surface. This
module is that surface.

Future work: per-version profile handlers (e.g. validators that
enforce ``.13``-specific structured-address rules) are a v0.0.7
deliverable and will plug in via classification codes from this
module.
"""

from __future__ import annotations

import re
from io import StringIO
from typing import Any

from defusedxml.ElementTree import ParseError
from defusedxml.ElementTree import parse as defused_parse

from camt053.security.xml_guard import guard_xml_payload

__all__ = [
    "CURRENT_SCHEMA_VERSIONS",
    "DEPRECATED_SCHEMA_VERSIONS",
    "SchemaClassification",
    "UnsupportedSchemaError",
    "classify_schema_version",
    "detect_schema_version",
    "validate_schema_version",
]


# ─── Version sets ────────────────────────────────────────────────────────────

#: camt.05x versions that are **CBPR+ current** as of Nov 2026. ``.08``
#: is the producer lingua franca for cross-border (BNY, JPM, Citi, GS,
#: DB, BNP, SC); ``.13`` is the T2S R2026.NOV target.
CURRENT_SCHEMA_VERSIONS: frozenset[str] = frozenset(
    [
        "camt.052.001.08",
        "camt.053.001.08",
        "camt.054.001.08",
        "camt.052.001.13",
        "camt.053.001.13",
        "camt.054.001.13",
        # Wider family kept current for libraries that already ship
        # support for the corresponding bundled XSDs.
        "camt.053.001.14",
    ]
)

#: camt.05x versions formally **deprecated** by major producing banks
#: but still widely consumed by ERPs and accounting middleware. The
#: library still parses them; consumers should warn rather than fail.
DEPRECATED_SCHEMA_VERSIONS: frozenset[str] = frozenset(
    [
        f"camt.{family}.001.{minor:02d}"
        for family in ("052", "053", "054")
        for minor in range(2, 8)
    ]
)


# ─── Classification result ──────────────────────────────────────────────────


class SchemaClassification:
    """Stable string codes returned by :func:`classify_schema_version`.

    Used as the discriminator in :func:`validate_schema_version`'s
    report and as the test in ``strict`` mode (anything other than
    :attr:`CURRENT` or :attr:`DEPRECATED` raises in strict mode).
    """

    #: The version is in :data:`CURRENT_SCHEMA_VERSIONS` — produced by
    #: CBPR+ banks today, accepted everywhere.
    CURRENT = "current"

    #: The version is in :data:`DEPRECATED_SCHEMA_VERSIONS` — formally
    #: deprecated for producers but still in widespread consumer use.
    DEPRECATED = "deprecated"

    #: The version matches the camt.05x namespace shape (i.e. is a
    #: valid camt.05x version string) but falls outside the
    #: classified sets above. Treat with caution; parsing may work.
    UNKNOWN = "unknown"

    #: The payload's root xmlns does not look like a camt.05x
    #: namespace at all (e.g. it is pain.001 or unqualified).
    UNSUPPORTED = "unsupported"


# ─── Errors ─────────────────────────────────────────────────────────────────


class UnsupportedSchemaError(ValueError):
    """Raised by :func:`validate_schema_version` in ``strict`` mode.

    The accompanying :attr:`classification` (one of the
    :class:`SchemaClassification` constants) tells the caller why
    the refusal fired; :attr:`detected_version` is the raw version
    string detected from the payload (``None`` for non-camt.05x
    namespaces).
    """

    def __init__(
        self,
        message: str,
        *,
        classification: str,
        detected_version: str | None,
    ) -> None:
        """Build an UnsupportedSchemaError with classification context."""
        super().__init__(message)
        self.classification = classification
        self.detected_version = detected_version


# ─── Regex helpers ──────────────────────────────────────────────────────────

# Matches the canonical ISO 20022 camt.05x namespace URIs:
#   urn:iso:std:iso:20022:tech:xsd:camt.053.001.08
_CAMT_NAMESPACE_RE = re.compile(
    r"urn:iso:std:iso:20022:tech:xsd:(camt\.0(5[234])\.001\.\d{2})"
)


# ─── Public API ─────────────────────────────────────────────────────────────


def detect_schema_version(xml: str) -> str | None:
    """Return the camt.05x schema version from a payload's root xmlns.

    Walks just the root element (cheap, no full parse) and pulls the
    version string out of the namespace URI. Hostile / malformed
    input is rejected by the existing
    :func:`camt053.security.xml_guard.guard_xml_payload` and
    :mod:`defusedxml` pre-flight, so this helper is safe to call on
    untrusted bank files.

    Args:
        xml: The raw XML payload as a string.

    Returns:
        The detected version string (e.g. ``"camt.053.001.08"``), or
        ``None`` if the root has no recognised camt.05x namespace.

    Raises:
        camt053.security.xml_guard.XmlSecurityError: For oversized
            payloads or inline DOCTYPE / ENTITY declarations.
        ValueError: For payloads that are not well-formed XML.
    """
    guard_xml_payload(xml)
    try:
        tree = defused_parse(StringIO(xml))
    except ParseError as exc:
        raise ValueError(f"Not well-formed XML: {exc}") from exc
    root = tree.getroot()
    if root is None:  # pragma: no cover — getroot only returns None pre-parse
        return None
    if not root.tag.startswith("{"):
        return None
    namespace_uri = root.tag[1 : root.tag.index("}")]
    match = _CAMT_NAMESPACE_RE.match(namespace_uri)
    return match.group(1) if match else None


def classify_schema_version(version: str | None) -> str:
    """Bucket a detected version into one of the four stable codes.

    Args:
        version: The version string returned by
            :func:`detect_schema_version`, or ``None``.

    Returns:
        One of the :class:`SchemaClassification` constants
        (``"current"`` / ``"deprecated"`` / ``"unknown"`` /
        ``"unsupported"``). ``None`` input always maps to
        :attr:`SchemaClassification.UNSUPPORTED`.
    """
    if version is None:
        return SchemaClassification.UNSUPPORTED
    if version in CURRENT_SCHEMA_VERSIONS:
        return SchemaClassification.CURRENT
    if version in DEPRECATED_SCHEMA_VERSIONS:
        return SchemaClassification.DEPRECATED
    # The version detector only matches the camt.05x namespace
    # shape, so we know we are inside the family — just not a
    # classified minor revision.
    return SchemaClassification.UNKNOWN


def validate_schema_version(
    xml: str,
    *,
    strict: bool = False,
) -> dict[str, Any]:
    """Pre-flight a camt.05x payload's schema version.

    Combines :func:`detect_schema_version` and
    :func:`classify_schema_version` into a single call returning a
    structured report. ``strict`` mode raises
    :class:`UnsupportedSchemaError` on any classification other than
    :attr:`SchemaClassification.CURRENT` or
    :attr:`SchemaClassification.DEPRECATED` (i.e. unknown camt.05x
    minor revisions and non-camt.05x namespaces are refused).

    Args:
        xml: The raw XML payload as a string.
        strict: If ``True``, refuse anything outside the current and
            deprecated sets. Defaults to ``False`` (report-only).

    Returns:
        A dictionary with the shape::

            {
                "version": "camt.053.001.08" | None,
                "classification": "current" | "deprecated" |
                                  "unknown" | "unsupported",
                "supported": bool,
            }

        ``supported`` is ``True`` iff the classification is
        :attr:`SchemaClassification.CURRENT` or
        :attr:`SchemaClassification.DEPRECATED`.

    Raises:
        UnsupportedSchemaError: In ``strict`` mode, when the
            classification is :attr:`SchemaClassification.UNKNOWN` or
            :attr:`SchemaClassification.UNSUPPORTED`.
        camt053.security.xml_guard.XmlSecurityError: For oversized /
            hostile payloads (DOCTYPE, ENTITY).
        ValueError: For payloads that are not well-formed XML.
    """
    version = detect_schema_version(xml)
    classification = classify_schema_version(version)
    supported = classification in (
        SchemaClassification.CURRENT,
        SchemaClassification.DEPRECATED,
    )
    if strict and not supported:
        raise UnsupportedSchemaError(
            (
                f"Refusing schema version {version!r}: classification "
                f"{classification!r} is not accepted under strict mode."
            ),
            classification=classification,
            detected_version=version,
        )
    return {
        "version": version,
        "classification": classification,
        "supported": supported,
    }
