# ADR-0002: Serialize Writes Through an Async Write Queue

- **Status:** Accepted
- **Date:** 2026-04-06

## Context

DuckDB has practical single-writer constraints for concurrent application workloads. The app performs many write operations from async request handlers.

## Decision

Serialize all write operations through a single async write worker (`WriteQueue`).

## Rationale

- Prevent write lock conflicts and unstable concurrent-write behavior.
- Provide a single place for write logging, checkpointing, and resilience behavior.
- Keep read paths independent while guaranteeing ordered writes.

## Consequences

### Positive

- Predictable write ordering.
- Reduced write lock contention at runtime.
- Centralized place for future retry/telemetry/backpressure controls.

### Negative / Trade-offs

- Adds queue latency under heavy write load.
- Can become a bottleneck at higher throughput.
- Caller timeout and eventual commit can diverge when waiting for results.

## Timeout Semantics

For operations using `return_result=True`, caller wait timeout is bounded by `WRITE_QUEUE_RESULT_TIMEOUT`.

If caller timeout occurs:
- caller receives timeout error,
- operation may still execute later in the worker,
- final commit state may differ from immediate caller perception.

This behavior is documented in [Database schema documentation](docs/DATABASE_SCHEMA.md) under concurrency notes.

## Related

- [DuckDB database decision](docs/adr/0001-use-duckdb.md)
- [Session auth decision](docs/adr/0003-session-auth-over-jwt.md)
- [Write queue implementation](app/database/write_queue.py)
