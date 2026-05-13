"""Tests for targeted security remediation helpers."""

from app.services.export_service import neutralize_csv_formula
from app.services.system_settings_service import system_settings_service


def test_neutralize_csv_formula_prefixes_formula_like_values():
    assert neutralize_csv_formula("=cmd|calc!A0") == "'=cmd|calc!A0"
    assert neutralize_csv_formula("+SUM(A1:A2)") == "'+SUM(A1:A2)"
    assert neutralize_csv_formula("  @malicious") == "'  @malicious"


def test_neutralize_csv_formula_leaves_safe_values_unchanged():
    assert neutralize_csv_formula("TRACK-123") == "TRACK-123"
    assert neutralize_csv_formula("") == ""
    assert neutralize_csv_formula(None) is None


def test_qr_base_url_validation_requires_http_url_with_host():
    assert system_settings_service.validate_base_url("https://mailroom.example.test") is True
    assert system_settings_service.validate_base_url("http://localhost:8000") is True
    assert system_settings_service.validate_base_url("javascript:alert(1)") is False
    assert system_settings_service.validate_base_url("https://") is False
    assert system_settings_service.validate_base_url("https://user:pass@example.test") is False
