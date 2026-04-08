"""Migrate live application data from DuckDB into SQLite."""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable
from uuid import UUID

import duckdb

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.connection import create_connection
from app.database.schema import init_database


RECIPIENT_EXPORT_COLUMNS = [
    "id",
    "employee_id",
    "name",
    "email",
    "department",
    "phone",
    "location",
    "is_active",
    "created_at",
    "updated_at",
]

TABLE_COLUMNS: dict[str, list[str]] = {
    "users": [
        "id",
        "username",
        "password_hash",
        "full_name",
        "role",
        "is_active",
        "must_change_password",
        "password_history",
        "failed_login_count",
        "locked_until",
        "created_at",
        "updated_at",
    ],
    "recipients": RECIPIENT_EXPORT_COLUMNS,
    "packages": [
        "id",
        "tracking_no",
        "carrier",
        "recipient_id",
        "status",
        "notes",
        "created_by",
        "created_at",
        "updated_at",
    ],
    "sessions": [
        "id",
        "user_id",
        "token",
        "expires_at",
        "last_activity",
        "ip_address",
        "user_agent",
        "created_at",
    ],
    "auth_events": [
        "id",
        "user_id",
        "event_type",
        "username",
        "ip_address",
        "details",
        "created_at",
    ],
    "package_events": [
        "id",
        "package_id",
        "old_status",
        "new_status",
        "notes",
        "actor_id",
        "created_at",
    ],
    "attachments": [
        "id",
        "package_id",
        "filename",
        "file_path",
        "mime_type",
        "file_size",
        "uploaded_by",
        "created_at",
    ],
    "system_settings": [
        "key",
        "value",
        "updated_by",
        "updated_at",
    ],
}

IMPORT_ORDER = [
    "users",
    "recipients",
    "packages",
    "sessions",
    "auth_events",
    "package_events",
    "attachments",
    "system_settings",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export recipients from DuckDB and migrate all tables into SQLite.",
    )
    parser.add_argument(
        "--source",
        default="data/mailroom.duckdb",
        help="Path to the source DuckDB database.",
    )
    parser.add_argument(
        "--target",
        default="data/mailroom.sqlite3",
        help="Path to the target SQLite database.",
    )
    parser.add_argument(
        "--recipient-export",
        default="data/recipient_export.csv",
        help="CSV path used to export recipients before importing them into SQLite.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the target SQLite database if it already exists.",
    )
    return parser.parse_args()


def normalize_value(value):
    """Normalize DuckDB values into sqlite3-friendly Python values."""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value
    return value


def fetch_table_rows(connection, table_name: str, columns: list[str]) -> list[tuple]:
    """Fetch rows from DuckDB using a stable column order."""
    column_sql = ", ".join(columns)
    rows = connection.execute(
        f"SELECT {column_sql} FROM {table_name}"
    ).fetchall()
    return [tuple(normalize_value(value) for value in row) for row in rows]


def export_recipients_to_csv(source_conn, export_path: Path) -> int:
    """Export recipient rows to a CSV file for backup and import."""
    export_path.parent.mkdir(parents=True, exist_ok=True)
    rows = fetch_table_rows(source_conn, "recipients", RECIPIENT_EXPORT_COLUMNS)

    with export_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(RECIPIENT_EXPORT_COLUMNS)
        for row in rows:
            writer.writerow(
                value.isoformat(sep=" ") if isinstance(value, datetime) else value
                for value in row
            )

    return len(rows)


def load_recipients_from_csv(export_path: Path) -> list[tuple]:
    """Read exported recipient rows back from CSV for SQLite import."""
    rows: list[tuple] = []
    with export_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            is_active = str(row["is_active"]).strip().lower() in {"1", "true", "yes"}
            rows.append(
                (
                    row["id"],
                    row["employee_id"],
                    row["name"],
                    row["email"],
                    row["department"] or None,
                    row["phone"] or None,
                    row["location"] or None,
                    int(is_active),
                    row["created_at"],
                    row["updated_at"],
                )
            )
    return rows


def executemany_insert(conn, table_name: str, columns: list[str], rows: Iterable[tuple]) -> int:
    """Bulk-insert rows into SQLite in the specified column order."""
    rows = list(rows)
    if not rows:
        return 0

    placeholders = ", ".join("?" for _ in columns)
    column_sql = ", ".join(columns)
    conn.executemany(
        f"INSERT INTO {table_name} ({column_sql}) VALUES ({placeholders})",
        rows,
    )
    return len(rows)


def remove_existing_sqlite_files(target_path: Path) -> None:
    """Remove SQLite database files before recreating them."""
    for suffix in ("", "-wal", "-shm"):
        Path(str(target_path) + suffix).unlink(missing_ok=True)


def main() -> int:
    args = parse_args()
    source_path = Path(args.source)
    target_path = Path(args.target)
    recipient_export_path = Path(args.recipient_export)

    if not source_path.exists():
        raise FileNotFoundError(f"DuckDB source database not found: {source_path.resolve()}")

    if target_path.exists() and not args.force:
        raise FileExistsError(
            f"SQLite target already exists: {target_path.resolve()} (use --force to overwrite)"
        )

    if args.force:
        remove_existing_sqlite_files(target_path)

    recipient_export_count = 0
    source_conn = duckdb.connect(str(source_path), read_only=True)
    try:
        recipient_export_count = export_recipients_to_csv(source_conn, recipient_export_path)
        table_rows = {
            table_name: fetch_table_rows(source_conn, table_name, columns)
            for table_name, columns in TABLE_COLUMNS.items()
            if table_name != "recipients"
        }
    finally:
        source_conn.close()

    init_database(str(target_path))
    sqlite_conn = create_connection(str(target_path))
    try:
        sqlite_conn.execute("BEGIN")

        imported_counts: dict[str, int] = {}
        for table_name in IMPORT_ORDER:
            columns = TABLE_COLUMNS[table_name]
            if table_name == "recipients":
                rows = load_recipients_from_csv(recipient_export_path)
            else:
                rows = table_rows.get(table_name, [])
            imported_counts[table_name] = executemany_insert(
                sqlite_conn,
                table_name,
                columns,
                rows,
            )

        sqlite_conn.commit()
    except Exception:
        sqlite_conn.rollback()
        raise
    finally:
        sqlite_conn.close()

    print(f"SOURCE_DUCKDB={source_path.resolve()}")
    print(f"TARGET_SQLITE={target_path.resolve()}")
    print(f"RECIPIENT_EXPORT_CSV={recipient_export_path.resolve()}")
    print(f"RECIPIENT_EXPORT_COUNT={recipient_export_count}")
    for table_name in IMPORT_ORDER:
        print(f"IMPORTED_{table_name.upper()}={imported_counts[table_name]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
