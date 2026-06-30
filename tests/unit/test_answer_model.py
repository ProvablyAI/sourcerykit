"""Tests for sourcerykit.provably._answer_model."""

import pytest
from pydantic import ValidationError

from sourcerykit.provably._answer_model import AggregateAnswer, QueryAnswer, ResultsetAnswer, TabularData

# ---------------------------------------------------------------------------
# TabularData
# ---------------------------------------------------------------------------


class TestTabularData:
    def test_empty_rows_returns_dict(self) -> None:
        td = TabularData(columns=[{"name": "col1"}], rows=[])
        result = td.extract_value()
        assert isinstance(result, dict)
        assert result["rows"] == []

    def test_single_cell_scalar_returned(self) -> None:
        td = TabularData(columns=[{"name": "score"}], rows=[[42]])
        result = td.extract_value()
        assert result == 42

    def test_raw_response_column_parsed_as_json(self) -> None:
        td = TabularData(
            columns=[{"name": "raw_response"}],
            rows=[['{"status": "ok", "value": 1}']],
        )
        result = td.extract_value()
        assert result == {"status": "ok", "value": 1}

    def test_raw_response_non_json_string_returned_as_is(self) -> None:
        td = TabularData(
            columns=[{"name": "raw_response"}],
            rows=[["plain string"]],
        )
        result = td.extract_value()
        assert result == "plain string"

    def test_multi_column_returns_full_tabular_dict(self) -> None:
        td = TabularData(
            columns=[{"name": "a"}, {"name": "b"}],
            rows=[[1, 2]],
        )
        result = td.extract_value()
        assert result == {"columns": [{"name": "a"}, {"name": "b"}], "rows": [[1, 2]]}


# ---------------------------------------------------------------------------
# AggregateAnswer
# ---------------------------------------------------------------------------


class TestAggregateAnswer:
    def test_extract_value_returns_string(self) -> None:
        aa = AggregateAnswer(type="aggregate", value="100")
        assert aa.extract_value() == "100"

    def test_extract_value_parses_json_string(self) -> None:
        aa = AggregateAnswer(type="aggregate", value='{"key": "val"}')
        result = aa.extract_value()
        assert result == {"key": "val"}

    def test_type_must_be_aggregate(self) -> None:
        with pytest.raises(ValidationError):
            AggregateAnswer(type="other", value="x")  # pyright: ignore[reportArgumentType]


# ---------------------------------------------------------------------------
# ResultsetAnswer
# ---------------------------------------------------------------------------


class TestResultsetAnswer:
    def test_extract_value_delegates_to_tabular(self) -> None:
        rs = ResultsetAnswer(
            type="resultset",
            value=TabularData(columns=[{"name": "score"}], rows=[[99]]),
        )
        assert rs.extract_value() == 99


# ---------------------------------------------------------------------------
# QueryAnswer
# ---------------------------------------------------------------------------


class TestQueryAnswer:
    def test_flatten_aggregate(self) -> None:
        qa = QueryAnswer.model_validate({"type": "aggregate", "value": "42"})
        assert qa.flatten() == "42"

    def test_flatten_resultset_single_cell(self) -> None:
        qa = QueryAnswer.model_validate(
            {
                "type": "resultset",
                "value": {
                    "columns": [{"name": "count"}],
                    "rows": [[7]],
                },
            }
        )
        assert qa.flatten() == 7

    def test_model_validate_wraps_root_automatically(self) -> None:
        """wrap_root validator: top-level dict without 'root' key is wrapped."""
        qa = QueryAnswer.model_validate({"type": "aggregate", "value": "x"})
        assert qa.root is not None

    def test_invalid_type_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            QueryAnswer.model_validate({"type": "unknown", "value": "x"})
