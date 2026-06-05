from pydantic import BaseModel, Field


class ClaimedValue(BaseModel):
    path: str = Field(
        description=(
            "JSONPath-style key identifying where the value came from in the tool output. "
            "Must be a flat string path like '$.path.field'. "
        )
    )

    value: str = Field(
        description=(
            "Raw extracted value as a string. Must be the direct value from tool output converted to string if needed."
        )
    )


class SourceryKitAgentResponse(BaseModel):
    reasoning: str = Field(description="Human-readable conversational explanation of the result.")

    claimed_values: list[ClaimedValue] = Field(
        description=(
            "A flat list of extracted values from tool outputs. "
            "Each item contains a JSONPath ('path') pointing to the source field "
            "and the corresponding extracted value as a string ('value'). "
        )
    )
