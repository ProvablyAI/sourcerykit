from enum import StrEnum


class VerificationMode(StrEnum):
    """How a claim's claimed_value is compared against the indexed query record."""

    VERBATIM = "verbatim"
    FIELD_EXTRACTION = "field_extraction"
    SCHEMA_TYPE = "schema_type"
    RANGE_THRESHOLD = "range_threshold"
