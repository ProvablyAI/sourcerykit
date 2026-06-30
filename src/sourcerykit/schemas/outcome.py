from enum import StrEnum


class Outcome(StrEnum):
    """Final verdict for a handoff evaluation."""

    PASS = "PASS"
    CAUGHT = "CAUGHT"
    ERROR = "ERROR"
