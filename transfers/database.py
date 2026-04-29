"""Database initialisation and connection helper for the Transfers service."""

import json
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "transfers.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transfers (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                reference        TEXT    NOT NULL UNIQUE,
                beneficiary_name TEXT    NOT NULL,
                account_number   TEXT    NOT NULL,
                amount           REAL    NOT NULL,
                status           TEXT    NOT NULL DEFAULT 'pending',
                created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                action     TEXT    NOT NULL,
                user_id    TEXT,
                payload    TEXT,
                created_at TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()


def insert_audit_log(action: str, payload: dict | None = None, user_id: str | None = None) -> None:
    """Record an audit log entry."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO audit_logs (action, user_id, payload) VALUES (?, ?, ?)",
            (action, user_id, json.dumps(payload) if payload is not None else None),
        )
        conn.commit()
