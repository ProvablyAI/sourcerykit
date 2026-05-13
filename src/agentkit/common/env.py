"""Tiny wrappers around :func:`os.getenv` that normalize whitespace and trailing slashes."""

from __future__ import annotations

import os


def get_env_str(name: str, default: str = "") -> str:
    """Return env var ``name`` stripped of surrounding whitespace, or ``default`` if unset."""
    return (os.getenv(name) or default).strip()


def get_env_url_base(name: str, default: str = "") -> str:
    """Return an env-sourced base URL with any trailing ``/`` removed for safe path concatenation."""
    return get_env_str(name, default).rstrip("/")
