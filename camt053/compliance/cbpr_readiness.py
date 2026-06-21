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

"""CBPR+ / Nov 2026 readiness checks for camt.053 statements.

A coordinated CBPR+ / Fedwire / CHAPS / T2 cutover lands on
**14-16 November 2026**: unstructured-only postal addresses get
rejected, `camt.110/111` exceptions and investigations become
mandatory, and T2S R2026.NOV upgrades camt.053 / 054 to schema
revision MR2026.

This module ships :func:`check_cbpr_readiness`, a deterministic
pre-flight checker that walks a camt.053 payload and reports any
content that will fail the Nov 2026 acceptance rules.

The checker is intentionally side-effect free, does no network I/O,
and reuses :mod:`camt053.security.xml_guard` plus :mod:`defusedxml`
for safe parsing of untrusted input.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from io import StringIO
from typing import Any

from defusedxml.ElementTree import ParseError
from defusedxml.ElementTree import parse as defused_parse

from camt053.security.xml_guard import guard_xml_payload

__all__ = [
    "CBPR_CUTOVER_DATE",
    "check_cbpr_readiness",
]


#: The coordinated CBPR+ / Fedwire / CHAPS / T2 cutover. ISO-8601 date.
#: After this date the rules checked by :func:`check_cbpr_readiness`
#: are enforced by the major clearing systems; payments that fail will
#: be rejected at receive-time.
CBPR_CUTOVER_DATE = "2026-11-16"


# camt.053 schema versions that are formally **deprecated** by major
# producing banks for CBPR+ payments but still widely consumed by
# ERPs. Flagged as warnings, not errors, because the consumer-side
# market has not yet caught up.
_DEPRECATED_SCHEMA_VERSIONS = frozenset(
    {
        "camt.053.001.02",
        "camt.053.001.03",
        "camt.053.001.04",
        "camt.053.001.05",
        "camt.053.001.06",
        "camt.053.001.07",
    }
)

# camt.053 schema versions that are CBPR+ current as of Nov 2026.
# .08 is the producer lingua franca (BNY, JPM, Citi, GS, DB, BNP, SC).
# .13 is the T2S R2026.NOV target.
_CURRENT_SCHEMA_VERSIONS = frozenset(
    {
        "camt.053.001.08",
        "camt.053.001.13",
    }
)

# Match the xmlns namespace URI to extract the schema version.
_NAMESPACE_RE = re.compile(
    r"urn:iso:std:iso:20022:tech:xsd:(camt\.053\.001\.\d{2})"
)


def check_cbpr_readiness(xml: str) -> dict[str, Any]:
    """Check a camt.053 payload for CBPR+ Nov 2026 readiness.

    The checker walks the document and reports:

    * **Schema version** vs the CBPR+ current set (``camt.053.001.08`` /
      ``camt.053.001.13``). Deprecated versions are flagged as
      warnings, unknown versions as errors.
    * **Postal addresses**: every ``<PstlAdr>`` element is classified
      as *fully structured* (no ``<AdrLine>``), *hybrid* (both
      ``<AdrLine>`` and ``<Twn>``/``<Ctry>``), or *unstructured-only*
      (one or more ``<AdrLine>`` with no ``<Twn>``/``<Ctry>`` sibling).
      Unstructured-only is the Nov 2026 reject case.

    Args:
        xml: The camt.053 payload as a string. The same byte-cap and
            DOCTYPE/ENTITY pre-flight enforced by
            :func:`camt053.security.xml_guard.guard_xml_payload` apply
            here.

    Returns:
        A dictionary with the shape:

        .. code-block:: python

            {
                "cbpr_ready": bool,
                "schema_version": str | None,
                "checked_at": "<ISO 8601 UTC timestamp>",
                "cutover_date": "2026-11-16",
                "issues": [
                    {
                        "code": "<STABLE_CODE>",
                        "severity": "error" | "warning",
                        "path": "<XPath-style location>",
                        "message": "<human-readable explanation>",
                    },
                    ...
                ],
                "summary": {
                    "addresses_checked": int,
                    "fully_structured": int,
                    "hybrid": int,
                    "unstructured_only": int,
                },
            }

        ``cbpr_ready`` is ``True`` iff no ``severity="error"`` issue
        was raised.

    Raises:
        camt053.security.xml_guard.XmlSecurityError: If the payload
            exceeds the byte cap or carries a DOCTYPE / ENTITY
            declaration.
        ValueError: If the payload is not well-formed XML.
    """
    guard_xml_payload(xml)
    try:
        tree = defused_parse(StringIO(xml))
    except ParseError as exc:
        raise ValueError(f"Not well-formed XML: {exc}") from exc

    root = tree.getroot()
    issues: list[dict[str, Any]] = []
    summary = {
        "addresses_checked": 0,
        "fully_structured": 0,
        "hybrid": 0,
        "unstructured_only": 0,
    }

    schema_version = _detect_schema_version(root)
    _check_schema_version(schema_version, issues)
    _check_addresses(root, issues, summary)

    cbpr_ready = not any(
        issue["severity"] == "error" for issue in issues
    )

    return {
        "cbpr_ready": cbpr_ready,
        "schema_version": schema_version,
        "checked_at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "cutover_date": CBPR_CUTOVER_DATE,
        "issues": issues,
        "summary": summary,
    }


def _detect_schema_version(root: Any) -> str | None:
    """Return the camt.053 schema version from the root element's xmlns.

    Returns ``None`` if the root element has no recognised namespace.
    """
    # ElementTree wraps the namespace in braces: "{xmlns}LocalName".
    if not root.tag.startswith("{"):
        return None
    namespace_uri = root.tag[1 : root.tag.index("}")]
    match = _NAMESPACE_RE.match(namespace_uri)
    return match.group(1) if match else None


def _check_schema_version(
    schema_version: str | None,
    issues: list[dict[str, Any]],
) -> None:
    """Append an issue if the schema version is unknown or deprecated."""
    if schema_version is None:
        issues.append(
            {
                "code": "UNKNOWN_SCHEMA",
                "severity": "error",
                "path": "/Document",
                "message": (
                    "Root element xmlns is not a recognised "
                    "camt.053 namespace. Cannot proceed with CBPR+ "
                    "readiness checks."
                ),
            }
        )
        return
    if schema_version in _DEPRECATED_SCHEMA_VERSIONS:
        issues.append(
            {
                "code": "DEPRECATED_SCHEMA",
                "severity": "warning",
                "path": "/Document",
                "message": (
                    f"Schema {schema_version} is deprecated for "
                    "CBPR+ producers; the current target is "
                    "camt.053.001.08. ERPs still consume .02-.07, "
                    "so this is a warning, not an error."
                ),
            }
        )
    elif schema_version not in _CURRENT_SCHEMA_VERSIONS:
        issues.append(
            {
                "code": "UNRECOGNISED_SCHEMA_VERSION",
                "severity": "warning",
                "path": "/Document",
                "message": (
                    f"Schema {schema_version} is not in the known "
                    "deprecated set nor the CBPR+ current set "
                    "(.08, .13). Verify it is what you intend."
                ),
            }
        )


def _check_addresses(
    root: Any,
    issues: list[dict[str, Any]],
    summary: dict[str, int],
) -> None:
    """Walk every <PstlAdr> in the tree and classify its structure."""
    for path, element in _iter_postal_addresses(root):
        summary["addresses_checked"] += 1
        local_children = {_localname(c.tag) for c in element}
        has_adrline = "AdrLine" in local_children
        has_town = "TwnNm" in local_children
        has_country = "Ctry" in local_children
        if not has_adrline:
            summary["fully_structured"] += 1
            continue
        if has_town and has_country:
            summary["hybrid"] += 1
            continue
        summary["unstructured_only"] += 1
        issues.append(
            {
                "code": "UNSTRUCTURED_ONLY_ADDRESS",
                "severity": "error",
                "path": path,
                "message": (
                    "Postal address carries only AdrLine with no "
                    "TwnNm + Ctry siblings. Unstructured-only "
                    "addresses are rejected after the CBPR+ Nov 2026 "
                    f"cutover ({CBPR_CUTOVER_DATE}). Add structured "
                    "TwnNm and Ctry, or convert to fully structured."
                ),
            }
        )


def _iter_postal_addresses(
    root: Any,
) -> list[tuple[str, Any]]:
    """Return ``(xpath, element)`` for every PstlAdr in the document."""
    found: list[tuple[str, Any]] = []
    _walk(root, "", found)
    return found


def _walk(
    node: Any,
    parent_path: str,
    collected: list[tuple[str, Any]],
) -> None:
    """Pre-order walk that collects every PstlAdr along the way."""
    # Track ordinal among siblings of the same local name for a
    # human-readable path. ElementTree does not give us the parent;
    # callers compute that and recurse with the accumulated path.
    name_counts: dict[str, int] = {}
    for child in node:
        local = _localname(child.tag)
        index = name_counts.get(local, 0)
        name_counts[local] = index + 1
        # Only annotate the path with the ordinal when there is more
        # than one sibling of the same name (after the walk completes
        # we cannot retroactively annotate, but it is acceptable to
        # always include the index for clarity).
        child_path = f"{parent_path}/{local}[{index}]"
        if local == "PstlAdr":
            collected.append((child_path, child))
        _walk(child, child_path, collected)


def _localname(tag: str) -> str:
    """Strip the ``{xmlns}`` prefix from an ElementTree tag string."""
    if tag.startswith("{"):
        return tag[tag.index("}") + 1 :]
    return tag
