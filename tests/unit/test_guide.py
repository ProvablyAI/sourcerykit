"""Tests for sourcerykit.handoff._guide."""

from sourcerykit.handoff._guide import default_instructions, field_descriptions


class TestFieldDescriptions:
    def test_returns_dict(self) -> None:
        result = field_descriptions()
        assert isinstance(result, dict)

    def test_dict_is_non_empty(self) -> None:
        assert len(field_descriptions()) > 0

    def test_all_values_are_strings(self) -> None:
        for key, value in field_descriptions().items():
            assert isinstance(key, str)
            assert isinstance(value, str)

    def test_contains_expected_fields(self) -> None:
        descriptions = field_descriptions()
        for expected in ("evaluate_url", "claims", "integration_api_key", "field_guide", "instructions"):
            assert expected in descriptions, f"'{expected}' missing from field_descriptions"


class TestDefaultInstructions:
    def test_returns_string(self) -> None:
        result = default_instructions()
        assert isinstance(result, str)

    def test_string_is_non_empty(self) -> None:
        assert len(default_instructions()) > 0

    def test_mentions_evaluate_url(self) -> None:
        assert "evaluate_url" in default_instructions()

    def test_deterministic(self) -> None:
        assert default_instructions() == default_instructions()
