import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")

from app.config import clear_settings_cache, get_settings
import duckdb


def main() -> None:
    clear_settings_cache()
    settings = get_settings()
    print("DB_PATH", settings.database_path)

    con = duckdb.connect(settings.database_path, read_only=True)
    try:
        for table in ["packages", "package_events", "attachments"]:
            print("TABLE", table)
            ddl = con.execute(
                "SELECT sql FROM duckdb_tables() WHERE table_name = ?",
                [table],
            ).fetchall()
            print("DDL", ddl)
            constraints = con.execute(
                "SELECT constraint_type, constraint_text FROM duckdb_constraints() WHERE table_name = ?",
                [table],
            ).fetchall()
            print("CONSTRAINTS", constraints)
    finally:
        con.close()


if __name__ == "__main__":
    main()
