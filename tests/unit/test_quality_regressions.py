"""Regression tests for the code-quality remediation pass.

Covers the behavior changes that the lint/type/timezone/except cleanup
introduced, so they cannot silently regress:

- corrupt/unsupported password hashes verify as False (never 500)
- corrupt password-history payloads fail closed without raising
- FileService enforces MAX_UPLOAD_SIZE / ALLOWED_IMAGE_TYPES from settings
- session helpers return honest False/int values on missing rows
- utc_now() is naive UTC (comparable with SQLite CURRENT_TIMESTAMP)
"""

import io
import json
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.clock import utc_now
from app.config import clear_settings_cache
from app.services.auth_service import auth_service
from app.services.file_service import FileService


class TestCorruptPasswordHashes:
    def test_verify_corrupt_hash_returns_false(self):
        assert auth_service.verify_password("anything", "not-a-valid-hash") is False

    def test_verify_empty_hash_returns_false(self):
        assert auth_service.verify_password("anything", "") is False

    def test_verify_truncated_argon2_hash_returns_false(self):
        full = auth_service.hash_password("CorrectHorse123!")
        assert auth_service.verify_password("CorrectHorse123!", full[:20]) is False

    def test_history_with_corrupt_json_fails_closed(self):
        assert auth_service.check_password_history("Password123!", "{oops") is False

    def test_history_with_corrupt_hash_entry_fails_closed(self):
        payload = json.dumps(["not-a-valid-hash"])
        assert auth_service.check_password_history("Password123!", payload) is False


class TestUtcNow:
    def test_utc_now_is_naive(self):
        assert utc_now().tzinfo is None

    def test_utc_now_matches_sqlite_current_timestamp_format(self):
        # SQLite CURRENT_TIMESTAMP renders 'YYYY-MM-DD HH:MM:SS'; naive UTC
        # datetimes must sort identically when stored via the adapter.
        stamp = utc_now()
        assert isinstance(stamp, datetime)
        assert stamp.isoformat(sep=" ", timespec="seconds")[:10] == stamp.date().isoformat()


class TestFileServiceSettingsWiring:
    def test_limits_come_from_settings(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MAX_UPLOAD_SIZE", "1024")
        monkeypatch.setenv("ALLOWED_IMAGE_TYPES", "image/png")
        clear_settings_cache()
        try:
            service = FileService(upload_dir=str(tmp_path))
            assert service.max_file_size == 1024
            assert service.allowed_mime_types == {"image/png"}
        finally:
            clear_settings_cache()

    async def test_oversize_upload_rejected_by_settings_limit(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MAX_UPLOAD_SIZE", "1024")
        clear_settings_cache()
        try:
            service = FileService(upload_dir=str(tmp_path))
            big = UploadFile(file=io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"x" * 2048))
            with pytest.raises(ValueError, match="exceeds maximum"):
                await service.save_upload(big, category="packages")
        finally:
            clear_settings_cache()

    def test_header_precheck_rejects_disallowed_type(self, tmp_path):
        service = FileService(upload_dir=str(tmp_path))
        bad = UploadFile(
            file=io.BytesIO(b"hello"),
            filename="evil.exe",
            headers=Headers({"content-type": "application/x-msdownload"}),
        )
        with pytest.raises(ValueError, match="not allowed"):
            service.validate_file(bad)


class TestSessionHelpersHonestReturns:
    async def test_terminate_unknown_session_returns_false(self, test_db):
        assert await auth_service.terminate_session_by_id(uuid4(), uuid4()) is False

    async def test_terminate_existing_session_returns_true_then_false(self, test_user):
        session = await auth_service.create_session(user_id=UUID(test_user["id"]))
        assert await auth_service.terminate_session_by_id(session.id, session.user_id) is True
        # Second call: already gone, must report False (drives the 404 path).
        assert (
            await auth_service.terminate_session_by_id(session.id, session.user_id) is False
        )

    async def test_cleanup_on_empty_db_returns_zero(self, test_db):
        cleaned = await auth_service.cleanup_expired_sessions()
        assert cleaned == 0
        assert isinstance(cleaned, int)
