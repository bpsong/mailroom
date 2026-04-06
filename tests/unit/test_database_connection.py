"""Unit tests for [`DatabaseConnection`](app/database/connection.py:10)."""

import threading

from app.database.connection import DatabaseConnection


def test_get_read_connection_reuses_thread_local_connection(test_db):
    """[`DatabaseConnection.get_read_connection()`](app/database/connection.py:45) reuses the same connection per thread."""
    db = DatabaseConnection(test_db)

    with db.get_read_connection() as first_conn:
        first_id = id(first_conn)

    with db.get_read_connection() as second_conn:
        second_id = id(second_conn)

    assert first_id == second_id

    db.close()


def test_close_recreates_read_connection(test_db):
    """[`DatabaseConnection.close()`](app/database/connection.py:69) closes and clears the thread-local connection."""
    db = DatabaseConnection(test_db)

    with db.get_read_connection() as first_conn:
        first_id = id(first_conn)

    db.close()

    with db.get_read_connection() as second_conn:
        second_id = id(second_conn)

    assert first_id != second_id

    db.close()


def test_get_read_connection_is_isolated_per_thread(test_db):
    """[`DatabaseConnection._get_read_connection()`](app/database/connection.py:28) keeps one persistent connection per thread."""
    db = DatabaseConnection(test_db)
    main_thread_conn_ids: list[int] = []
    worker_thread_conn_ids: list[int] = []

    with db.get_read_connection() as main_conn:
        main_thread_conn_ids.append(id(main_conn))

    def worker() -> None:
        with db.get_read_connection() as worker_conn:
            worker_thread_conn_ids.append(id(worker_conn))
        db.close()

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert len(worker_thread_conn_ids) == 1
    assert main_thread_conn_ids[0] != worker_thread_conn_ids[0]

    db.close()
