"""List users in the SQLite database and reset all passwords."""

from __future__ import annotations

import json
from pathlib import Path

from app.database.connection import create_connection
from app.services.auth_service import auth_service


NEW_PASSWORD = "Password!1234"
DB_PATH = Path("data/mailroom.sqlite3")


def fetch_users(conn) -> list[dict]:
    """Return user account rows for reporting."""
    rows = conn.execute(
        """
        SELECT id, username, full_name, role, is_active,
               must_change_password, password_hash, password_history
        FROM users
        ORDER BY username
        """
    ).fetchall()

    return [
        {
            "id": str(row[0]),
            "username": row[1],
            "full_name": row[2],
            "role": row[3],
            "is_active": bool(row[4]),
            "must_change_password": bool(row[5]),
            "password_hash": row[6],
            "password_history": row[7],
        }
        for row in rows
    ]


def print_users(label: str, users: list[dict]) -> None:
    """Print a concise account listing."""
    print(label)
    for user in users:
        print(
            " - username={username} role={role} active={active} full_name={full_name}".format(
                username=user["username"],
                role=user["role"],
                active=user["is_active"],
                full_name=user["full_name"] or "",
            )
        )


def main() -> int:
    """Reset every user password and show before/after results."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database file not found: {DB_PATH.resolve()}")

    conn = create_connection(str(DB_PATH))
    try:
        before_users = fetch_users(conn)
        print(f"DATABASE_PATH={DB_PATH.resolve()}")
        print_users("USERS_BEFORE", before_users)

        for user in before_users:
            new_hash = auth_service.hash_password(NEW_PASSWORD)

            try:
                existing_history = user["password_history"]
                new_history = auth_service.update_password_history(new_hash, existing_history)
            except Exception:
                new_history = json.dumps([new_hash])

            conn.execute(
                """
                UPDATE users
                SET password_hash = ?,
                    password_history = ?,
                    must_change_password = false,
                    failed_login_count = 0,
                    locked_until = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                [new_hash, new_history, user["id"]],
            )

        conn.commit()

        after_users = fetch_users(conn)
        print_users("USERS_AFTER", after_users)

        verification_failures: list[str] = []
        for user in after_users:
            if not auth_service.verify_password(NEW_PASSWORD, user["password_hash"]):
                verification_failures.append(user["username"])

        if verification_failures:
            print("PASSWORD_RESET_VERIFICATION=FAILED")
            print("FAILED_USERS=" + ",".join(verification_failures))
            return 1

        print("PASSWORD_RESET_VERIFICATION=OK")
        print(f"RESET_PASSWORD={NEW_PASSWORD}")
        print(f"UPDATED_USER_COUNT={len(after_users)}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
