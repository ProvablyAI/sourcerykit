"""Sphinx configuration"""

from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path

os.environ.setdefault("AGENTKIT_API_KEY", "dummy")
os.environ.setdefault("AGENTKIT_ORG_ID", "123e4567-e89b-12d3-a456-426614174000")
os.environ.setdefault("AGENTKIT_POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/db")

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

project = "SourceryKit"
copyright = "Provably Technologies Ltd"
author = "Provably Technologies Ltd"

try:
    from importlib.metadata import version as pkg_version

    release = pkg_version("sourcerykit")
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

myst_enable_extensions = [
    "alert",
    "colon_fence",
]

myst_fence_as_directive = {"mermaid"}

# README / CHANGELOG / CONTEXT live outside docs/; links use ../ paths.
suppress_warnings = ["myst.xref_missing"]

html_theme = "sphinx_rtd_theme"

autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
}
autodoc_member_order = "bysource"

# (Provably Description)
REMOTE_MD_URL = "https://raw.githubusercontent.com/ProvablyAI/.github/refs/heads/main/profile/README.md"
LOCAL_MD_PATH = Path(__file__).resolve().parent / "src/provably.md"


def download_remote_description() -> None:
    print(f"--> Fetching {REMOTE_MD_URL}")
    try:
        with urllib.request.urlopen(REMOTE_MD_URL, timeout=10) as response:
            content = response.read().decode("utf-8")

        front = "# \n ## \n"

        LOCAL_MD_PATH.write_text(front + content, encoding="utf-8")
        print("--> Remote description synced successfully.")

    except Exception as e:
        print(f"--> Warning: Failed to fetch remote markdown: {e}")
        if not LOCAL_MD_PATH.exists():
            LOCAL_MD_PATH.write_text("Provably", encoding="utf-8")


download_remote_description()
