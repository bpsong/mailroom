"""Unit tests for settings provider behavior and isolation."""

from app.config import clear_settings_cache, get_settings, settings


class TestSettingsProvider:
    """Validate cached settings provider semantics."""

    def test_get_settings_returns_cached_instance(self, monkeypatch):
        """Provider should return the same instance while cache is warm."""
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-cache-check")
        monkeypatch.setenv("APP_ENV", "testing")

        clear_settings_cache()
        first = get_settings()
        second = get_settings()

        assert first is second

    def test_clear_settings_cache_reloads_env_values(self, monkeypatch):
        """Cache clear should make new environment values visible."""
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-reload")
        monkeypatch.setenv("APP_ENV", "testing")
        monkeypatch.setenv("DATABASE_PATH", "./data/test_first.duckdb")

        clear_settings_cache()
        first = get_settings()
        assert first.database_path == "./data/test_first.duckdb"

        monkeypatch.setenv("DATABASE_PATH", "./data/test_second.duckdb")
        second_without_clear = get_settings()
        assert second_without_clear.database_path == "./data/test_first.duckdb"

        clear_settings_cache()
        second_with_clear = get_settings()
        assert second_with_clear.database_path == "./data/test_second.duckdb"

    def test_legacy_settings_alias_is_immutable(self):
        """Backward-compatible alias should reject mutation attempts."""
        try:
            settings.database_path = "./data/forbidden.duckdb"
            raised = False
        except AttributeError:
            raised = True

        assert raised is True

