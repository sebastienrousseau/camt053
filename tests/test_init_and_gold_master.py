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

"""Package-level smoke tests and a parse -> reverse gold-master check."""

import os
from importlib.resources import files

import pytest

import camt053
from camt053.constants import REVERSAL_MESSAGE_TYPE, valid_xml_types
from camt053.xml.validate_via_xsd import validate_xml_string_via_xsd

GOLD = os.path.join(os.path.dirname(__file__), "gold_master")
XSD = os.path.join(
    os.path.dirname(__file__),
    "..",
    "camt053",
    "templates",
    REVERSAL_MESSAGE_TYPE,
    f"{REVERSAL_MESSAGE_TYPE}.xsd",
)


def test_version_and_exports():
    """The package exposes its version and headline API."""
    assert camt053.__version__ == "0.0.4"
    assert callable(camt053.parse_document)
    assert callable(camt053.generate_reversal_for_statement)


def test_py_typed_marker_ships():
    """The PEP 561 ``py.typed`` marker ships with the package."""
    assert files("camt053").joinpath("py.typed").is_file()


def test_constants():
    """The supported types and reversal type are consistent."""
    assert REVERSAL_MESSAGE_TYPE in valid_xml_types
    assert len(valid_xml_types) == 3


@pytest.mark.smoke
def test_gold_master_statement_reverses_and_validates():
    """The bundled gold-master statement reverses to XSD-valid XML."""
    with open(os.path.join(GOLD, "statement_ac04.xml"), encoding="utf-8") as f:
        xml = f.read()
    stmt = camt053.parse_statement(xml)
    reversal = camt053.generate_reversal_for_statement(stmt, "AC04")
    assert validate_xml_string_via_xsd(reversal, XSD)
    # The reversing entry flips the credit transfer into a debit return.
    assert reversal.count("<RvslInd>true</RvslInd>") == 1
    assert "<CdtDbtInd>DBIT</CdtDbtInd>" in reversal
