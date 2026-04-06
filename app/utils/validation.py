"""Shared validation helpers."""

import re


EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def is_valid_email(email: str) -> bool:
    """Return True when the provided email matches the application's format rules."""
    return bool(EMAIL_PATTERN.match(email))
