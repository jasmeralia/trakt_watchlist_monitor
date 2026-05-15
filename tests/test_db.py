import sqlite3

from db import get_last_price, init_db, log_notification, upsert_price, was_notified


def test_init_db_creates_tables() -> None:
    conn = init_db(":memory:")
    try:
        rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
                AND name IN ('price_history', 'notification_log')
            """
        ).fetchall()
    finally:
        conn.close()

    assert {row[0] for row in rows} == {"price_history", "notification_log"}


def test_get_last_price_returns_none_for_unknown_item() -> None:
    conn = init_db(":memory:")
    try:
        assert get_last_price(conn, 1, "movie", "HD") is None
    finally:
        conn.close()


def test_upsert_then_get_returns_price() -> None:
    conn = init_db(":memory:")
    try:
        upsert_price(conn, 1, "movie", "HD", 9.99)

        assert get_last_price(conn, 1, "movie", "HD") == 9.99
    finally:
        conn.close()


def test_was_notified_returns_false_then_true_after_logging() -> None:
    conn = init_db(":memory:")
    try:
        assert was_notified(conn, 1, "movie", "HD", 7.99) is False

        log_notification(conn, 1, "movie", "HD", 7.99, 12.99)

        assert was_notified(conn, 1, "movie", "HD", 7.99) is True
    finally:
        conn.close()


def test_init_db_returns_open_connection() -> None:
    conn = init_db(":memory:")
    try:
        assert isinstance(conn, sqlite3.Connection)
        conn.execute("SELECT 1")
    finally:
        conn.close()
