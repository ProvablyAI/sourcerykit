from enum import StrEnum


class VerificationMode(StrEnum):
    """How a claim's claimed_value is compared against the indexed query record."""

    FIELD_EXTRACTION = "field_extraction"
    RANGE_THRESHOLD = "range_threshold"
