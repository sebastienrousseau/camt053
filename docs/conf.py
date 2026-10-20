"""Sphinx configuration for camt053 documentation."""

import os
import re
import sys

# Make the camt053 package importable for autodoc without an editable install,
# so the docs build (CI) can rely on hash-pinned dependencies only.
sys.path.insert(0, os.path.abspath(".."))

project = "camt053"
# The year only: docs/_templates/copyright.html renders the
# footer as "© <year> Sebastien Rousseau", linked to the author's site.
copyright = "2026"
author = "Sebastien Rousseau"
# Read from pyproject.toml, the single source of the version, so the
# rendered manual cannot fall behind the package (it said 0.0.5 for
# fifteen releases).
with open(
    os.path.join(os.path.dirname(__file__), "..", "pyproject.toml"),
    encoding="utf-8",
) as _pyproject:
    release = re.search(
        r'^version = "([^"]+)"', _pyproject.read(), re.MULTILINE
    ).group(1)
version = release

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "myst_parser",
    "sphinx_design",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]

html_theme_options = {
    "github_url": "https://github.com/sebastienrousseau/camt053",
    "show_toc_level": 2,
}

autodoc_member_order = "bysource"
autodoc_typehints = "description"

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]
