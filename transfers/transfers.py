"""Transfer CRUD operations."""

import sqlite3
import uuid
from database import get_connection, insert_audit_log


def _generate_reference() -> str:
    return "TXN-" + uuid.uuid4().hex[:12].upper()


def create_transfer(
    beneficiary_name: str,
    account_number: str,
    amount: float,
) -> dict:
    """Insert a new transfer and return the created record."""
    for _ in range(5):
        reference = _generate_reference()
        try:
            with get_connection() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO transfers (reference, beneficiary_name, account_number, amount)
                    VALUES (?, ?, ?, ?)
                    """,
                    (reference, beneficiary_name, account_number, amount),
                )
                conn.commit()
                transfer_id = cur.lastrowid
            transfer = get_transfer(transfer_id)
            insert_audit_log(
                action="transfer_created",
                payload={
                    "reference": transfer["reference"],
                    "beneficiary_name": beneficiary_name,
                    "account_number": account_number,
                    "amount": amount,
                },
            )
            return transfer
        except sqlite3.IntegrityError:
            continue
    raise RuntimeError("Failed to generate a unique transfer reference after multiple attempts.")


def get_transfer(transfer_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM transfers WHERE id = ?", (transfer_id,)
        ).fetchone()
    return dict(row) if row else None


def list_transfers() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM transfers ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]
