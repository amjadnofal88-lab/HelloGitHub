"""Database setup and connection management."""

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

            CREATE TABLE IF NOT EXISTS transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                policy_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                transfer_date TEXT DEFAULT (datetime('now')),
                status TEXT DEFAULT 'pending',
                idempotency_key TEXT UNIQUE,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (policy_id) REFERENCES policies(id) ON DELETE CASCADE
            );
        """)
        # Migration: add idempotency_key to existing transfers tables that pre-date this column
        try:
            conn.execute(
                "ALTER TABLE transfers ADD COLUMN idempotency_key TEXT UNIQUE"
            )
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                raise
