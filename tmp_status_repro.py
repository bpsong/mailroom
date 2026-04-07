import duckdb
import uuid
import datetime
import os


def run() -> None:
    db = "tmp_status_repro.duckdb"
    if os.path.exists(db):
        os.remove(db)

    con = duckdb.connect(db)
    try:
        con.execute("CREATE TABLE users (id UUID PRIMARY KEY, username VARCHAR)")
        con.execute(
            "CREATE TABLE recipients (id UUID PRIMARY KEY, employee_id VARCHAR, name VARCHAR, email VARCHAR)"
        )
        con.execute(
            """
            CREATE TABLE packages (
                id UUID PRIMARY KEY,
                tracking_no VARCHAR NOT NULL,
                carrier VARCHAR NOT NULL,
                recipient_id UUID NOT NULL,
                status VARCHAR NOT NULL,
                notes TEXT,
                created_by UUID NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                FOREIGN KEY (recipient_id) REFERENCES recipients(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
            """
        )

        uid = str(uuid.uuid4())
        rid = str(uuid.uuid4())
        pid = str(uuid.uuid4())
        now = datetime.datetime.utcnow()

        con.execute("INSERT INTO users VALUES (?, ?)", [uid, "u1"])
        con.execute(
            "INSERT INTO recipients VALUES (?, ?, ?, ?)",
            [rid, "E1", "R1", "r1@example.com"],
        )
        con.execute(
            "INSERT INTO packages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [pid, "T1", "UPS", rid, "registered", "n", uid, now, now],
        )
        print("inserted package", pid)

        try:
            rows = con.execute(
                """
                UPDATE packages
                SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                RETURNING id, tracking_no, carrier, recipient_id, status, notes, created_by, created_at, updated_at
                """,
                ["awaiting_pickup", "Ready", pid],
            ).fetchall()
            print("update_returning_ok", rows)
        except Exception as exc:
            print("update_returning_error", type(exc).__name__, str(exc))

        rows2 = con.execute(
            "SELECT id, status, notes FROM packages WHERE id = ?", [pid]
        ).fetchall()
        print("post_state", rows2)
    finally:
        con.close()


if __name__ == "__main__":
    run()
