"""Database setup and connection management."""

import json
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "insurance.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                date_of_birth TEXT,
                address TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                policy_number TEXT UNIQUE NOT NULL,
                policy_type TEXT NOT NULL,
                coverage_amount REAL NOT NULL,
                premium_amount REAL NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                policy_id INTEGER NOT NULL,
                claim_number TEXT UNIQUE NOT NULL,
                claim_date TEXT NOT NULL,
                description TEXT NOT NULL,
                amount_claimed REAL NOT NULL,
                amount_approved REAL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (policy_id) REFERENCES policies(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                payload TEXT,
                user_id INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)


def insert_audit_log(action, payload=None, user_id=None):
    """Insert a record into the audit_logs table.

    Args:
        action: A string describing the action being logged (e.g. 'whatsapp_sent').
        payload: An optional dict of additional data; stored as JSON.
        user_id: An optional integer identifying the user who triggered the action.

    Returns:
        The row id of the newly inserted audit log entry.
    """
    payload_json = json.dumps(payload) if payload is not None else None
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO audit_logs (action, payload, user_id) VALUES (?, ?, ?)",
            (action, payload_json, user_id),
        )
        return cursor.lastrowid
