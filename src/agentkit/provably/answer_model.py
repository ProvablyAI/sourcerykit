"""Data validation and serialization contracts for the Rust API layers."""

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

__all__ = ["QueryAnswer", "TabularData", "AggregateAnswer", "ResultsetAnswer"]


def _safe_deserialize(cell: Any) -> Any:
    """Helper to cleanly parse stringified JSON containers if serialized."""
    if isinstance(cell, str) and cell.strip().startswith(("{", "[")):
        try:
            return json.loads(cell)
        except json.JSONDecodeError:
            return cell
    return cell


class TabularData(BaseModel):
    columns: list[dict[str, Any]] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)

    def extract_value(self) -> Any:
        """Unpacks tabular results down to the core target payload."""
        if not self.rows or not self.rows:
            return self.model_dump()

        row0 = self.rows
        # Extracted column names are normalized to lowercase
        col_names = [str(c.get("name") or "").lower() for c in self.columns]

        # Target 1: Extract intercept record payloads cleanly if present
        if "raw_response" in col_names:
            return _safe_deserialize(row0[col_names.index("raw_response")])

        # Target 2: Single cell scalar fallbacks
        if len(col_names) == 1 and len(row0) == 1:
            return _safe_deserialize(row0)

        return self.model_dump()


class AggregateAnswer(BaseModel):
    type: Literal["aggregate"]
    value: str

    def extract_value(self) -> Any:
        return _safe_deserialize(self.value)


class ResultsetAnswer(BaseModel):
    type: Literal["resultset"]
    value: TabularData

    def extract_value(self) -> Any:
        return self.value.extract_value()


class QueryAnswer(BaseModel):
    """Wrapper mapping the structure of QueryAnswer enum."""

    root: AggregateAnswer | ResultsetAnswer = Field(..., discriminator="type")

    @model_validator(mode="before")
    @classmethod
    def wrap_root(cls, data: Any) -> Any:
        if isinstance(data, dict) and "root" not in data:
            return {"root": data}
        return data

    def flatten(self) -> Any:
        return self.root.extract_value()
