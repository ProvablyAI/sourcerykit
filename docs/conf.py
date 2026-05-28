"""Sphinx configuration for provably-sdk."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("AGENTKIT_API_KEY", "dummy")
os.environ.setdefault("AGENTKIT_ORG_ID", "123e4567-e89b-12d3-a456-426614174000")
os.environ.setdefault("AGENTKIT_POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/db")

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
    "sphinx.ext.githubpages",
    "sphinxcontrib.mermaid",
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

html_theme = "sphinx_rtd_theme"

autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
}
autodoc_member_order = "bysource"
