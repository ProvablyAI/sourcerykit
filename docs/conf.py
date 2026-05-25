"""Sphinx configuration for provably-sdk."""

from __future__ import annotations

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

project = "provably-sdk"
copyright = "Provably Technologies Ltd"
author = "Provably Technologies Ltd"

try:
    from importlib.metadata import version as pkg_version

    release = pkg_version("provably-sdk")
except Exception:
    release = "0.0.0"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
]

templates_path = []
exclude_patterns = ["_build", "historical-plans", "README.md"]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

myst_heading_anchors = 3

# README / CHANGELOG / CONTEXT live outside docs/; links use ../ paths.
suppress_warnings = ["myst.xref_missing"]

html_theme = "alabaster"

autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
}
autodoc_member_order = "bysource"
