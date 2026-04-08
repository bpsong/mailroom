# ADR-0001: Use SQLite as the Primary Application Database

- Status: Accepted
- Date: 2026-04-08

## Context

The application needs a lightweight relational database for internal mailroom workflows with simple deployment, minimal infrastructure overhead, and predictable Windows-friendly behavior.

## Decision

Use SQLite as the primary application database.

## Rationale

- Ships as part of the Python standard library through `sqlite3`.
- Keeps deployment simple with a single local database file.
- Supports WAL mode, foreign keys, and enough SQL features for the current workload.
- Removes the DuckDB-specific update and locking workarounds that were complicating the service layer and tests.

## Consequences

- Writes still need careful serialization under concurrent load.
- Scaling far beyond a single application node would require a different database backend.
- Direct SQL usage in services remains a coupling point for future migrations.

## Related

- [ADR-0002: Serialize writes through an async write queue](0002-write-queue-for-sqlite.md)
- [Database schema](docs/DATABASE_SCHEMA.md)
