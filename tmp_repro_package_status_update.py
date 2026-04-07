import asyncio
import logging
import os
from datetime import datetime, UTC
from uuid import UUID, uuid4

# Set env BEFORE importing app modules
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["APP_ENV"] = "testing"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["DATABASE_PATH"] = "./tmp_repro_service.duckdb"

from app.config import clear_settings_cache, get_settings
from app.database.connection import get_db, close_db
from app.database.schema import init_database
from app.database.write_queue import get_write_queue, close_write_queue
from app.models import PackageStatusUpdate, User
from app.services.package_service import package_service


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


async def main() -> None:
    clear_settings_cache()
    settings = get_settings()
    db_path = settings.database_path

    init_database(db_path)

    db = get_db()

    write_queue = await get_write_queue()

    user_id: UUID = uuid4()
    recipient_id: UUID = uuid4()
    package_id: UUID = uuid4()
    now = datetime.now(UTC)

    await write_queue.execute(
        """
        INSERT INTO users (
            id, username, password_hash, full_name, role, is_active,
            must_change_password, password_history, failed_login_count,
            locked_until, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
        """,
        [
            user_id,
            f"repro_user_{str(user_id)[:8]}",
            "fake_hash",
            "Repro User",
            "operator",
            True,
            False,
            "[]",
            0,
            None,
            now,
            now,
        ],
        return_result=True,
    )

    await write_queue.execute(
        """
        INSERT INTO recipients (
            id, employee_id, name, email, department, phone, location,
            is_active, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
        """,
        [
            recipient_id,
            f"EMP-{str(recipient_id)[:8]}",
            "Repro Recipient",
            f"repro_{str(recipient_id)[:8]}@example.com",
            "Ops",
            "",
            "",
            True,
            now,
            now,
        ],
        return_result=True,
    )

    await write_queue.execute(
        """
        INSERT INTO packages (
            id, tracking_no, carrier, recipient_id, status, notes,
            created_by, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
        """,
        [
            package_id,
            f"REPRO-{str(package_id)[:8]}",
            "UPS",
            recipient_id,
            "registered",
            "initial",
            user_id,
            now,
            now,
        ],
        return_result=True,
    )

    # Validate visibility from write worker connection vs thread-local read connection.
    writer_rows = await write_queue.execute(
        "SELECT id, status FROM packages WHERE id = ?",
        [package_id],
        return_result=True,
    )
    logging.getLogger(__name__).info("WRITER_SEES_PACKAGE %s", writer_rows)

    with db.get_read_connection() as conn:
        version = conn.execute("SELECT version()").fetchone()
        logging.getLogger(__name__).info("DuckDB version=%s", version[0] if version else "unknown")
        reader_row = conn.execute(
            "SELECT id, status FROM packages WHERE id = ?",
            [package_id],
        ).fetchone()
        logging.getLogger(__name__).info("READER_SEES_PACKAGE %s", reader_row)

    actor = User(
        id=user_id,
        username=f"repro_user_{str(user_id)[:8]}",
        password_hash="fake_hash",
        full_name="Repro User",
        role="operator",
        is_active=True,
        must_change_password=False,
        password_history="[]",
        failed_login_count=0,
        locked_until=None,
        created_at=now,
        updated_at=now,
    )

    statuses = ["awaiting_pickup", "out_for_delivery", "delivered", "returned"]

    for i in range(1, 21):
        next_status = statuses[i % len(statuses)]
        update = PackageStatusUpdate(status=next_status, notes=f"iteration={i}")
        try:
            updated = await package_service.update_status(package_id=package_id, status_update=update, actor=actor)
            logging.getLogger(__name__).info(
                "UPDATE_OK iter=%s package_id=%s status=%s notes=%s",
                i,
                updated.id,
                updated.status,
                updated.notes,
            )
        except Exception as exc:
            logging.getLogger(__name__).exception("UPDATE_FAIL iter=%s error=%s", i, exc)
            break

    with db.get_read_connection() as conn:
        row = conn.execute(
            "SELECT id, status, notes, updated_at FROM packages WHERE id = ?",
            [package_id],
        ).fetchone()
        logging.getLogger(__name__).info("FINAL_STATE %s", row)

    await close_write_queue()
    close_db()


if __name__ == "__main__":
    asyncio.run(main())
