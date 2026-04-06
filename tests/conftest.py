"""Pytest configuration and fixtures."""

import os
import tempfile
import asyncio
from uuid import uuid4

import duckdb
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

from app.config import clear_settings_cache, get_settings
from app.database import connection as db_connection
from app.database.schema import SCHEMA_SQL
from app.database.write_queue import close_write_queue
from app.main import app
from app.services.auth_service import auth_service


@pytest.fixture
def anyio_backend():
    """Use a single AnyIO backend to avoid duplicate test runs."""
    return "asyncio"


@pytest.fixture(scope="session")
def test_db_path():
    """Create a temporary test database."""
    # Create temporary directory for test database
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_mailroom.db")
    
    # Initialize database with schema
    conn = duckdb.connect(db_path)
    try:
        conn.execute(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()
    
    yield db_path
    
    # Cleanup
    try:
        os.remove(db_path)
        os.rmdir(temp_dir)
    except:
        pass


@pytest.fixture
def test_db(test_db_path, monkeypatch):
    """Set up test database for each test."""
    # Override the database path in the application
    monkeypatch.setenv("DATABASE_PATH", test_db_path)
    clear_settings_cache()
    get_settings()
    
    # Reset database connection and write queue so tests use isolated DB
    db_connection.close_db()
    try:
        asyncio.run(close_write_queue())
    except RuntimeError:
        # Event loop already running (e.g., during pytest-asyncio)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(close_write_queue())
    
    yield test_db_path
    
    # Clean up test data after each test
    conn = duckdb.connect(test_db_path)
    try:
        # Delete in reverse order of dependencies
        conn.execute("DELETE FROM attachments")
        conn.execute("DELETE FROM package_events")
        conn.execute("DELETE FROM packages")
        conn.execute("DELETE FROM sessions")
        conn.execute("DELETE FROM auth_events")
        conn.execute("DELETE FROM recipients")
        conn.execute("DELETE FROM users")
        conn.commit()
    finally:
        conn.close()

    # Reset cached settings for subsequent tests
    clear_settings_cache()


@pytest.fixture
def test_user(test_db):
    """Create a test operator user."""
    username = f"test_user_{uuid4().hex[:8]}"
    password = "TestPassword123!"
    password_hash = auth_service.hash_password(password)
    
    conn = duckdb.connect(test_db)
    try:
        result = conn.execute(
            """
            INSERT INTO users (username, password_hash, full_name, role, is_active, must_change_password)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            [username, password_hash, "Test User", "operator", True, False]
        ).fetchone()
        assert result is not None
        
        conn.commit()
        
        yield {
            "id": result[0],
            "username": username,
            "password": password,
            "role": "operator",
        }
    finally:
        conn.close()


@pytest.fixture
def test_admin(test_db):
    """Create a test admin user."""
    username = f"test_admin_{uuid4().hex[:8]}"
    password = "AdminPassword123!"
    password_hash = auth_service.hash_password(password)
    
    conn = duckdb.connect(test_db)
    try:
        result = conn.execute(
            """
            INSERT INTO users (username, password_hash, full_name, role, is_active, must_change_password)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            [username, password_hash, "Test Admin", "admin", True, False]
        ).fetchone()
        assert result is not None
        
        conn.commit()
        
        yield {
            "id": result[0],
            "username": username,
            "password": password,
            "role": "admin",
        }
    finally:
        conn.close()


@pytest.fixture
def test_recipient(test_db):
    """Create a test recipient."""
    employee_id = f"EMP{uuid4().hex[:8]}"
    
    conn = duckdb.connect(test_db)
    try:
        result = conn.execute(
            """
            INSERT INTO recipients (employee_id, name, email, department)
            VALUES (?, ?, ?, ?)
            RETURNING id
            """,
            [employee_id, "Test Recipient", "test@example.com", "Engineering"]
        ).fetchone()
        assert result is not None
        
        conn.commit()
        
        yield {
            "id": result[0],
            "employee_id": employee_id,
            "name": "Test Recipient",
        }
    finally:
        conn.close()


def _prime_csrf_token(client: TestClient, path: str = "/auth/login") -> str:
    """Ensure a CSRF token cookie exists for subsequent protected requests."""
    client.get(path)
    token = client.cookies.get("csrf_token")
    assert token, "CSRF token cookie was not set"
    return token


def _login(client: TestClient, username: str, password: str, next_url: str | None = None) -> tuple[dict, str]:
    """Login user via form workflow and return response payload + current CSRF token."""
    csrf_token = _prime_csrf_token(client)
    data = {
        "username": username,
        "password": password,
        "csrf_token": csrf_token,
    }
    if next_url:
        data["next"] = next_url

    response = client.post(
        "/auth/login",
        data=data,
        headers={"accept": "application/json"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()

    # CSRF cookie may be refreshed by middleware; always use latest value.
    csrf_token = client.cookies.get("csrf_token") or csrf_token

    return payload, csrf_token


@pytest.fixture
def client(test_db):
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def login_user(client):
    """Return helper that logs in a user and returns (client, payload, csrf_token)."""

    def _login_user(username: str, password: str, next_url: str | None = None):
        payload, csrf_token = _login(client, username, password, next_url)
        return client, payload, csrf_token

    return _login_user


@pytest.fixture
async def async_client(test_db):
    """Create an async HTTP client that exercises the full FastAPI lifespan."""
    with patch("app.main.run_initial_migration", return_value=None):
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                yield client
