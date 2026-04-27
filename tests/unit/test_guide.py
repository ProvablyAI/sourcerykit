from __future__ import annotations

from provably.handoff.guide import (
    DEFAULT_INSTRUCTIONS,
    FIELD_DESCRIPTIONS,
    FIELD_DESCRIPTIONS_OFF,
    PROVABLY_OFF_NOTE,
    default_instructions,
    field_descriptions,
)


def test_field_descriptions_on_returns_neutral_set() -> None:
    guide = field_descriptions(provably_indexing=True)
    assert set(FIELD_DESCRIPTIONS).issubset(guide.keys())
    for key in FIELD_DESCRIPTIONS_OFF:
        assert guide[key] == FIELD_DESCRIPTIONS[key]


def test_field_descriptions_off_merges_overrides() -> None:
    guide = field_descriptions(provably_indexing=False)
    for key, off_text in FIELD_DESCRIPTIONS_OFF.items():
        assert guide[key] == off_text


def test_field_descriptions_returns_fresh_copy() -> None:
    a = field_descriptions(provably_indexing=True)
    a["claims"] = "MUTATED"
    b = field_descriptions(provably_indexing=True)
    assert b["claims"] != "MUTATED"


def test_default_instructions_on_no_caveat() -> None:
    assert default_instructions(provably_indexing=True) == DEFAULT_INSTRUCTIONS


def test_default_instructions_off_appends_caveat() -> None:
    text = default_instructions(provably_indexing=False)
    assert text.startswith(DEFAULT_INSTRUCTIONS)
    assert text.endswith(PROVABLY_OFF_NOTE)


def test_default_instructions_is_neutral_no_named_agents() -> None:
    """The SDK default must not name Cluster A / Cluster B; consumers add personas."""
    assert "Cluster A" not in DEFAULT_INSTRUCTIONS
    assert "Cluster B" not in DEFAULT_INSTRUCTIONS
