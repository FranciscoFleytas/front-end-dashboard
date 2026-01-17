from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, Iterable, Optional

from .settings import settings


def connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or settings.DB_PATH
    conn = sqlite3.connect(path, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    _apply_pragmas(conn)
    return conn


def _apply_pragmas(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=30000;")


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS quotes (
            quote_id TEXT PRIMARY KEY,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            status TEXT NOT NULL,
            fulfillment_status TEXT NOT NULL,
            late_payment INTEGER NOT NULL DEFAULT 0,
            currency_id TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            subtotals_cents_json TEXT NOT NULL,
            email TEXT NOT NULL,
            username TEXT NOT NULL,
            follows INTEGER NOT NULL,
            likes INTEGER NOT NULL,
            views INTEGER NOT NULL,
            comments INTEGER NOT NULL,
            preference_id TEXT,
            init_point TEXT,
            payment_id TEXT,
            payment_status TEXT,
            raw_payment_json TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_quotes_status_created_at
            ON quotes(status, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_quotes_payment_id
            ON quotes(payment_id);
        CREATE INDEX IF NOT EXISTS idx_quotes_expires_at
            ON quotes(expires_at);

        CREATE TABLE IF NOT EXISTS payment_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote_id TEXT,
            payment_id TEXT,
            event_type TEXT,
            received_at INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_events_quote_received
            ON payment_events(quote_id, received_at DESC);
        CREATE INDEX IF NOT EXISTS idx_events_payment_id
            ON payment_events(payment_id);
        """
    )
    _ensure_column(conn, "quotes", "init_point", "TEXT")


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
    existing = conn.execute(f"PRAGMA table_info({table});").fetchall()
    if any(row["name"] == column for row in existing):
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type};")


@contextmanager
def get_db() -> Iterable[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterable[None]:
    conn.execute("BEGIN IMMEDIATE;")
    try:
        yield
    except Exception:
        conn.execute("ROLLBACK;")
        raise
    else:
        conn.execute("COMMIT;")


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return dict(row)


def load_json(value: Optional[str]) -> Any:
    if not value:
        return None
    return json.loads(value)


def dump_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True)
