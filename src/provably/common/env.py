from __future__ import annotations

import os


def get_env_str(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def get_env_url_base(name: str, default: str = "") -> str:
    return get_env_str(name, default).rstrip("/")
