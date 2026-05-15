import sqlite3
from datetime import UTC, datetime

# pylint: disable=too-many-arguments,too-many-positional-arguments


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS price_history (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            trakt_id     INTEGER NOT NULL,
            media_type   TEXT    NOT NULL,
            quality      TEXT    NOT NULL,
            price        REAL    NOT NULL,
            currency     TEXT    NOT NULL DEFAULT 'USD',
            observed_at  TEXT    NOT NULL,
            UNIQUE(trakt_id, media_type, quality) ON CONFLICT REPLACE
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_log (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            trakt_id       INTEGER NOT NULL,
            media_type     TEXT    NOT NULL,
            quality        TEXT    NOT NULL,
            notified_at    TEXT    NOT NULL,
            price          REAL    NOT NULL,
            original_price REAL    NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def get_last_price(
    conn: sqlite3.Connection, trakt_id: int, media_type: str, quality: str
) -> float | None:
    row = conn.execute(
        """
        SELECT price
        FROM price_history
        WHERE trakt_id = ? AND media_type = ? AND quality = ?
        """,
        (trakt_id, media_type, quality),
    ).fetchone()
    if row is None:
        return None
    return float(row[0])


def upsert_price(
    conn: sqlite3.Connection,
    trakt_id: int,
    media_type: str,
    quality: str,
    price: float,
    currency: str = "USD",
) -> None:
    conn.execute(
        """
        INSERT INTO price_history (trakt_id, media_type, quality, price, currency, observed_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (trakt_id, media_type, quality, price, currency, _utc_now()),
    )
    conn.commit()


def was_notified(
    conn: sqlite3.Connection, trakt_id: int, media_type: str, quality: str, price: float
) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM notification_log
        WHERE trakt_id = ?
            AND media_type = ?
            AND quality = ?
            AND price <= ?
        LIMIT 1
        """,
        (trakt_id, media_type, quality, price),
    ).fetchone()
    return row is not None


def log_notification(
    conn: sqlite3.Connection,
    trakt_id: int,
    media_type: str,
    quality: str,
    price: float,
    original_price: float,
) -> None:
    conn.execute(
        """
        INSERT INTO notification_log (
            trakt_id, media_type, quality, notified_at, price, original_price
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (trakt_id, media_type, quality, _utc_now(), price, original_price),
    )
    conn.commit()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
