"""Carrier management service for CRUD operations."""

import logging
from typing import Optional, List

from app.models.carrier import Carrier, CarrierCreate, CarrierUpdate
from app.database.connection import get_db
from app.database.write_queue import get_write_queue


logger = logging.getLogger(__name__)


def _validate_carrier_name(raw_name: str) -> str:
    """Validate a raw carrier name and return the normalized value."""
    if len(raw_name) > 100:
        raise ValueError("Carrier name must not exceed 100 characters")

    name = raw_name.strip()
    if not name:
        raise ValueError("Carrier name cannot be empty")

    return name


class CarrierService:
    """Service for carrier management operations."""

    async def get_active_carriers(self) -> List[Carrier]:
        """Return all carriers where is_active = 1, ordered by name."""
        db = get_db()
        with db.get_read_connection() as conn:
            result = conn.execute(
                """
                SELECT id, name, is_active, created_at, updated_at
                FROM carriers
                WHERE is_active = 1
                ORDER BY name ASC
                """
            ).fetchall()

        return [
            Carrier(
                id=row[0],
                name=row[1],
                is_active=bool(row[2]),
                created_at=row[3],
                updated_at=row[4],
            )
            for row in result
        ]

    async def get_all_carriers(self) -> List[Carrier]:
        """Return all carriers, ordered by name."""
        db = get_db()
        with db.get_read_connection() as conn:
            result = conn.execute(
                """
                SELECT id, name, is_active, created_at, updated_at
                FROM carriers
                ORDER BY name ASC
                """
            ).fetchall()

        return [
            Carrier(
                id=row[0],
                name=row[1],
                is_active=bool(row[2]),
                created_at=row[3],
                updated_at=row[4],
            )
            for row in result
        ]

    async def get_carrier_by_id(self, carrier_id: int) -> Optional[Carrier]:
        """Return a carrier by id, or None if not found."""
        db = get_db()
        with db.get_read_connection() as conn:
            row = conn.execute(
                """
                SELECT id, name, is_active, created_at, updated_at
                FROM carriers
                WHERE id = ?
                """,
                [carrier_id],
            ).fetchone()

        if not row:
            return None

        return Carrier(
            id=row[0],
            name=row[1],
            is_active=bool(row[2]),
            created_at=row[3],
            updated_at=row[4],
        )

    async def create_carrier(self, data: CarrierCreate) -> Carrier:
        """
        Validate and insert a new carrier.

        Raises:
            ValueError: If name is empty, too long, or already exists (case-insensitive).
        """
        name = _validate_carrier_name(data.name)

        # Case-insensitive uniqueness check
        db = get_db()
        with db.get_read_connection() as conn:
            existing = conn.execute(
                "SELECT id FROM carriers WHERE LOWER(name) = LOWER(?)",
                [name],
            ).fetchone()

        if existing:
            raise ValueError("A carrier with this name already exists")

        write_queue = await get_write_queue()
        result = await write_queue.execute(
            """
            INSERT INTO carriers (name, is_active, created_at, updated_at)
            VALUES (?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id, name, is_active, created_at, updated_at
            """,
            [name],
            return_result=True,
        )

        row = result[0]
        return Carrier(
            id=row[0],
            name=row[1],
            is_active=bool(row[2]),
            created_at=row[3],
            updated_at=row[4],
        )

    async def update_carrier(self, carrier_id: int, data: CarrierUpdate) -> Carrier:
        """
        Validate and update a carrier's name.

        Raises:
            ValueError: If carrier not found, name is empty, too long, or already exists.
        """
        # Check carrier exists
        carrier = await self.get_carrier_by_id(carrier_id)
        if not carrier:
            raise ValueError("Carrier not found")

        name = _validate_carrier_name(data.name)

        # Case-insensitive uniqueness check (exclude current carrier)
        db = get_db()
        with db.get_read_connection() as conn:
            existing = conn.execute(
                "SELECT id FROM carriers WHERE LOWER(name) = LOWER(?) AND id != ?",
                [name, carrier_id],
            ).fetchone()

        if existing:
            raise ValueError("A carrier with this name already exists")

        write_queue = await get_write_queue()
        result = await write_queue.execute(
            """
            UPDATE carriers
            SET name = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            RETURNING id, name, is_active, created_at, updated_at
            """,
            [name, carrier_id],
            return_result=True,
        )

        row = result[0]
        return Carrier(
            id=row[0],
            name=row[1],
            is_active=bool(row[2]),
            created_at=row[3],
            updated_at=row[4],
        )

    async def deactivate_carrier(self, carrier_id: int) -> Carrier:
        """
        Set is_active = 0 for the given carrier.

        Raises:
            ValueError: If carrier not found.
        """
        carrier = await self.get_carrier_by_id(carrier_id)
        if not carrier:
            raise ValueError("Carrier not found")

        write_queue = await get_write_queue()
        result = await write_queue.execute(
            """
            UPDATE carriers
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            RETURNING id, name, is_active, created_at, updated_at
            """,
            [carrier_id],
            return_result=True,
        )

        row = result[0]
        return Carrier(
            id=row[0],
            name=row[1],
            is_active=bool(row[2]),
            created_at=row[3],
            updated_at=row[4],
        )


carrier_service = CarrierService()
