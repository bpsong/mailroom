# ADR-0002: Serialize Writes Through an Async Write Queue

- Status: Accepted
- Date: 2026-04-08

## Context

SQLite supports WAL mode and concurrent readers well, but write contention still becomes operationally noisy when many async handlers try to commit at the same time.

## Decision

Serialize application writes through a single async worker implemented by `WriteQueue`.

## Rationale

- Keeps write ordering deterministic.
- Reduces lock contention in request handlers.
- Centralizes timeout, rollback, and checkpoint behavior.
- Preserves the existing async service API while the storage engine remains embedded.

## Consequences

- The queue is still a throughput bottleneck for heavy write bursts.
- Caller timeout and eventual commit can diverge for `return_result=True` operations.
- Future migrations to a different database can remove this queue if it stops providing value.

## Related

- [ADR-0001: Use SQLite as the primary application database](0001-use-sqlite.md)
- [ADR-0003: Session auth over JWT](0003-session-auth-over-jwt.md)
- [Database schema](docs/DATABASE_SCHEMA.md)
