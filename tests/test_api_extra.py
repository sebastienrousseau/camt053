"""The REST stack is the ``api`` extra, not a base dependency.

``pip install camt053`` parses, validates and generates without fastapi,
starlette, pydantic or uvicorn; ``camt053.api`` names the extra when it
is missing.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "tests" / "gold_master" / "business_sample_camt.053.001.04.xml"
WEB_STACK = ("fastapi", "starlette", "pydantic", "uvicorn")

_WITHOUT_WEB_STACK = """
import sys
for name in {stack!r}:
    sys.modules[name] = None  # import of it raises ImportError
import camt053
doc = camt053.parse_document(open({sample!r}, encoding="utf-8").read())
loaded = sorted(n for n in {stack!r} if sys.modules.get(n) is not None)
print(doc.message_type, len(doc.all_entries()), loaded)
"""


def test_the_base_install_parses_without_the_web_stack() -> None:
    """With fastapi, starlette, pydantic and uvicorn unimportable."""
    code = _WITHOUT_WEB_STACK.format(stack=WEB_STACK, sample=str(SAMPLE))
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split()[0].startswith("camt.053")
    assert result.stdout.strip().endswith("[]")


def test_the_api_names_its_extra_when_fastapi_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "fastapi", None)
    monkeypatch.delitem(sys.modules, "camt053.api", raising=False)
    monkeypatch.delitem(sys.modules, "camt053.api.app", raising=False)
    with pytest.raises(ImportError, match=r"pip install 'camt053\[api\]'"):
        importlib.import_module("camt053.api")


def test_the_web_stack_is_optional_and_in_the_api_extra() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        poetry = tomllib.load(handle)["tool"]["poetry"]
    deps, api = poetry["dependencies"], set(poetry["extras"]["api"])
    for name in (*WEB_STACK, "httpx"):
        assert deps[name]["optional"] is True, name
        assert name in api, name
