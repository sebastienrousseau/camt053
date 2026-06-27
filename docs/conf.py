"""Sphinx configuration for camt053 documentation."""

import os
import sys

# Make the camt053 package importable for autodoc without an editable install,
# so the docs build (CI) can rely on hash-pinned dependencies only.
sys.path.insert(0, os.path.abspath(".."))

project = "camt053"
copyright = "2026, Sebastien Rousseau"
author = "Sebastien Rousseau"
release = "0.0.5"

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
