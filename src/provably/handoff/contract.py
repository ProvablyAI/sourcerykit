"""Build the LLM-facing JSON contract for emitting :class:`HandoffClaim` claims.

This is the *prompt-time* counterpart to :mod:`provably.handoff.guide`: ``guide``
describes a payload to a *receiving* agent, while ``contract`` describes the
per-claim JSON the *sending* agent must emit so its claims can be lifted into
:class:`HandoffClaim` without manual reshaping.

The shape and rules below are derived from :class:`HandoffClaim` and
:data:`VerificationMode` so the prompt cannot drift from the wire model.
Deployments layer their own action-name allow-list and tone notes on top
via the keyword arguments to :func:`claim_contract`.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import get_args

from provably.handoff.types import HandoffClaim, VerificationMode

__all__ = ["claim_contract"]


_CLAIM_FIELDS_FOR_LLM: tuple[tuple[str, str], ...] = (
    ("action_name", "string"),
    ("claimed_value", "object"),
    ("verification_mode", " | ".join(f'"{m}"' for m in get_args(VerificationMode))),
    ("json_path", "string"),
    ("expected_json_schema", "object | null"),
    ("range_min", "number | null"),
    ("range_max", "number | null"),
)

_unknown_claim_fields = {n for n, _ in _CLAIM_FIELDS_FOR_LLM} - set(HandoffClaim.model_fields)
if _unknown_claim_fields:  # pragma: no cover - drift guard
    raise RuntimeError(
        f"claim_contract drift: {_unknown_claim_fields} not present on HandoffClaim"
    )


_MODE_RULES: dict[str, str] = {
    "verbatim": "For verbatim: claimed_value must equal the full indexed payload.",
    "field_extraction": (
        "For field_extraction: set json_path; claimed_value is the value at that path."
    ),
    "schema_type": (
        "For schema_type: set json_path and expected_json_schema; "
        "claimed_value may be a concise summary."
    ),
    "range_threshold": (
        "For range_threshold: set json_path and range_min and/or range_max for numeric bounds."
    ),
}

_missing_modes = set(get_args(VerificationMode)) - set(_MODE_RULES)
if _missing_modes:  # pragma: no cover - drift guard
    raise RuntimeError(f"claim_contract drift: {_missing_modes} missing from _MODE_RULES")


_SYSTEM_FIELDS_NOTE = (
    "Do not include query_record_id, request_payload, response_payload, or proof "
    "identifiers; those are added by the system."
)


def claim_contract(
    *,
    action_names: Iterable[str] | None = None,
    wrapper_fields: dict[str, str] | None = None,
    extra_rules: Iterable[str] | None = None,
) -> str:
    """Render the LLM JSON contract for emitting :class:`HandoffClaim` claims.

    Args:
        action_names: When provided, the contract restricts ``action_name`` to these
            values. When ``None``, no allow-list rule is added.
        wrapper_fields: Extra top-level keys the LLM must emit alongside ``claims``;
            keys are field names, values are JSON type descriptions
            (e.g. ``{"reasoning": "string"}``). Pass ``None`` for a claims-only response.
        extra_rules: Deployment-specific rule lines appended after the SDK rules.

    Returns:
        A system-prompt string describing the required JSON shape and rules.
    """
    claim_body = ",\n    ".join(f'"{name}": {ty}' for name, ty in _CLAIM_FIELDS_FOR_LLM)
    wrapper_text = "".join(f'"{k}": {v}, ' for k, v in (wrapper_fields or {}).items())
    shape = (
        f'{{{wrapper_text}"claims": [\n'
        "  {\n"
        f"    {claim_body}\n"
        "  }\n"
        "]}"
    )

    lines: list[str] = [
        "You reply with a single JSON object only (no markdown fences). Shape:",
        shape,
        "Rules:",
    ]
    lines.extend(f"- {_MODE_RULES[mode]}" for mode in get_args(VerificationMode))
    lines.append(f"- {_SYSTEM_FIELDS_NOTE}")
    if action_names is not None:
        names = ", ".join(action_names)
        lines.append(f"- action_name must be one of: {names}.")
    if extra_rules:
        lines.extend(f"- {rule}" for rule in extra_rules)
    return "\n".join(lines)
