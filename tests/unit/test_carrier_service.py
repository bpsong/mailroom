"""Unit tests for CarrierService.

Covers requirements: 12.5, 12.6, 13.3, 13.4, 13.5, 13.6, 13.7
"""

import pytest
from pydantic import ValidationError

from app.database.connection import create_connection
from app.models.carrier import CarrierCreate, CarrierUpdate
from app.services.carrier_service import CarrierService
from app.database.migrations import MigrationManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service() -> CarrierService:
    return CarrierService()


# ---------------------------------------------------------------------------
# CRUD operations  (Requirements 12.5, 13.3, 13.4, 13.5)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_carrier(test_db):
    """Req 13.3 – create with valid name returns carrier with correct name and is_active=True."""
    service = _make_service()
    carrier = await service.create_carrier(CarrierCreate(name="TestCarrier"))

    assert carrier.id is not None
    assert carrier.name == "TestCarrier"
    assert carrier.is_active is True


@pytest.mark.asyncio
async def test_get_active_carriers(test_db):
    """Req 12.6 – deactivated carrier excluded from active list."""
    service = _make_service()
    c1 = await service.create_carrier(CarrierCreate(name="ActiveOne"))
    c2 = await service.create_carrier(CarrierCreate(name="InactiveOne"))
    await service.deactivate_carrier(c2.id)

    active = await service.get_active_carriers()
    active_ids = {c.id for c in active}

    assert c1.id in active_ids
    assert c2.id not in active_ids


@pytest.mark.asyncio
async def test_get_all_carriers(test_db):
    """Req 12.6 – deactivated carrier still returned by get_all_carriers."""
    service = _make_service()
    c1 = await service.create_carrier(CarrierCreate(name="AllOne"))
    c2 = await service.create_carrier(CarrierCreate(name="AllTwo"))
    await service.deactivate_carrier(c2.id)

    all_carriers = await service.get_all_carriers()
    all_ids = {c.id for c in all_carriers}

    assert c1.id in all_ids
    assert c2.id in all_ids


@pytest.mark.asyncio
async def test_get_carrier_by_id(test_db):
    """Req 12.5 – retrieve carrier by id returns correct fields."""
    service = _make_service()
    created = await service.create_carrier(CarrierCreate(name="ByIdCarrier"))

    fetched = await service.get_carrier_by_id(created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == "ByIdCarrier"
    assert fetched.is_active is True


@pytest.mark.asyncio
async def test_get_carrier_by_id_not_found(test_db):
    """Req 12.5 – non-existent id returns None."""
    service = _make_service()
    result = await service.get_carrier_by_id(999999)
    assert result is None


@pytest.mark.asyncio
async def test_update_carrier(test_db):
    """Req 13.4 – update persists new name."""
    service = _make_service()
    created = await service.create_carrier(CarrierCreate(name="OldName"))

    updated = await service.update_carrier(created.id, CarrierUpdate(name="NewName"))

    assert updated.id == created.id
    assert updated.name == "NewName"

    # Verify persistence via a fresh read
    fetched = await service.get_carrier_by_id(created.id)
    assert fetched is not None
    assert fetched.name == "NewName"


@pytest.mark.asyncio
async def test_deactivate_carrier(test_db):
    """Req 13.5 – deactivate sets is_active=False."""
    service = _make_service()
    created = await service.create_carrier(CarrierCreate(name="ToDeactivate"))

    deactivated = await service.deactivate_carrier(created.id)

    assert deactivated.is_active is False

    # Verify persistence
    fetched = await service.get_carrier_by_id(created.id)
    assert fetched is not None
    assert fetched.is_active is False


# ---------------------------------------------------------------------------
# Validation error cases  (Requirements 13.6, 13.7)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_carrier_empty_name(test_db):
    """Req 13.6 – empty name raises ValueError."""
    service = _make_service()
    with pytest.raises(ValueError, match="Carrier name cannot be empty"):
        await service.create_carrier(CarrierCreate(name=" "))


@pytest.mark.asyncio
async def test_create_carrier_whitespace_only_name(test_db):
    """Req 13.6 – whitespace-only name raises ValueError."""
    service = _make_service()
    with pytest.raises(ValueError, match="Carrier name cannot be empty"):
        await service.create_carrier(CarrierCreate(name="   "))


@pytest.mark.asyncio
async def test_create_carrier_name_too_long(test_db):
    """Req 13.6 – name exceeding 100 chars is rejected (Pydantic enforces max_length=100)."""
    service = _make_service()
    long_name = "A" * 101
    # Pydantic rejects the input before the service runs
    with pytest.raises(ValidationError):
        await service.create_carrier(CarrierCreate(name=long_name))


@pytest.mark.asyncio
async def test_create_carrier_duplicate_name(test_db):
    """Req 13.7 – duplicate name raises ValueError."""
    service = _make_service()
    await service.create_carrier(CarrierCreate(name="DuplicateCarrier"))

    with pytest.raises(ValueError, match="A carrier with this name already exists"):
        await service.create_carrier(CarrierCreate(name="DuplicateCarrier"))


@pytest.mark.asyncio
async def test_create_carrier_duplicate_name_case_insensitive(test_db):
    """Req 13.7 – duplicate name check is case-insensitive."""
    service = _make_service()
    await service.create_carrier(CarrierCreate(name="CaseCarrier"))

    with pytest.raises(ValueError, match="A carrier with this name already exists"):
        await service.create_carrier(CarrierCreate(name="casecarrier"))


@pytest.mark.asyncio
async def test_update_carrier_empty_name(test_db):
    """Req 13.6 – update with empty name raises ValueError."""
    service = _make_service()
    created = await service.create_carrier(CarrierCreate(name="UpdateEmptyTest"))

    with pytest.raises(ValueError, match="Carrier name cannot be empty"):
        await service.update_carrier(created.id, CarrierUpdate(name="  "))


@pytest.mark.asyncio
async def test_update_carrier_name_too_long(test_db):
    """Req 13.6 – update with >100 char name is rejected (Pydantic enforces max_length=100)."""
    service = _make_service()
    created = await service.create_carrier(CarrierCreate(name="UpdateLongTest"))

    # Pydantic rejects the input before the service runs
    with pytest.raises(ValidationError):
        await service.update_carrier(created.id, CarrierUpdate(name="B" * 101))


@pytest.mark.asyncio
async def test_update_carrier_not_found(test_db):
    """Req 12.5 – update non-existent id raises ValueError."""
    service = _make_service()
    with pytest.raises(ValueError, match="Carrier not found"):
        await service.update_carrier(999999, CarrierUpdate(name="Ghost"))


@pytest.mark.asyncio
async def test_deactivate_carrier_not_found(test_db):
    """Req 12.5 – deactivate non-existent id raises ValueError."""
    service = _make_service()
    with pytest.raises(ValueError, match="Carrier not found"):
        await service.deactivate_carrier(999999)


# ---------------------------------------------------------------------------
# Seeding logic  (Requirements 13.3)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_seed_default_carriers(test_db):
    """Seeding on empty carriers table inserts UPS, FedEx, USPS, DHL, Amazon Logistics."""
    # Ensure table is empty (test_db fixture cleans up, but carriers table is not cleared there)
    conn = create_connection(test_db)
    try:
        conn.execute("DELETE FROM carriers")
    finally:
        conn.close()

    manager = MigrationManager(test_db)
    manager._seed_default_carriers()

    service = _make_service()
    all_carriers = await service.get_all_carriers()
    names = {c.name for c in all_carriers}

    expected = {"UPS", "FedEx", "USPS", "DHL", "Amazon Logistics"}
    assert expected == names


@pytest.mark.asyncio
async def test_seed_default_carriers_idempotent(test_db):
    """Seeding twice does not duplicate entries."""
    conn = create_connection(test_db)
    try:
        conn.execute("DELETE FROM carriers")
    finally:
        conn.close()

    manager = MigrationManager(test_db)
    manager._seed_default_carriers()
    manager._seed_default_carriers()  # second call should be a no-op

    service = _make_service()
    all_carriers = await service.get_all_carriers()
    names = [c.name for c in all_carriers]

    # No duplicates
    assert len(names) == len(set(names))
    assert len(names) == 5
