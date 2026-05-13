"""JSON helpers for stable, comparable serialization of claim values."""

from __future__ import annotations

import json
from typing import Any


def canonical_json(value: Any) -> str:
    """Return a deterministic JSON string (sorted keys, non-ASCII preserved) for equality checks."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False)
