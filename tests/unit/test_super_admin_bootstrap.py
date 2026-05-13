"""Tests for first-super-admin bootstrap behavior."""

from app.config import clear_settings_cache
from app.database.connection import create_connection
from app.database.migrations import MigrationManager, run_initial_migration


def test_run_initial_migration_does_not_create_super_admin_by_default(tmp_path, monkeypatch):
    db_path = tmp_path / "mailroom.sqlite3"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    clear_settings_cache()

    result = run_initial_migration()

    assert result is None
    conn = create_connection(str(db_path))
    try:
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        conn.close()

    assert user_count == 0
    clear_settings_cache()


def test_bootstrap_super_admin_generates_one_time_password(tmp_path):
    db_path = tmp_path / "mailroom.sqlite3"
    manager = MigrationManager(str(db_path))
    manager.run_migrations()

    result = manager.bootstrap_super_admin(username="setup_admin")

    assert result.created is True
    assert result.username == "setup_admin"
    assert result.generated_password is True
    assert result.password

    conn = create_connection(str(db_path))
    try:
        row = conn.execute(
            """
            SELECT username, password_hash, role, must_change_password
            FROM users
            """
        ).fetchone()
    finally:
        conn.close()

    assert row[0] == "setup_admin"
    assert manager.ph.verify(row[1], result.password)
    assert row[2] == "super_admin"
    assert row[3] == 1


def test_bootstrap_super_admin_does_not_create_when_users_exist(tmp_path):
    db_path = tmp_path / "mailroom.sqlite3"
    manager = MigrationManager(str(db_path))
    manager.run_migrations()

    first = manager.bootstrap_super_admin(username="first_admin")
    second = manager.bootstrap_super_admin(username="second_admin")

    assert first.created is True
    assert second.created is False
    assert second.password is None
    assert manager.user_count() == 1
