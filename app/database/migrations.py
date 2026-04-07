"""Database migration system."""

import logging
from pathlib import Path
from typing import Optional

import duckdb
from argon2 import PasswordHasher

from app.config import settings
from app.database.schema import init_database, verify_schema

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages database migrations and initialization."""
    
    def __init__(self, db_path: str):
        """
        Initialize the migration manager.
        
        Args:
            db_path: Path to the DuckDB database file
        """
        self.db_path = db_path
        self.ph = PasswordHasher(
            time_cost=settings.argon2_time_cost,
            memory_cost=settings.argon2_memory_cost,
            parallelism=settings.argon2_parallelism,
        )
    
    def run_migrations(self) -> None:
        """
        Run all pending migrations.
        
        This method checks if the database exists and has the correct schema,
        and creates it if necessary.
        """
        db_file = Path(self.db_path)
        
        if not db_file.exists():
            logger.info("Database does not exist, creating new database")
            self._create_database()
        else:
            logger.info("Database exists, verifying schema")
            if not verify_schema(self.db_path):
                logger.warning("Schema verification failed, recreating schema")
                self._create_database()
            else:
                logger.info("Schema verification passed")

        # Repair older databases that still have package_events/attachments
        # foreign keys referencing packages. Those constraints trigger DuckDB
        # UPDATE rewrite issues on package status changes.
        self._remove_package_dependent_foreign_keys_if_needed()
        
        # Enforce data quality requirements on existing data
        self._enforce_recipient_department_requirement()
    
    def _create_database(self) -> None:
        """Create the database with initial schema."""
        logger.info("Initializing database schema")
        init_database(self.db_path)
        logger.info("Database schema created successfully")

    def _remove_package_dependent_foreign_keys_if_needed(self) -> None:
        """Repair legacy schemas that still reference packages via foreign keys."""
        conn: duckdb.DuckDBPyConnection | None = None
        try:
            conn = duckdb.connect(self.db_path)
            fk_rows = conn.execute(
                """
                SELECT table_name, constraint_text
                FROM duckdb_constraints()
                WHERE table_name IN ('package_events', 'attachments')
                  AND constraint_type = 'FOREIGN KEY'
                """
            ).fetchall()

            if not fk_rows:
                return

            logger.warning(
                "Repairing legacy foreign keys on package_events/attachments: %s",
                fk_rows,
            )

            events_backup = conn.execute(
                "SELECT id, package_id, old_status, new_status, notes, actor_id, created_at FROM package_events"
            ).fetchall()
            attachments_backup = conn.execute(
                "SELECT id, package_id, filename, file_path, mime_type, file_size, uploaded_by, created_at FROM attachments"
            ).fetchall()

            conn.execute("BEGIN TRANSACTION")
            conn.execute("DROP TABLE IF EXISTS attachments")
            conn.execute("DROP TABLE IF EXISTS package_events")

            conn.execute(
                """
                CREATE TABLE package_events (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    package_id UUID NOT NULL,
                    old_status VARCHAR,
                    new_status VARCHAR NOT NULL,
                    notes TEXT,
                    actor_id UUID NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE attachments (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    package_id UUID NOT NULL,
                    filename VARCHAR NOT NULL,
                    file_path VARCHAR NOT NULL,
                    mime_type VARCHAR NOT NULL,
                    file_size INTEGER NOT NULL,
                    uploaded_by UUID NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            for row in events_backup:
                conn.execute(
                    "INSERT INTO package_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                    list(row),
                )

            for row in attachments_backup:
                conn.execute(
                    "INSERT INTO attachments VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    list(row),
                )

            conn.execute("CREATE INDEX IF NOT EXISTS idx_package_events_package_id ON package_events(package_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_package_events_actor_id ON package_events(actor_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_package_events_created_at ON package_events(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_package_id ON attachments(package_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_uploaded_by ON attachments(uploaded_by)")
            conn.commit()
            logger.info("Legacy package foreign keys removed successfully")
        except Exception:
            if conn is not None:
                conn.rollback()
            raise
        finally:
            if conn is not None:
                conn.close()
    
    def bootstrap_super_admin(
        self,
        username: str = "admin",
        password: str = "ChangeMe123!",
        full_name: str = "System Administrator"
    ) -> bool:
        """
        Create the initial super admin user if no users exist.
        
        Args:
            username: Username for the super admin
            password: Initial password (should be changed on first login)
            full_name: Full name of the super admin
            
        Returns:
            True if super admin was created, False if users already exist
        """
        conn = duckdb.connect(self.db_path)
        
        try:
            # Check if any users exist
            result = conn.execute("SELECT COUNT(*) FROM users").fetchone()
            user_count = result[0] if result else 0
            
            if user_count > 0:
                logger.info("Users already exist, skipping super admin creation")
                return False
            
            # Hash the password
            password_hash = self.ph.hash(password)
            
            # Create super admin user
            conn.execute("""
                INSERT INTO users (
                    username,
                    password_hash,
                    full_name,
                    role,
                    is_active,
                    must_change_password
                ) VALUES (?, ?, ?, 'super_admin', true, true)
            """, (username, password_hash, full_name))
            
            conn.commit()
            
            logger.info(f"Super admin user '{username}' created successfully")
            logger.warning(
                f"Default password is '{password}' - "
                "CHANGE THIS IMMEDIATELY on first login!"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error creating super admin user: {e}")
            conn.rollback()
            raise
        
        finally:
            conn.close()
    
    def reset_database(self) -> None:
        """
        Reset the database by dropping all tables and recreating schema.
        
        WARNING: This will delete all data!
        """
        logger.warning("Resetting database - all data will be lost!")
        
        conn = duckdb.connect(self.db_path)
        
        try:
            # Drop all tables
            tables = [
                'attachments',
                'package_events',
                'packages',
                'recipients',
                'auth_events',
                'sessions',
                'users'
            ]
            
            for table in tables:
                try:
                    conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                except Exception as e:
                    logger.warning(f"Error dropping table {table}: {e}")
            
            conn.commit()
            logger.info("All tables dropped")
        
        finally:
            conn.close()
        
        # Recreate schema
        self._create_database()
        logger.info("Database reset complete")
    
    def _enforce_recipient_department_requirement(self) -> None:
        """Ensure all recipients have a non-empty department value."""
        conn: duckdb.DuckDBPyConnection | None = None
        try:
            conn = duckdb.connect(self.db_path)
            conn.execute(
                """
                UPDATE recipients
                SET department = 'Unassigned'
                WHERE department IS NULL OR TRIM(department) = ''
                """
            )
            conn.commit()
        except Exception as exc:
            logger.error(f"Failed to enforce recipient department requirement: {exc}")
        finally:
            if conn:
                conn.close()


def run_initial_migration(
    create_super_admin: bool = True,
    super_admin_username: str = "admin",
    super_admin_password: str = "ChangeMe123!",
    super_admin_full_name: str = "System Administrator"
) -> None:
    """
    Run the initial database migration and optionally create super admin.
    
    Args:
        create_super_admin: Whether to create the super admin user
        super_admin_username: Username for the super admin
        super_admin_password: Initial password for the super admin
        super_admin_full_name: Full name of the super admin
    """
    manager = MigrationManager(settings.database_path)
    
    # Run migrations
    manager.run_migrations()
    
    # Create super admin if requested
    if create_super_admin:
        manager.bootstrap_super_admin(
            username=super_admin_username,
            password=super_admin_password,
            full_name=super_admin_full_name
        )


if __name__ == "__main__":
    # Run migrations when executed directly
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    run_initial_migration()
