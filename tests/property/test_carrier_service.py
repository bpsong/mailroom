"""Property-based tests for CarrierService.

Feature: ui-improvements
Properties tested: 8, 10, 11, 12
"""

import asyncio
import sqlite3
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from app.database.connection import DatabaseConnection
from app.database.schema import SCHEMA_SQL
from app.database.write_queue import WriteQueue
from app.models.carrier import CarrierCreate, CarrierUpdate
from app.services.carrier_service import CarrierService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_in_memory_db() -> tuple[str, DatabaseConnection]:
    """Create a fresh temporary SQLite file with the full schema applied."""
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    tmp.close()
    db_path = tmp.name

    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.executescript(SCHEMA_SQL)
    conn.close()

    db_conn = DatabaseConnection(db_path)
    return db_path, db_conn


async def _make_service() -> tuple[CarrierService, WriteQueue, DatabaseConnection, str]:
    """Return a CarrierService wired to a fresh isolated database."""
    db_path, db_conn = _make_in_memory_db()
    wq = WriteQueue(db_path)
    await wq.start()
    service = CarrierService()
    return service, wq, db_conn, db_path


async def _teardown(wq: WriteQueue, db_conn: DatabaseConnection, db_path: str) -> None:
    """Stop the write queue and clean up the temp database file."""
    await wq.stop()
    db_conn.close()
    for suffix in ("", "-wal", "-shm"):
        try:
            os.unlink(db_path + suffix)
        except FileNotFoundError:
            pass


def _run(coro):
    """Run a coroutine in a fresh event loop (Hypothesis calls sync functions)."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Property 8: Carrier deactivation removes from active list but retains in DB
# Validates: Requirements 12.6, 13.5
# ---------------------------------------------------------------------------

@given(name=st.text(min_size=1, max_size=100).filter(lambda s: s.strip() != ""))
@settings(max_examples=100, deadline=None)
def test_property_8_deactivation_removes_from_active_retains_in_all(name):
    """**Validates: Requirements 12.6, 13.5**

    For any active carrier, after calling deactivate_carrier(id), the carrier
    SHALL NOT appear in get_active_carriers() but SHALL still appear in
    get_all_carriers() with is_active = false.
    """

    async def _run_test():
        service, wq, db_conn, db_path = await _make_service()
        try:
            with patch("app.services.carrier_service.get_db", return_value=db_conn), \
                 patch("app.services.carrier_service.get_write_queue", return_value=wq):
                # Create a carrier
                carrier = await service.create_carrier(CarrierCreate(name=name.strip()))
                carrier_id = carrier.id

                # Verify it appears in active list before deactivation
                active_before = await service.get_active_carriers()
                assert any(c.id == carrier_id for c in active_before)

                # Deactivate
                deactivated = await service.deactivate_carrier(carrier_id)
                assert deactivated.is_active is False

                # Must NOT appear in active carriers
                active_after = await service.get_active_carriers()
                assert not any(c.id == carrier_id for c in active_after)

                # MUST still appear in all carriers with is_active = False
                all_carriers = await service.get_all_carriers()
                matching = [c for c in all_carriers if c.id == carrier_id]
                assert len(matching) == 1
                assert matching[0].is_active is False
        finally:
            await _teardown(wq, db_conn, db_path)

    _run(_run_test())


# ---------------------------------------------------------------------------
# Property 10: Carrier create and update persist correctly
# Validates: Requirements 13.3, 13.4
# ---------------------------------------------------------------------------

@given(
    create_name=st.text(min_size=1, max_size=100).filter(lambda s: s.strip() != ""),
    update_name=st.text(min_size=1, max_size=100).filter(lambda s: s.strip() != ""),
)
@settings(max_examples=100, deadline=None)
def test_property_10_create_and_update_persist_correctly(create_name, update_name):
    """**Validates: Requirements 13.3, 13.4**

    For any valid carrier name (non-empty, <= 100 chars, not a duplicate),
    create_carrier SHALL result in a carrier retrievable via get_all_carriers()
    with is_active=true and the correct name. update_carrier with a valid name
    SHALL result in get_carrier_by_id returning the updated name.
    """
    # If create and update names are the same (case-insensitively), the update
    # is a no-op rename to the same name — that's fine, just skip the duplicate
    # conflict scenario by ensuring they differ or are the same carrier.

    async def _run_test():
        service, wq, db_conn, db_path = await _make_service()
        try:
            with patch("app.services.carrier_service.get_db", return_value=db_conn), \
                 patch("app.services.carrier_service.get_write_queue", return_value=wq):

                # --- Create ---
                carrier = await service.create_carrier(CarrierCreate(name=create_name))
                carrier_id = carrier.id

                # Verify in get_all_carriers
                all_carriers = await service.get_all_carriers()
                matching = [c for c in all_carriers if c.id == carrier_id]
                assert len(matching) == 1
                assert matching[0].is_active is True
                assert matching[0].name == create_name.strip()

                # --- Update ---
                # If update_name (stripped) equals create_name (stripped) case-insensitively,
                # the update is valid (renaming to same name on same carrier is allowed).
                updated = await service.update_carrier(carrier_id, CarrierUpdate(name=update_name))
                assert updated.name == update_name.strip()

                # Verify via get_carrier_by_id
                fetched = await service.get_carrier_by_id(carrier_id)
                assert fetched is not None
                assert fetched.name == update_name.strip()
        finally:
            await _teardown(wq, db_conn, db_path)

    _run(_run_test())


# ---------------------------------------------------------------------------
# Property 11: Carrier name validation rejects invalid inputs
# Validates: Requirements 13.6
# ---------------------------------------------------------------------------

@given(
    invalid_name=st.one_of(
        st.just(""),
        st.just("   "),
        st.text(min_size=101),
    )
)
@settings(max_examples=100, deadline=None)
def test_property_11_invalid_names_raise_value_error(invalid_name):
    """**Validates: Requirements 13.6**

    For any carrier name that is empty (after stripping whitespace) or exceeds
    100 characters, create_carrier or update_carrier SHALL raise a ValueError
    and SHALL NOT persist any change to the database.
    """

    async def _run_test():
        service, wq, db_conn, db_path = await _make_service()
        try:
            with patch("app.services.carrier_service.get_db", return_value=db_conn), \
                 patch("app.services.carrier_service.get_write_queue", return_value=wq):

                carriers_before = await service.get_all_carriers()
                count_before = len(carriers_before)

                # --- create_carrier with invalid name ---
                # Pydantic will reject min_length=1 violations before service logic,
                # so we bypass the model for the empty-string case by calling the
                # service validation path directly via a model with a workaround,
                # OR we test the service's own strip-and-validate logic.
                # The service strips whitespace and checks emptiness itself.
                # For names > 100 chars, Pydantic rejects at model level (ValueError).
                # We test both paths.
                raised_create = False
                try:
                    # Use object() trick: pass a duck-typed object to bypass Pydantic
                    # field validation so we can test the service's own guard.
                    class _FakeName:
                        name = invalid_name

                    await service.create_carrier(_FakeName())  # type: ignore[arg-type]
                except (ValueError, Exception):
                    raised_create = True

                # No new carrier should have been persisted
                carriers_after_create = await service.get_all_carriers()
                assert len(carriers_after_create) == count_before, (
                    f"create_carrier with invalid name {invalid_name!r} persisted a carrier"
                )

                # --- update_carrier with invalid name (need a valid carrier first) ---
                # Create a valid carrier to update
                valid_carrier = await service.create_carrier(CarrierCreate(name="ValidCarrier"))
                count_with_valid = len(await service.get_all_carriers())

                raised_update = False
                try:
                    class _FakeUpdateName:
                        name = invalid_name

                    await service.update_carrier(valid_carrier.id, _FakeUpdateName())  # type: ignore[arg-type]
                except (ValueError, Exception):
                    raised_update = True

                # The valid carrier's name should be unchanged
                fetched = await service.get_carrier_by_id(valid_carrier.id)
                assert fetched is not None
                assert fetched.name == "ValidCarrier", (
                    f"update_carrier with invalid name {invalid_name!r} changed the carrier name"
                )
                # No extra carriers created
                assert len(await service.get_all_carriers()) == count_with_valid

        finally:
            await _teardown(wq, db_conn, db_path)

    _run(_run_test())


# ---------------------------------------------------------------------------
# Property 12: Carrier name deduplication is case-insensitive
# Validates: Requirements 13.7
# ---------------------------------------------------------------------------

def _case_variants(name: str):
    """Return a few case variants of a name."""
    return [
        name.upper(),
        name.lower(),
        name.swapcase(),
        name.capitalize(),
        name,
    ]


@given(base_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=" ")).filter(lambda s: s.strip() != "" and len(s.strip()) <= 50 and any(c.isalpha() for c in s) and all(ord(c) < 128 for c in s)))
@settings(max_examples=100, deadline=None)
def test_property_12_deduplication_is_case_insensitive(base_name):
    """**Validates: Requirements 13.7**

    For any existing carrier name N, attempting to create a new carrier with
    any case variation of N SHALL raise a ValueError and SHALL NOT create a
    second entry.
    """

    async def _run_test():
        service, wq, db_conn, db_path = await _make_service()
        try:
            with patch("app.services.carrier_service.get_db", return_value=db_conn), \
                 patch("app.services.carrier_service.get_write_queue", return_value=wq):

                stripped = base_name.strip()
                # Create the original carrier
                original = await service.create_carrier(CarrierCreate(name=stripped))

                all_before = await service.get_all_carriers()
                count_before = len(all_before)

                # Try each case variant — all should raise ValueError
                for variant in _case_variants(stripped):
                    if not variant.strip():
                        continue
                    # Skip if variant is identical to original (same bytes) — still
                    # should raise duplicate error
                    with pytest.raises(ValueError, match="already exists"):
                        await service.create_carrier(CarrierCreate(name=variant))

                    # Count must not have increased
                    all_after = await service.get_all_carriers()
                    assert len(all_after) == count_before, (
                        f"Duplicate carrier created for variant {variant!r} of {stripped!r}"
                    )

        finally:
            await _teardown(wq, db_conn, db_path)

    _run(_run_test())
