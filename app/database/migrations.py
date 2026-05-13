"""Database migration and initialization helpers."""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from argon2 import PasswordHasher

from app.config import settings
from app.database.connection import create_connection
from app.database.schema import init_database, verify_schema

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BootstrapResult:
    """Result of a first-super-admin bootstrap attempt."""

    created: bool
    username: str
    password: Optional[str] = None
    generated_password: bool = False


class MigrationManager:
    """Manage database bootstrap and lightweight repair steps."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.ph = PasswordHasher(
            time_cost=settings.argon2_time_cost,
            memory_cost=settings.argon2_memory_cost,
            parallelism=settings.argon2_parallelism,
        )

    def run_migrations(self) -> None:
        """Ensure the SQLite database exists and matches the current schema."""
        db_file = Path(self.db_path)

        if not db_file.exists():
            logger.info("Database does not exist, creating new database")
        else:
            logger.info("Database exists, applying schema updates if needed")

        init_database(self.db_path)

        if not verify_schema(self.db_path):
            raise RuntimeError(f"Schema verification failed for database: {self.db_path}")

        self._enforce_recipient_department_requirement()
        self._seed_default_carriers()

    def user_count(self) -> int:
        """Return the number of users currently stored in the database."""
        conn = create_connection(self.db_path)
        try:
            result = conn.execute("SELECT COUNT(*) FROM users").fetchone()
            return result[0] if result else 0
        finally:
            conn.close()

    def bootstrap_super_admin(
        self,
        username: str = "admin",
        password: Optional[str] = None,
        full_name: str = "System Administrator",
    ) -> BootstrapResult:
        """Create the initial super admin if the users table is empty."""
        conn = create_connection(self.db_path)

        try:
            if self.user_count() > 0:
                logger.info("Users already exist, skipping super admin creation")
                return BootstrapResult(created=False, username=username)

            generated_password = password is None
            temporary_password = password or secrets.token_urlsafe(18)

            if len(temporary_password) < settings.password_min_length:
                raise ValueError(
                    f"Super admin password must be at least {settings.password_min_length} characters"
                )

            password_hash = self.ph.hash(temporary_password)
            conn.execute(
                """
                INSERT INTO users (
                    username,
                    password_hash,
                    full_name,
                    role,
                    is_active,
                    must_change_password
                ) VALUES (?, ?, ?, 'super_admin', 1, 1)
                """,
                (username, password_hash, full_name),
            )

            logger.info("Super admin user '%s' created successfully", username)
            return BootstrapResult(
                created=True,
                username=username,
                password=temporary_password,
                generated_password=generated_password,
            )

        finally:
            conn.close()

    def reset_database(self) -> None:
        """Delete the SQLite database files and recreate the schema."""
        logger.warning("Resetting database - all data will be lost!")

        db_file = Path(self.db_path)
        wal_file = db_file.with_name(db_file.name + "-wal")
        shm_file = db_file.with_name(db_file.name + "-shm")

        for path in (db_file, wal_file, shm_file):
            if path.exists():
                path.unlink()

        init_database(self.db_path)
        logger.info("Database reset complete")

    def _enforce_recipient_department_requirement(self) -> None:
        """Backfill missing recipient departments with a safe default."""
        conn = create_connection(self.db_path)
        try:
            conn.execute(
                """
                UPDATE recipients
                SET department = 'Unassigned'
                WHERE department IS NULL OR TRIM(department) = ''
                """
            )
        except Exception as exc:
            logger.error("Failed to enforce recipient department requirement: %s", exc)
        finally:
            conn.close()

    def _seed_default_carriers(self) -> None:
        """Seed the carriers table with default entries when it is empty."""
        conn = create_connection(self.db_path)
        try:
            result = conn.execute("SELECT COUNT(*) FROM carriers").fetchone()
            carrier_count = result[0] if result else 0

            if carrier_count > 0:
                logger.info("Carriers already exist, skipping default carrier seeding")
                return

            default_carriers = ["UPS", "FedEx", "USPS", "DHL", "Amazon Logistics"]
            for name in default_carriers:
                conn.execute(
                    "INSERT INTO carriers (name, is_active) VALUES (?, 1)",
                    (name,),
                )
            logger.info("Seeded %d default carriers", len(default_carriers))
        except Exception as exc:
            logger.error("Failed to seed default carriers: %s", exc)
        finally:
            conn.close()


def run_initial_migration(
    create_super_admin: bool = False,
    super_admin_username: str = "admin",
    super_admin_password: Optional[str] = None,
    super_admin_full_name: str = "System Administrator",
) -> Optional[BootstrapResult]:
    """Initialize the database and optionally seed the first super admin."""
    manager = MigrationManager(settings.database_path)
    manager.run_migrations()

    if create_super_admin:
        return manager.bootstrap_super_admin(
            username=super_admin_username,
            password=super_admin_password,
            full_name=super_admin_full_name,
        )

    return None


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    run_initial_migration()
