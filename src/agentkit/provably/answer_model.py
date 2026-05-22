"""Data validation and serialization contracts for the Rust API layers."""

from typing import Any, Literal

import msgspec
from pydantic import BaseModel, Field, model_validator

from agentkit.logger import get_logger

_log = get_logger(__name__)

__all__ = ["QueryAnswer", "TabularData", "AggregateAnswer", "ResultsetAnswer"]


def _safe_deserialize(cell: Any) -> Any:
    """Helper to cleanly parse stringified JSON containers using high-speed C decoding."""
    if isinstance(cell, str) and cell.strip().startswith(("{", "[")):
        try:
            return msgspec.json.decode(cell)
        except Exception as e:
            _log.debug("safe_deserialize_fallback", error=str(e))
            return cell
    return cell


class TabularData(BaseModel):
    columns: list[dict[str, Any]] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)

    def extract_value(self) -> Any:
        """Unpacks tabular results down to the core target payload."""
        if not self.rows:
            return {"columns": self.columns, "rows": self.rows}

        row0 = self.rows[0]
        # Extracted column names are normalized to lowercase
        col_names = [str(c.get("name") or "").lower() for c in self.columns]

        # Target 1: Extract intercept record payloads cleanly if present
        if "raw_response" in col_names:
            return _safe_deserialize(row0[col_names.index("raw_response")])

        # Target 2: Single cell scalar
        if len(col_names) == 1 and len(row0) == 1:
            return _safe_deserialize(row0[0])

        return {"columns": self.columns, "rows": self.rows}


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
