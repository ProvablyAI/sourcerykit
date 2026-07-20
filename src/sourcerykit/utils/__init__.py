"""Utility helpers for SourceryKit."""

import json
from typing import Any

from sourcerykit.utils import validation


def extract_actual(raw_response: str | None, claimed_value: str | None) -> dict[str, Any]:
    """Extract actual values from stored raw_response for each claimed path."""
    from sourcerykit.evaluator._eval_modes import _get_by_json_path

    if not raw_response:
        return {}
    try:
        data = json.loads(raw_response)
    except (json.JSONDecodeError, TypeError):
        return {}

    if not claimed_value:
        return {}
    try:
        pairs = json.loads(claimed_value) if isinstance(claimed_value, str) else claimed_value
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(pairs, list) or not pairs:
        return {}

    result: dict[str, Any] = {}
    for entry in pairs:
        path = entry.get("path", "$") if isinstance(entry, dict) else "$"
        try:
            result[path] = _get_by_json_path(data, path)
        except (KeyError, IndexError, TypeError):
            result[path] = None
    return result


__all__ = ["validation", "extract_actual"]
