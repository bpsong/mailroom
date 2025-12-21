"""Helpers for parsing and normalizing query parameters."""

from typing import Optional, Tuple, Union

from fastapi import HTTPException, status


TRUE_VALUES = {"true", "1", "yes", "on"}
FALSE_VALUES = {"false", "0", "no", "off"}


def normalize_optional_bool_param(
    value: Optional[Union[str, bool]],
    *,
    param_name: str = "value",
) -> Tuple[Optional[bool], Optional[str]]:
    """
    Convert optional boolean-like query parameter strings to bools.
    
    Args:
        value: Raw query parameter value (string, bool, or None)
        param_name: Human-friendly parameter name for error messages
        
    Returns:
        Tuple of (parsed bool or None, normalized string or None)
    """
    if value is None:
        return None, None
    
    if isinstance(value, bool):
        return value, "true" if value else "false"
    
    stripped = value.strip()
    if stripped == "":
        return None, None
    
    lowered = stripped.lower()
    if lowered in TRUE_VALUES:
        return True, "true"
    if lowered in FALSE_VALUES:
        return False, "false"
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid {param_name} value. Expected true or false.",
    )

