"""Customer CRUD operations."""

from database import get_connection


def create_customer(name, email, phone=None, date_of_birth=None, address=None):
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO customers (name, email, phone, date_of_birth, address)
               VALUES (?, ?, ?, ?, ?)""",
            (name, email, phone, date_of_birth, address),
        )
        return cursor.lastrowid


def get_customer(customer_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        return dict(row) if row else None


def get_customer_by_email(email):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM customers WHERE email = ?", (email,)
        ).fetchone()
        return dict(row) if row else None


def list_customers():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM customers ORDER BY name"
        ).fetchall()
        return [dict(r) for r in rows]


def update_customer(customer_id, **kwargs):
    # Column names come from the hard-coded `allowed` set, never from user input.
    allowed = {"name", "email", "phone", "date_of_birth", "address"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in fields)  # safe: keys filtered above
    values = list(fields.values()) + [customer_id]
    with get_connection() as conn:
        conn.execute(
            f"UPDATE customers SET {set_clause} WHERE id = ?", values  # noqa: S608
        )
    return True


def delete_customer(customer_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
    return True
