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

"""Tests for the CBPR+ Nov 2026 readiness checker."""

from __future__ import annotations

import pytest

from camt053.compliance import (
    CBPR_CUTOVER_DATE,
    check_cbpr_readiness,
)
from camt053.security.xml_guard import XmlSecurityError


def _wrap(inner_xml: str, version: str = "08") -> str:
    """Wrap ``inner_xml`` in a minimal camt.053 envelope of the given version."""
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.{version}">\n'
        f"  <BkToCstmrStmt>\n"
        f"    <GrpHdr><MsgId>MSG-1</MsgId>"
        f"<CreDtTm>2026-06-21T10:00:00</CreDtTm></GrpHdr>\n"
        f"    <Stmt>\n"
        f"      <Id>STMT-1</Id>\n"
        f"      <Acct><Id><IBAN>DE89370400440532013000</IBAN></Id></Acct>\n"
        f"      {inner_xml}\n"
        f"    </Stmt>\n"
        f"  </BkToCstmrStmt>\n"
        f"</Document>\n"
    )


def test_cutover_date_constant_is_nov_2026() -> None:
    """The exported constant is the official CBPR+ cutover date."""
    assert CBPR_CUTOVER_DATE == "2026-11-16"


def test_clean_v08_payload_with_no_addresses_is_ready() -> None:
    """A minimal camt.053.001.08 payload with no addresses is CBPR+ ready."""
    result = check_cbpr_readiness(_wrap("", version="08"))
    assert result["cbpr_ready"] is True
    assert result["schema_version"] == "camt.053.001.08"
    assert result["cutover_date"] == "2026-11-16"
    assert result["summary"]["addresses_checked"] == 0
    assert result["issues"] == []


def test_v13_payload_is_recognised_as_current() -> None:
    """camt.053.001.13 is the CBPR+ target for T2S R2026.NOV."""
    result = check_cbpr_readiness(_wrap("", version="13"))
    assert result["cbpr_ready"] is True
    assert result["schema_version"] == "camt.053.001.13"


def test_deprecated_schema_version_is_a_warning_not_an_error() -> None:
    """ERPs still consume .02; flag as warning, keep cbpr_ready True."""
    result = check_cbpr_readiness(_wrap("", version="02"))
    assert result["cbpr_ready"] is True
    assert result["schema_version"] == "camt.053.001.02"
    codes = [i["code"] for i in result["issues"]]
    severities = [i["severity"] for i in result["issues"]]
    assert "DEPRECATED_SCHEMA" in codes
    assert "warning" in severities
    assert "error" not in severities


def test_unknown_schema_version_is_a_warning() -> None:
    """A version we have not classified gets flagged as a warning."""
    result = check_cbpr_readiness(_wrap("", version="99"))
    codes = [i["code"] for i in result["issues"]]
    assert "UNRECOGNISED_SCHEMA_VERSION" in codes


def test_non_camt053_namespace_is_an_error() -> None:
    """A non-camt.053 root element fails with UNKNOWN_SCHEMA."""
    xml = (
        '<?xml version="1.0"?>'
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">'
        "<Stmt/></Document>"
    )
    result = check_cbpr_readiness(xml)
    assert result["cbpr_ready"] is False
    assert result["schema_version"] is None
    codes = [i["code"] for i in result["issues"]]
    assert "UNKNOWN_SCHEMA" in codes


def test_no_namespace_at_all_is_an_error() -> None:
    """A document without xmlns also fails UNKNOWN_SCHEMA."""
    xml = '<?xml version="1.0"?><Document><Stmt/></Document>'
    result = check_cbpr_readiness(xml)
    assert result["cbpr_ready"] is False
    assert result["schema_version"] is None


def test_fully_structured_address_passes() -> None:
    """An address with TwnNm + Ctry and no AdrLine is fully structured."""
    address = (
        "<Ntry><NtryDtls><TxDtls><RltdPties><Cdtr>"
        "<PstlAdr>"
        "<TwnNm>Frankfurt</TwnNm>"
        "<Ctry>DE</Ctry>"
        "</PstlAdr>"
        "</Cdtr></RltdPties></TxDtls></NtryDtls></Ntry>"
    )
    result = check_cbpr_readiness(_wrap(address))
    assert result["cbpr_ready"] is True
    assert result["summary"]["addresses_checked"] == 1
    assert result["summary"]["fully_structured"] == 1
    assert result["summary"]["unstructured_only"] == 0


def test_hybrid_address_with_adrline_plus_twn_ctry_passes() -> None:
    """AdrLine alongside structured TwnNm + Ctry is the hybrid case (OK)."""
    address = (
        "<Ntry><NtryDtls><TxDtls><RltdPties><Cdtr>"
        "<PstlAdr>"
        "<AdrLine>123 High Street</AdrLine>"
        "<TwnNm>London</TwnNm>"
        "<Ctry>GB</Ctry>"
        "</PstlAdr>"
        "</Cdtr></RltdPties></TxDtls></NtryDtls></Ntry>"
    )
    result = check_cbpr_readiness(_wrap(address))
    assert result["cbpr_ready"] is True
    assert result["summary"]["hybrid"] == 1


def test_unstructured_only_address_is_an_error() -> None:
    """AdrLine without TwnNm + Ctry fails the Nov 2026 rule."""
    address = (
        "<Ntry><NtryDtls><TxDtls><RltdPties><Cdtr>"
        "<PstlAdr>"
        "<AdrLine>123 High Street</AdrLine>"
        "<AdrLine>London W1A 1AA</AdrLine>"
        "</PstlAdr>"
        "</Cdtr></RltdPties></TxDtls></NtryDtls></Ntry>"
    )
    result = check_cbpr_readiness(_wrap(address))
    assert result["cbpr_ready"] is False
    assert result["summary"]["unstructured_only"] == 1
    issue = next(
        i for i in result["issues"] if i["code"] == "UNSTRUCTURED_ONLY_ADDRESS"
    )
    assert issue["severity"] == "error"
    assert "2026-11-16" in issue["message"]
    assert "PstlAdr" in issue["path"]


def test_address_with_adrline_and_only_town_is_still_unstructured_only() -> (
    None
):
    """Town without country is treated as unstructured-only (both required)."""
    address = (
        "<Ntry><NtryDtls><TxDtls><RltdPties><Cdtr>"
        "<PstlAdr>"
        "<AdrLine>Some street</AdrLine>"
        "<TwnNm>Berlin</TwnNm>"
        "</PstlAdr>"
        "</Cdtr></RltdPties></TxDtls></NtryDtls></Ntry>"
    )
    result = check_cbpr_readiness(_wrap(address))
    assert result["cbpr_ready"] is False
    assert result["summary"]["unstructured_only"] == 1


def test_multiple_addresses_get_classified_independently() -> None:
    """One bad address among three structured ones still trips cbpr_ready."""
    addresses = (
        # Fully structured.
        "<Ntry><NtryDtls><TxDtls><RltdPties><Cdtr>"
        "<PstlAdr><TwnNm>Paris</TwnNm><Ctry>FR</Ctry></PstlAdr>"
        "</Cdtr></RltdPties></TxDtls></NtryDtls></Ntry>"
        # Hybrid.
        "<Ntry><NtryDtls><TxDtls><RltdPties><Cdtr>"
        "<PstlAdr><AdrLine>Line</AdrLine>"
        "<TwnNm>Madrid</TwnNm><Ctry>ES</Ctry></PstlAdr>"
        "</Cdtr></RltdPties></TxDtls></NtryDtls></Ntry>"
        # Unstructured-only.
        "<Ntry><NtryDtls><TxDtls><RltdPties><Cdtr>"
        "<PstlAdr><AdrLine>Only line</AdrLine></PstlAdr>"
        "</Cdtr></RltdPties></TxDtls></NtryDtls></Ntry>"
    )
    result = check_cbpr_readiness(_wrap(addresses))
    summary = result["summary"]
    assert summary["addresses_checked"] == 3
    assert summary["fully_structured"] == 1
    assert summary["hybrid"] == 1
    assert summary["unstructured_only"] == 1
    assert result["cbpr_ready"] is False


def test_checked_at_is_iso_utc_z_format() -> None:
    """The checked_at timestamp is ISO 8601 with a trailing Z."""
    result = check_cbpr_readiness(_wrap(""))
    assert result["checked_at"].endswith("Z")
    # Format: YYYY-MM-DDTHH:MM:SSZ (20 chars)
    assert len(result["checked_at"]) == 20


def test_malformed_xml_raises_valueerror() -> None:
    """Non-well-formed XML surfaces a clear ValueError."""
    with pytest.raises(ValueError, match="well-formed"):
        check_cbpr_readiness("<Document>unclosed")


def test_doctype_payload_is_rejected_by_xml_guard() -> None:
    """A DOCTYPE in the payload is refused by the XML pre-flight guard."""
    xml = (
        "<?xml version='1.0'?>"
        "<!DOCTYPE bad [<!ENTITY x 'attack'>]>"
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08"/>'
    )
    with pytest.raises(XmlSecurityError):
        check_cbpr_readiness(xml)


def test_path_uses_xpath_style_indexing() -> None:
    """Address paths read like /BkToCstmrStmt[0]/Stmt[0]/Ntry[N]/.../PstlAdr[0]."""
    address = (
        "<Ntry><NtryDtls><TxDtls><RltdPties><Cdtr>"
        "<PstlAdr><AdrLine>Only line</AdrLine></PstlAdr>"
        "</Cdtr></RltdPties></TxDtls></NtryDtls></Ntry>"
    )
    result = check_cbpr_readiness(_wrap(address))
    issue = result["issues"][0]
    # The path should at least include Ntry, NtryDtls, TxDtls, and PstlAdr.
    assert "Ntry[0]" in issue["path"]
    assert "PstlAdr[0]" in issue["path"]
