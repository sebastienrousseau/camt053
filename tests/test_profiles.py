# Copyright (C) 2023-2026 Sebastien Rousseau.
# SPDX-License-Identifier: Apache-2.0
"""Tests for the per-schema-version profile dispatch (#85)."""

from __future__ import annotations

import dataclasses
from unittest import mock

import pytest

from camt053.profiles import (
    Profile_v02,
    Profile_v08,
    Profile_v13,
    Profile_v14,
    ProfileFinding,
    ProfileSeverity,
    SchemaProfile,
    get_profile,
    list_profiles,
    profile_for_xml,
)
from camt053.profiles.base import SchemaProfile as _AbcSchemaProfile
from camt053.services import validate_against_profile

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_NS = {
    "08": "urn:iso:std:iso:20022:tech:xsd:camt.053.001.08",
    "13": "urn:iso:std:iso:20022:tech:xsd:camt.053.001.13",
    "14": "urn:iso:std:iso:20022:tech:xsd:camt.053.001.14",
    "02": "urn:iso:std:iso:20022:tech:xsd:camt.053.001.02",
}


def _wrap(ns: str, inner: str = "") -> str:
    """Wrap an inner snippet in a minimal camt.053 Document for the namespace."""
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Document xmlns="{ns}"><BkToCstmrStmt><Stmt>'
        f"{inner}"
        f"</Stmt></BkToCstmrStmt></Document>"
    )


UNSTRUCTURED_PSTL = "<PstlAdr><AdrLine>1 Main St</AdrLine></PstlAdr>"
STRUCTURED_PSTL = "<PstlAdr><TwnNm>London</TwnNm><Ctry>GB</Ctry></PstlAdr>"
PARTIAL_MISSING_CTRY = (
    "<PstlAdr><StrtNm>Main St</StrtNm><TwnNm>London</TwnNm></PstlAdr>"
)


# ---------------------------------------------------------------------------
# Base classes
# ---------------------------------------------------------------------------


class TestProfileSeverity:
    """The severity enum is stable as a wire format."""

    def test_string_values_are_stable(self) -> None:
        assert ProfileSeverity.ERROR.value == "error"
        assert ProfileSeverity.WARNING.value == "warning"
        assert ProfileSeverity.INFO.value == "info"

    def test_iteration(self) -> None:
        assert {s.value for s in ProfileSeverity} == {
            "error",
            "warning",
            "info",
        }


class TestProfileFinding:
    """ProfileFinding shape + JSON round-trip."""

    def test_dict_view(self) -> None:
        f = ProfileFinding(
            severity=ProfileSeverity.WARNING,
            code="X.Y",
            message="m",
            element="PstlAdr",
            location="PstlAdr[0]",
        )
        d = f.to_dict()
        assert d == {
            "severity": "warning",
            "code": "X.Y",
            "message": "m",
            "element": "PstlAdr",
            "location": "PstlAdr[0]",
        }

    def test_frozen(self) -> None:
        f = ProfileFinding(
            severity=ProfileSeverity.INFO, code="x", message="x"
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            f.code = "y"  # type: ignore[misc]


class TestSchemaProfileAbstractness:
    """SchemaProfile cannot be instantiated directly."""

    def test_abstract(self) -> None:
        with pytest.raises(TypeError):
            _AbcSchemaProfile()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# Profile_v02 (deprecated family)
# ---------------------------------------------------------------------------


class TestProfileV02:
    """Deprecated .02-.07 family."""

    def test_emits_deprecation_warning(self) -> None:
        findings = Profile_v02().validate(_wrap(_NS["02"]))
        codes = [f.code for f in findings]
        assert "CAMT.SCHEMA.DEPRECATED" in codes

    def test_parse_failure_yields_error(self) -> None:
        findings = Profile_v02().validate("not xml")
        assert findings[0].severity == ProfileSeverity.ERROR
        assert findings[0].code == "CAMT.PROFILE.PARSE_FAILED"

    def test_post_cutover_adds_error(self) -> None:
        with mock.patch("camt053.profiles.v02.datetime") as mock_dt:
            from datetime import datetime, timezone

            mock_dt.now.return_value = datetime(
                2027, 1, 1, tzinfo=timezone.utc
            )
            findings = Profile_v02().validate(_wrap(_NS["02"]))
        codes = [f.code for f in findings]
        assert "CAMT.SCHEMA.POST_CUTOVER" in codes
        post = next(
            f for f in findings if f.code == "CAMT.SCHEMA.POST_CUTOVER"
        )
        assert post.severity == ProfileSeverity.ERROR


# ---------------------------------------------------------------------------
# Profile_v08 (cross-border current)
# ---------------------------------------------------------------------------


class TestProfileV08:
    """Cross-border CBPR+ producer current set."""

    def test_warns_on_unstructured_only(self) -> None:
        xml = _wrap(_NS["08"], UNSTRUCTURED_PSTL)
        findings = Profile_v08().validate(xml)
        assert findings
        assert findings[0].severity == ProfileSeverity.WARNING
        assert findings[0].code == "CAMT.CBPR.UNSTRUCTURED_ADDRESS"
        assert findings[0].element == "PstlAdr"

    def test_no_finding_for_structured(self) -> None:
        xml = _wrap(_NS["08"], STRUCTURED_PSTL)
        assert Profile_v08().validate(xml) == []

    def test_parse_failure_yields_error(self) -> None:
        findings = Profile_v08().validate("not xml")
        assert findings[0].code == "CAMT.PROFILE.PARSE_FAILED"

    def test_multiple_unstructured_each_reported(self) -> None:
        xml = _wrap(_NS["08"], UNSTRUCTURED_PSTL + UNSTRUCTURED_PSTL)
        findings = Profile_v08().validate(xml)
        assert len(findings) == 2
        assert findings[0].location != findings[1].location


# ---------------------------------------------------------------------------
# Profile_v13 (T2S MR2026 strict)
# ---------------------------------------------------------------------------


class TestProfileV13:
    """T2S MR2026 strict address rules."""

    def test_error_on_unstructured_only(self) -> None:
        xml = _wrap(_NS["13"], UNSTRUCTURED_PSTL)
        findings = Profile_v13().validate(xml)
        assert findings[0].severity == ProfileSeverity.ERROR
        assert findings[0].code == "CAMT.MR2026.UNSTRUCTURED_ADDRESS"

    def test_error_on_partial_missing_country(self) -> None:
        xml = _wrap(_NS["13"], PARTIAL_MISSING_CTRY)
        findings = Profile_v13().validate(xml)
        codes = [f.code for f in findings]
        assert "CAMT.MR2026.MISSING_COUNTRY" in codes

    def test_clean_payload_yields_no_findings(self) -> None:
        xml = _wrap(_NS["13"], STRUCTURED_PSTL)
        assert Profile_v13().validate(xml) == []

    def test_parse_failure_yields_error(self) -> None:
        findings = Profile_v13().validate("nope")
        assert findings[0].code == "CAMT.PROFILE.PARSE_FAILED"


# ---------------------------------------------------------------------------
# Profile_v14 (inherits .13 rules)
# ---------------------------------------------------------------------------


class TestProfileV14:
    """Profile_v14 inherits the strict v13 rules."""

    def test_inherits_v13(self) -> None:
        assert issubclass(Profile_v14, Profile_v13)

    def test_same_strict_address_rule(self) -> None:
        xml = _wrap(_NS["14"], UNSTRUCTURED_PSTL)
        findings = Profile_v14().validate(xml)
        assert findings[0].code == "CAMT.MR2026.UNSTRUCTURED_ADDRESS"

    def test_version_attribute(self) -> None:
        assert Profile_v14.version == "camt.053.001.14"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestRegistry:
    """The registry resolves every supported minor revision."""

    @pytest.mark.parametrize(
        ("version", "expected_cls"),
        [
            ("camt.053.001.02", Profile_v02),
            ("camt.053.001.03", Profile_v02),
            ("camt.053.001.04", Profile_v02),
            ("camt.053.001.05", Profile_v02),
            ("camt.053.001.06", Profile_v02),
            ("camt.053.001.07", Profile_v02),
            ("camt.053.001.08", Profile_v08),
            ("camt.053.001.13", Profile_v13),
            ("camt.053.001.14", Profile_v14),
            ("camt.052.001.13", Profile_v13),
            ("camt.054.001.13", Profile_v13),
        ],
    )
    def test_get_profile(
        self, version: str, expected_cls: type[SchemaProfile]
    ) -> None:
        profile = get_profile(version)
        assert profile is not None
        assert isinstance(profile, expected_cls)

    def test_get_profile_unknown_version(self) -> None:
        assert get_profile("camt.999.999.99") is None

    def test_get_profile_malformed_string(self) -> None:
        assert get_profile("not-a-version") is None

    def test_list_profiles_one_per_minor(self) -> None:
        profiles = list_profiles()
        # 4 distinct profile classes (v02 covers .02-.07 but is one instance)
        assert {type(p).__name__ for p in profiles} == {
            "Profile_v02",
            "Profile_v08",
            "Profile_v13",
            "Profile_v14",
        }

    def test_profile_for_xml_resolves_via_namespace(self) -> None:
        xml = _wrap(_NS["13"], STRUCTURED_PSTL)
        profile = profile_for_xml(xml)
        assert isinstance(profile, Profile_v13)

    def test_profile_for_xml_no_namespace(self) -> None:
        assert profile_for_xml("<Document/>") is None

    def test_profile_for_xml_unsupported_minor(self) -> None:
        xml = _wrap("urn:iso:std:iso:20022:tech:xsd:camt.053.001.99")
        assert profile_for_xml(xml) is None


# ---------------------------------------------------------------------------
# services.validate_against_profile (the public entry point)
# ---------------------------------------------------------------------------


class TestValidateAgainstProfile:
    """The services-layer entry point that drives the registry."""

    def test_clean_v13_payload_is_ready(self) -> None:
        xml = _wrap(_NS["13"], STRUCTURED_PSTL)
        result = validate_against_profile(xml)
        assert result["ready"] is True
        assert result["profile"] == "Profile_v13"
        assert result["findings"] == []
        assert result["schema_version"] == "camt.053.001.13"

    def test_unstructured_v13_is_not_ready(self) -> None:
        xml = _wrap(_NS["13"], UNSTRUCTURED_PSTL)
        result = validate_against_profile(xml)
        assert result["ready"] is False
        codes = [f["code"] for f in result["findings"]]
        assert "CAMT.MR2026.UNSTRUCTURED_ADDRESS" in codes

    def test_v08_warning_does_not_block_ready(self) -> None:
        # v08 emits a WARNING, not an ERROR -- ready stays True.
        xml = _wrap(_NS["08"], UNSTRUCTURED_PSTL)
        result = validate_against_profile(xml)
        assert result["ready"] is True
        assert result["findings"]
        assert result["findings"][0]["severity"] == "warning"

    def test_unregistered_version_reports_error(self) -> None:
        xml = _wrap("urn:iso:std:iso:20022:tech:xsd:camt.053.001.99")
        result = validate_against_profile(xml)
        assert result["ready"] is False
        assert result["profile"] is None
        assert result["findings"][0]["code"] == "CAMT.PROFILE.UNREGISTERED"

    def test_findings_are_json_serialisable(self) -> None:
        import json as _json

        xml = _wrap(_NS["13"], UNSTRUCTURED_PSTL)
        result = validate_against_profile(xml)
        # round-trips without raising
        assert _json.loads(_json.dumps(result)) == result
