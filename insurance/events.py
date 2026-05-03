"""Events CRUD operations."""

import json

from database import get_connection


def create_event(event_type, payload):
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO events (type, payload) VALUES (?, ?)",
            (event_type, json.dumps(payload)),
        )
        return cursor.lastrowid


def get_event(event_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["payload"] = json.loads(result["payload"])
        return result


def list_events(event_type=None):
    with get_connection() as conn:
        if event_type:
            rows = conn.execute(
                "SELECT * FROM events WHERE type = ? ORDER BY created_at DESC",
                (event_type,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY created_at DESC"
            ).fetchall()
        result = []
        for row in rows:
            r = dict(row)
            r["payload"] = json.loads(r["payload"])
            result.append(r)
        return result


def delete_event(event_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
    return True
