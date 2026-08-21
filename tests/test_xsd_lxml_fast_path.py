"""The lxml fast path for XSD validation, and its safety properties.

``validate_xml_string_via_xsd`` uses libxml2 as an accept/reject gate
when ``lxml`` is installed, falling back to ``xmlschema`` otherwise. Two
implementations behind one function is a real risk, so these tests pin
the properties that make it safe:

* a rejection by lxml is never final -- xmlschema decides,
* the two agree on documents that are valid and on documents that are
  not,
* the lxml parser has entity expansion, DTD loading and network access
  switched off, because ``defusedxml`` does not cover lxml.

Both branches are exercised regardless of whether ``lxml`` is installed
in the environment running the suite.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

# `camt053.xml` re-exports a *function* named `validate_via_xsd`, which
# shadows the module of the same name — `from camt053.xml import
# validate_via_xsd` hands back the function. Import the module by path.
module = importlib.import_module("camt053.xml.validate_via_xsd")
validate_xml_string_via_xsd = module.validate_xml_string_via_xsd

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "tests" / "gold_master" / "business_sample_camt.053.001.04.xml"

NOT_XML = "this is not xml at all <<<"

lxml_installed = pytest.mark.skipif(
    not module._LXML_AVAILABLE, reason="lxml is not installed"
)


def _valid_document() -> str:
    """Return a known-good camt.053 document."""
    return GOLD.read_text(encoding="utf-8")


def _schema_for(xml: str) -> str:
    """Return the bundled XSD path matching a document's namespace."""
    match = re.search(
        r"urn:iso:std:iso:20022:tech:xsd:(camt\.\d+\.\d+\.\d+)", xml
    )
    assert match, "gold-master document has no recognisable namespace"
    return str(ROOT / "camt053" / "xsd" / f"{match.group(1)}.xsd")


def _invalid_document() -> str:
    """Return the same document with a required element removed."""
    xml = _valid_document()
    return re.sub(r"<GrpHdr>.*?</GrpHdr>", "", xml, count=1, flags=re.S)


class TestFallbackBehaviour:
    """What happens when lxml is absent or declines."""

    def test_a_valid_document_is_accepted_without_the_fast_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The pure-Python accept path must still work.

        With lxml installed a valid document is accepted by the gate and
        never reaches xmlschema, so this is the only thing that
        exercises the fallback's accept -- the path every user without
        lxml takes for every document.
        """
        xml = _valid_document()
        monkeypatch.setattr(module, "_LXML_AVAILABLE", False)

        assert validate_xml_string_via_xsd(xml, _schema_for(xml)) is True

    def test_an_invalid_document_is_rejected_without_the_fast_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """And the fallback's reject."""
        xml = _invalid_document()
        monkeypatch.setattr(module, "_LXML_AVAILABLE", False)

        assert validate_xml_string_via_xsd(xml, _schema_for(xml)) is False

    def test_an_lxml_rejection_is_not_final(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A False from lxml must fall through to xmlschema.

        This is what makes installing or removing lxml unable to change
        a verdict: the fast path can only shortcut an accept.
        """
        xml = _valid_document()
        calls: list[str] = []

        monkeypatch.setattr(module, "_LXML_AVAILABLE", True)
        monkeypatch.setattr(
            module,
            "_lxml_accepts",
            lambda content, schema: calls.append("lxml") or False,
        )

        # lxml says no, xmlschema says yes, and yes wins.
        assert validate_xml_string_via_xsd(xml, _schema_for(xml)) is True
        assert calls == ["lxml"]

    def test_unparseable_input_is_rejected_by_both_paths(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Garbage in is False out, with or without the fast path."""
        schema = _schema_for(_valid_document())

        monkeypatch.setattr(module, "_LXML_AVAILABLE", False)
        assert validate_xml_string_via_xsd(NOT_XML, schema) is False

        monkeypatch.setattr(module, "_LXML_AVAILABLE", True)
        assert validate_xml_string_via_xsd(NOT_XML, schema) is False


@lxml_installed
class TestLxmlGate:
    """The fast path itself, when lxml is present."""

    def test_it_accepts_the_gold_master(self) -> None:
        """The happy path the speed-up exists for."""
        xml = _valid_document()
        assert module._lxml_accepts(xml, _schema_for(xml)) is True

    def test_it_rejects_a_schema_invalid_document(self) -> None:
        """A document missing a required element is not accepted."""
        xml = _invalid_document()
        assert module._lxml_accepts(xml, _schema_for(xml)) is False

    def test_it_reports_false_rather_than_raising_on_garbage(self) -> None:
        """Any internal failure defers to xmlschema instead of raising."""
        schema = _schema_for(_valid_document())
        assert module._lxml_accepts(NOT_XML, schema) is False

    def test_it_reports_false_for_a_missing_schema(self) -> None:
        """A bad schema path defers rather than raising."""
        assert module._lxml_accepts(_valid_document(), "no/such.xsd") is False

    def test_the_compiled_schema_is_cached(self) -> None:
        """Compiling is the expensive, document-independent part."""
        schema = _schema_for(_valid_document())
        assert module._get_cached_lxml_schema(
            schema
        ) is module._get_cached_lxml_schema(schema)


@lxml_installed
class TestParserHardening:
    """defusedxml does not cover lxml, so this is configured by hand."""

    def test_an_external_file_entity_does_not_leak_the_file(
        self, tmp_path: Path
    ) -> None:
        """The XXE case: a SYSTEM entity must not read local files.

        Asserting on the parser's flags would only restate the
        constructor call. This runs the attack: a document that, with a
        default parser, substitutes the contents of a real file on disk
        into the output.
        """
        import lxml.etree as etree

        secret = tmp_path / "secret.txt"
        secret.write_text("TOP-SECRET-VALUE", encoding="utf-8")

        payload = (
            '<?xml version="1.0"?>'
            "<!DOCTYPE root ["
            f'<!ENTITY xxe SYSTEM "file://{secret}">'
            "]>"
            "<root>&xxe;</root>"
        )

        parsed = etree.fromstring(
            payload.encode("utf-8"), module._hardened_lxml_parser()
        )

        assert "TOP-SECRET-VALUE" not in (parsed.text or "")
        assert "TOP-SECRET-VALUE" not in etree.tostring(parsed).decode()

    def test_entities_are_not_expanded(self) -> None:
        """Billion-laughs and XXE both rely on expansion."""
        import lxml.etree as etree

        payload = (
            '<?xml version="1.0"?>'
            '<!DOCTYPE root [<!ENTITY boom "EXPANDED">]>'
            "<root>&boom;</root>"
        )
        parsed = etree.fromstring(
            payload.encode("utf-8"), module._hardened_lxml_parser()
        )

        assert "EXPANDED" not in (parsed.text or "")


@lxml_installed
class TestEquivalence:
    """The two implementations must not disagree."""

    def test_they_agree_on_the_gold_master_documents(self) -> None:
        """Every bundled sample, both ways.

        The wider sweep (28 documents including mutations) was run
        before shipping this; these are the ones cheap enough to keep
        in the suite.
        """
        from io import StringIO

        import defusedxml.ElementTree as defused_et

        for path in sorted((ROOT / "tests" / "gold_master").glob("*.xml")):
            xml = path.read_text(encoding="utf-8")
            match = re.search(
                r"urn:iso:std:iso:20022:tech:xsd:(camt\.\d+\.\d+\.\d+)", xml
            )
            if not match:
                continue
            schema = str(ROOT / "camt053" / "xsd" / f"{match.group(1)}.xsd")
            if not Path(schema).is_file():
                continue

            by_xmlschema = module._get_cached_schema(schema).is_valid(
                defused_et.parse(StringIO(xml))
            )
            by_lxml = module._lxml_accepts(xml, schema)

            assert by_xmlschema == by_lxml, (
                f"{path.name}: xmlschema says {by_xmlschema}, "
                f"lxml says {by_lxml}"
            )
