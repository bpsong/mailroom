"""Timezone-safe clock helpers.

SQLite ``CURRENT_TIMESTAMP`` and this project's stored timestamps are naive
UTC (``YYYY-MM-DD HH:MM:SS``). All Python-side timestamps must therefore be
naive UTC as well: ``datetime.now()`` returns *local* time (wrong on
non-UTC servers) and ``datetime.utcnow()`` is deprecated. Use :func:`utc_now`
everywhere instead so DB comparisons and Python comparisons agree.

This module lives at the top level of the ``app`` package (rather than
under ``app.utils``) so low-level modules like ``app.database.write_queue``
can import it without triggering the eager re-exports in
``app.utils.__init__`` (which would create a circular import).
"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current UTC time as a naive ``datetime``.

    Naive (tzinfo-free) by design: it sorts and compares equal with SQLite
    ``CURRENT_TIMESTAMP`` values and with timestamps historically stored via
    ``datetime.datetime.utcnow()``.
    """
    return datetime.now(UTC).replace(tzinfo=None)
