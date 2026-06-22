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

"""Tests for B1: schema-version negotiation."""

from __future__ import annotations

import pytest

from camt053 import services
from camt053.schema_version import (
    CURRENT_SCHEMA_VERSIONS,
    DEPRECATED_SCHEMA_VERSIONS,
    SchemaClassification,
    UnsupportedSchemaError,
    classify_schema_version,
    detect_schema_version,
    validate_schema_version,
)
from camt053.security.xml_guard import XmlSecurityError


def _wrap(version: str) -> str:
    """Return a minimal camt.05x payload at the given full version string.

    The version string looks like ``camt.053.001.08``; the helper
    splits the family and minor and renders the canonical xmlns.
    """
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Document xmlns="urn:iso:std:iso:20022:tech:xsd:{version}">'
        f"<BkToCstmrStmt><GrpHdr><MsgId>M</MsgId>"
        f"<CreDtTm>2026-06-21T10:00:00</CreDtTm></GrpHdr>"
        f"<Stmt><Id>S</Id>"
        f"<Acct><Id><IBAN>DE89370400440532013000</IBAN></Id></Acct>"
        f"</Stmt></BkToCstmrStmt></Document>"
    )


# ─── version sets ───────────────────────────────────────────────────────────


def test_current_set_includes_camt053_001_08():
    """CBPR+ producer lingua franca is in the current set."""
    assert "camt.053.001.08" in CURRENT_SCHEMA_VERSIONS


def test_current_set_includes_camt053_001_13():
    """T2S R2026.NOV target is in the current set."""
    assert "camt.053.001.13" in CURRENT_SCHEMA_VERSIONS


def test_current_set_includes_camt052_and_camt054_at_08():
    """All three siblings in the family share the .001.08 line."""
    assert "camt.052.001.08" in CURRENT_SCHEMA_VERSIONS
    assert "camt.054.001.08" in CURRENT_SCHEMA_VERSIONS


def test_deprecated_set_covers_02_through_07():
    """The deprecated set covers .02-.07 across all three families."""
    for family in ("052", "053", "054"):
        for minor in range(2, 8):
            assert (
                f"camt.{family}.001.{minor:02d}" in DEPRECATED_SCHEMA_VERSIONS
            )


def test_deprecated_and_current_sets_are_disjoint():
    """A version cannot be both current and deprecated at once."""
    overlap = CURRENT_SCHEMA_VERSIONS & DEPRECATED_SCHEMA_VERSIONS
    assert overlap == frozenset()


# ─── detect_schema_version ──────────────────────────────────────────────────


def test_detect_returns_canonical_string_for_current_version():
    """A clean .08 payload yields exactly ``"camt.053.001.08"``."""
    assert detect_schema_version(_wrap("camt.053.001.08")) == (
        "camt.053.001.08"
    )


def test_detect_handles_deprecated_minor_versions():
    """Older .02 statements still detect their version string."""
    assert detect_schema_version(_wrap("camt.053.001.02")) == (
        "camt.053.001.02"
    )


def test_detect_returns_none_for_non_camt_namespace():
    """A pain.001 payload has a non-camt.05x xmlns → None."""
    xml = (
        '<?xml version="1.0"?>'
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">'
        "<CstmrCdtTrfInitn/></Document>"
    )
    assert detect_schema_version(xml) is None


def test_detect_returns_none_for_unqualified_root():
    """A document with no xmlns at all yields None."""
    xml = '<?xml version="1.0"?><Document/>'
    assert detect_schema_version(xml) is None


def test_detect_raises_value_error_on_malformed_xml():
    """Malformed XML surfaces a clear ValueError."""
    with pytest.raises(ValueError, match="well-formed"):
        detect_schema_version("<Document>unclosed")


def test_detect_refuses_doctype_via_xml_guard():
    """A DOCTYPE payload is rejected by the xml_guard pre-flight."""
    xml = (
        "<?xml version='1.0'?>"
        "<!DOCTYPE bad [<!ENTITY x 'attack'>]>"
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08"/>'
    )
    with pytest.raises(XmlSecurityError):
        detect_schema_version(xml)


# ─── classify_schema_version ────────────────────────────────────────────────


def test_classify_current_version():
    """A current-set version classifies as ``"current"``."""
    assert (
        classify_schema_version("camt.053.001.08")
        == SchemaClassification.CURRENT
    )


def test_classify_deprecated_version():
    """A deprecated-set version classifies as ``"deprecated"``."""
    assert (
        classify_schema_version("camt.053.001.02")
        == SchemaClassification.DEPRECATED
    )


def test_classify_unknown_camt_version():
    """A version in the camt.05x family but outside both sets is ``unknown``."""
    # camt.053.001.99 doesn't exist but matches the family shape.
    assert (
        classify_schema_version("camt.053.001.99")
        == SchemaClassification.UNKNOWN
    )


def test_classify_none_is_unsupported():
    """``None`` (non-camt.05x namespace) classifies as ``unsupported``."""
    assert classify_schema_version(None) == SchemaClassification.UNSUPPORTED


# ─── validate_schema_version (report-only) ──────────────────────────────────


def test_validate_report_for_current_payload():
    """Report shape: current → supported=True."""
    report = validate_schema_version(_wrap("camt.053.001.08"))
    assert report == {
        "version": "camt.053.001.08",
        "classification": "current",
        "supported": True,
    }


def test_validate_report_for_deprecated_payload():
    """Report shape: deprecated → supported=True (still parseable)."""
    report = validate_schema_version(_wrap("camt.053.001.02"))
    assert report["classification"] == "deprecated"
    assert report["supported"] is True


def test_validate_report_for_unknown_minor():
    """An unknown minor revision yields supported=False but no raise."""
    report = validate_schema_version(_wrap("camt.053.001.99"))
    assert report["version"] == "camt.053.001.99"
    assert report["classification"] == "unknown"
    assert report["supported"] is False


def test_validate_report_for_non_camt_namespace():
    """A pain.001 payload reports version=None, classification=unsupported."""
    xml = (
        '<?xml version="1.0"?>'
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">'
        "<CstmrCdtTrfInitn/></Document>"
    )
    report = validate_schema_version(xml)
    assert report == {
        "version": None,
        "classification": "unsupported",
        "supported": False,
    }


# ─── validate_schema_version strict mode ────────────────────────────────────


def test_strict_mode_accepts_current_payload():
    """Strict mode is happy with a CBPR+ current payload."""
    report = validate_schema_version(_wrap("camt.053.001.08"), strict=True)
    assert report["supported"] is True


def test_strict_mode_accepts_deprecated_payload():
    """Strict mode still accepts deprecated payloads (real-world ERPs)."""
    # Deprecated is not refused; the v0.0.6 contract is that ERPs
    # keep working until they migrate, with a classification flag.
    report = validate_schema_version(_wrap("camt.053.001.02"), strict=True)
    assert report["classification"] == "deprecated"


def test_strict_mode_refuses_unknown_minor():
    """An unknown minor revision is refused in strict mode."""
    with pytest.raises(UnsupportedSchemaError) as info:
        validate_schema_version(_wrap("camt.053.001.99"), strict=True)
    assert info.value.classification == "unknown"
    assert info.value.detected_version == "camt.053.001.99"


def test_strict_mode_refuses_non_camt_namespace():
    """A non-camt.05x payload is refused in strict mode."""
    xml = (
        '<?xml version="1.0"?>'
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">'
        "<CstmrCdtTrfInitn/></Document>"
    )
    with pytest.raises(UnsupportedSchemaError) as info:
        validate_schema_version(xml, strict=True)
    assert info.value.classification == "unsupported"
    assert info.value.detected_version is None


def test_unsupported_schema_error_carries_classification_attribute():
    """The exception type exposes the classification + detected version."""
    err = UnsupportedSchemaError(
        "boom", classification="unknown", detected_version="camt.053.001.99"
    )
    assert err.classification == "unknown"
    assert err.detected_version == "camt.053.001.99"
    assert "boom" in str(err)


# ─── services facade re-exports ─────────────────────────────────────────────


def test_services_detect_schema_version_works():
    """services.detect_schema_version is the same function."""
    assert (
        services.detect_schema_version(_wrap("camt.053.001.08"))
        == "camt.053.001.08"
    )


def test_services_classify_schema_version_works():
    """services.classify_schema_version is the same function."""
    assert (
        services.classify_schema_version("camt.053.001.08")
        == SchemaClassification.CURRENT
    )


def test_services_validate_schema_version_works():
    """services.validate_schema_version round-trips through the facade."""
    report = services.validate_schema_version(_wrap("camt.053.001.08"))
    assert report["supported"] is True


def test_services_re_exports_sets_and_classes():
    """The constants + classes are reachable via the services facade."""
    assert services.CURRENT_SCHEMA_VERSIONS is CURRENT_SCHEMA_VERSIONS
    assert services.DEPRECATED_SCHEMA_VERSIONS is DEPRECATED_SCHEMA_VERSIONS
    assert services.SchemaClassification is SchemaClassification
    assert services.UnsupportedSchemaError is UnsupportedSchemaError
