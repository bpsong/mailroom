# ADR-0001: Use DuckDB as the Primary Application Database

- **Status:** Accepted
- **Date:** 2026-04-06

## Context

The application needs a lightweight relational database for internal mailroom workflows with simple deployment and minimal infrastructure overhead.

## Decision

Use DuckDB as the primary database for the current system.

## Rationale

- Easy local and server deployment (single file database).
- SQL support with sufficient features for current reporting and transactional needs.
- Good fit for the current single-application, moderate-concurrency environment.

## Consequences

### Positive

- Operational simplicity (no external DB server management).
- Fast setup for development and small-to-medium deployments.

### Negative / Trade-offs

- Single-writer constraints require explicit write serialization.
- Migration path to a multi-writer database may be needed at higher scale.
- Direct SQL usage across services increases coupling to DuckDB behavior.

## Related

- [Write queue design decision](docs/adr/0002-write-queue-for-duckdb.md)
- [Database schema documentation](docs/DATABASE_SCHEMA.md)
