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

    sourcerykit_ref: str = Field(
        default="",
        description=(
            "Unique reference to the specific tool call this claim is about. "
            "Must be copied exactly from the tool's sourcerykit_ref return value. "
            "Each tool call returns a unique sourcerykit_ref — you must use the one "
            "that corresponds to the tool call you are claiming about."
        ),
    )


class SourceryKitAgentResponse(BaseModel):
    answer: str = Field(description="Human-readable conversational explanation of the result.")

    claimed_values: list[ClaimedValue] = Field(
        description=(
            "A flat list of extracted values from tool outputs. "
            "Each item contains a JSONPath ('path') pointing to the source field, "
            "the corresponding extracted value as a string ('value'), "
            "and a 'sourcerykit_ref' copied exactly from the tool output. "
            "The sourcerykit_ref is MANDATORY — do not leave it empty."
        )
    )
