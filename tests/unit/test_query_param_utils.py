"""Tests for query parameter helper utilities."""

import pytest
from fastapi import HTTPException

from app.utils.query_params import normalize_optional_bool_param


@pytest.mark.parametrize(
    "raw_value,expected",
    [
        (None, (None, None)),
        ("", (None, None)),
        ("   ", (None, None)),
        ("true", (True, "true")),
        ("TRUE", (True, "true")),
        ("false", (False, "false")),
        ("False", (False, "false")),
        ("1", (True, "true")),
        ("0", (False, "false")),
        ("yes", (True, "true")),
        ("no", (False, "false")),
        (True, (True, "true")),
        (False, (False, "false")),
    ],
)
def test_normalize_optional_bool_param_valid_inputs(raw_value, expected):
    """Valid inputs should return the expected tuple."""
    assert normalize_optional_bool_param(raw_value, param_name="is_active") == expected


def test_normalize_optional_bool_param_invalid_input():
    """Invalid values should raise an HTTPException."""
    with pytest.raises(HTTPException) as exc:
        normalize_optional_bool_param("maybe", param_name="is_active")
    
    assert exc.value.status_code == 400
    assert "is_active" in exc.value.detail

