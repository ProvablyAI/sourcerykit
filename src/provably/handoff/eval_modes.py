"""Per-claim evaluation for each HandoffClaim verification_mode."""

from __future__ import annotations

import math
from typing import Any

import jsonschema

from provably.handoff.json_utils import canonical_json
from provably.handoff.types import HandoffClaim

__all__ = ["evaluate_claim"]


def evaluate_claim(claim: HandoffClaim, indexed_root: Any) -> dict[str, Any]:
    """Run ``claim.verification_mode`` against ``indexed_root``; see :data:`VerificationMode` for modes.

    ``indexed_root`` is the canonical indexed value from the Provably query record (already
    unwrapped via :func:`provably.handoff.evaluator.extract_indexed_from_query_record`).

    Returns a verdict dict with ``action_name``, ``verification_mode``, ``result`` (``"PASS"``
    or ``"CAUGHT"``), ``claimed``, ``indexed``, plus ``indexed_at_path`` for non-verbatim modes
    and ``detail`` when caught.
    """
    base = _base_verdict(claim, indexed_root)
    mode = claim.verification_mode

    if mode == "verbatim":
        return _eval_verbatim(claim, indexed_root, base)

    try:
        at_path = _get_by_json_path(indexed_root, claim.json_path)
    except (KeyError, TypeError) as exc:
        return {**base, "result": "CAUGHT", "detail": f"json_path: {exc}"}

    base["indexed_at_path"] = canonical_json(at_path)

    if mode == "field_extraction":
        return _eval_field_extraction(claim, at_path, base)
    if mode == "schema_type":
        return _eval_schema_type(claim, at_path, base)
    if mode == "range_threshold":
        return _eval_range_threshold(claim, at_path, base)
    return {**base, "result": "CAUGHT", "detail": f"unknown verification_mode: {mode}"}


def _base_verdict(claim: HandoffClaim, indexed_root: Any) -> dict[str, Any]:
    return {
        "action_name": claim.action_name,
        "verification_mode": claim.verification_mode,
        "claimed": canonical_json(claim.claimed_value),
        "indexed": canonical_json(indexed_root),
    }


def _eval_verbatim(claim: HandoffClaim, indexed_root: Any, base: dict[str, Any]) -> dict[str, Any]:
    ok = canonical_json(claim.claimed_value) == canonical_json(indexed_root)
    return {**base, "result": "PASS" if ok else "CAUGHT"}


def _eval_field_extraction(claim: HandoffClaim, at_path: Any, base: dict[str, Any]) -> dict[str, Any]:
    ok = canonical_json(claim.claimed_value) == canonical_json(at_path)
    return {**base, "result": "PASS" if ok else "CAUGHT"}


def _eval_schema_type(claim: HandoffClaim, at_path: Any, base: dict[str, Any]) -> dict[str, Any]:
    schema = claim.expected_json_schema
    if not schema:
        return {**base, "result": "CAUGHT", "detail": "expected_json_schema is required for schema_type"}
    try:
        jsonschema.validate(at_path, schema)
    except jsonschema.ValidationError as exc:
        return {**base, "result": "CAUGHT", "detail": exc.message}
    except jsonschema.SchemaError as exc:
        return {**base, "result": "CAUGHT", "detail": f"invalid schema: {exc}"}
    return {**base, "result": "PASS"}


def _eval_range_threshold(claim: HandoffClaim, at_path: Any, base: dict[str, Any]) -> dict[str, Any]:
    if claim.range_min is None and claim.range_max is None:
        return {**base, "result": "CAUGHT", "detail": "range_threshold requires range_min and/or range_max"}
    try:
        value = _coerce_number(at_path)
    except (TypeError, ValueError) as exc:
        return {**base, "result": "CAUGHT", "detail": f"indexed value not numeric: {exc}"}
    if claim.range_min is not None and value < float(claim.range_min):
        return {**base, "result": "CAUGHT", "detail": f"value {value} below range_min {claim.range_min}"}
    if claim.range_max is not None and value > float(claim.range_max):
        return {**base, "result": "CAUGHT", "detail": f"value {value} above range_max {claim.range_max}"}
    if not _numbers_match(claim.claimed_value, at_path):
        return {**base, "result": "CAUGHT", "detail": "claimed_value does not match indexed numeric at path"}
    return {**base, "result": "PASS"}


def _get_by_json_path(obj: Any, path: str) -> Any:
    cursor = obj
    for segment in (path or "").split("."):
        segment = segment.strip()
        if not segment:
            continue
        if not isinstance(cursor, dict):
            raise KeyError(f"expected dict at segment {segment!r}, got {type(cursor).__name__}")
        cursor = cursor[segment]
    return cursor


def _coerce_number(value: Any) -> float:
    if isinstance(value, bool):
        raise TypeError("boolean is not a numeric bound value")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value.strip())
    raise TypeError(f"not numeric: {type(value).__name__}")


def _numbers_match(a: Any, b: Any) -> bool:
    try:
        return math.isclose(_coerce_number(a), _coerce_number(b), rel_tol=0.0, abs_tol=1e-9)
    except (TypeError, ValueError):
        return False
