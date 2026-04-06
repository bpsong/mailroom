# ADR-0003: Use Server-Side Session Authentication Instead of JWT

- **Status:** Accepted
- **Date:** 2026-04-06

## Context

The application is an internal, server-rendered FastAPI + HTMX system with CSRF protection and browser form workflows.

## Decision

Use server-side session tokens stored in database-backed session records, delivered via HttpOnly cookie (`session_token`), instead of JWT-based stateless auth.

## Rationale

- Fits browser-first HTML/HTMX interactions with minimal frontend auth complexity.
- Simplifies server-side invalidation (logout, forced rotation, admin actions).
- Works cleanly with CSRF middleware for state-changing requests.

## Consequences

### Positive

- Immediate session revocation and termination control.
- Lower risk of long-lived stateless token misuse in this architecture.
- Cleaner alignment with current middleware and route patterns.

### Negative / Trade-offs

- Requires session persistence and periodic cleanup.
- Adds DB reads to validate session on protected requests.
- Less suitable than JWT for cross-service token delegation without additional infrastructure.

## Related

- [API documentation](docs/API_DOCUMENTATION.md)
- [DuckDB decision](docs/adr/0001-use-duckdb.md)
