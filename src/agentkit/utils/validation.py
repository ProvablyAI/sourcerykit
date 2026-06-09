"""Simple input validators for user-provided fields."""


def validate_length(field_name: str, value: str | None, max_len: int = 255, allow_none: bool = False) -> None:
    """Raise ValueError if ``value`` violates length constraints."""
    if value is None:
        if allow_none:
            return
        raise ValueError(f"{field_name} is required")

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    if not value:
        if allow_none:
            return
        raise ValueError(f"{field_name} must be a non-empty string")

    if len(value) > max_len:
        raise ValueError(f"{field_name} must be at most {max_len} characters")
