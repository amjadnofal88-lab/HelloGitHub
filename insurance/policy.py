"""Policy CRUD operations."""

import uuid
from database import get_connection


def _generate_policy_number():
    return "POL-" + uuid.uuid4().hex[:8].upper()


def create_policy(customer_id, policy_type, coverage_amount, premium_amount,
                  start_date, end_date):
    policy_number = _generate_policy_number()
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO policies
               (customer_id, policy_number, policy_type, coverage_amount,
                premium_amount, start_date, end_date)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (customer_id, policy_number, policy_type, coverage_amount,
             premium_amount, start_date, end_date),
        )
        return cursor.lastrowid, policy_number


def get_policy(policy_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM policies WHERE id = ?", (policy_id,)
        ).fetchone()
        return dict(row) if row else None


def get_policy_by_number(policy_number):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM policies WHERE policy_number = ?", (policy_number,)
        ).fetchone()
        return dict(row) if row else None


def list_policies(customer_id=None):
    with get_connection() as conn:
        if customer_id:
            rows = conn.execute(
                "SELECT * FROM policies WHERE customer_id = ? ORDER BY created_at DESC",
                (customer_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM policies ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]


def update_policy(policy_id, **kwargs):
    # Column names come from the hard-coded `allowed` set, never from user input.
    allowed = {"coverage_amount", "premium_amount", "start_date", "end_date", "status"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in fields)  # safe: keys filtered above
    values = list(fields.values()) + [policy_id]
    with get_connection() as conn:
        conn.execute(
            f"UPDATE policies SET {set_clause} WHERE id = ?", values  # noqa: S608
        )
    return True


def delete_policy(policy_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM policies WHERE id = ?", (policy_id,))
    return True
