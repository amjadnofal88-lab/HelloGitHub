"""Claims CRUD operations."""

import uuid
from database import get_connection


def _generate_claim_number():
    return "CLM-" + uuid.uuid4().hex[:8].upper()


def create_claim(policy_id, claim_date, description, amount_claimed):
    claim_number = _generate_claim_number()
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO claims
               (policy_id, claim_number, claim_date, description, amount_claimed)
               VALUES (?, ?, ?, ?, ?)""",
            (policy_id, claim_number, claim_date, description, amount_claimed),
        )
        return cursor.lastrowid, claim_number


def get_claim(claim_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM claims WHERE id = ?", (claim_id,)
        ).fetchone()
        return dict(row) if row else None


def get_claim_by_number(claim_number):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM claims WHERE claim_number = ?", (claim_number,)
        ).fetchone()
        return dict(row) if row else None


def list_claims(policy_id=None):
    with get_connection() as conn:
        if policy_id:
            rows = conn.execute(
                "SELECT * FROM claims WHERE policy_id = ? ORDER BY claim_date DESC",
                (policy_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM claims ORDER BY claim_date DESC"
            ).fetchall()
        return [dict(r) for r in rows]


def update_claim(claim_id, **kwargs):
    # Column names come from the hard-coded `allowed` set, never from user input.
    allowed = {"description", "amount_claimed", "amount_approved", "status"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in fields)  # safe: keys filtered above
    values = list(fields.values()) + [claim_id]
    with get_connection() as conn:
        conn.execute(
            f"UPDATE claims SET {set_clause} WHERE id = ?", values  # noqa: S608
        )
    return True


def delete_claim(claim_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM claims WHERE id = ?", (claim_id,))
    return True
