import sqlite3
from pathlib import Path

from .extensions import db
from .models import Customer, Policy


def migrate_legacy_sqlite(legacy_db_path):
    """Import customers and policies from legacy insurance.db into unified schema."""
    legacy_path = Path(legacy_db_path)
    if not legacy_path.exists():
        raise FileNotFoundError(f"Legacy DB not found: {legacy_db_path}")

    conn = sqlite3.connect(str(legacy_path))
    conn.row_factory = sqlite3.Row

    customer_map = {}

    for row in conn.execute("SELECT id, name, email, phone FROM customers"):
        existing = Customer.query.filter_by(email=row["email"]).first()
        if existing:
            customer_map[row["id"]] = existing.id
            continue
        customer = Customer(name=row["name"], email=row["email"], phone=row["phone"])
        db.session.add(customer)
        db.session.flush()
        customer_map[row["id"]] = customer.id

    for row in conn.execute("SELECT customer_id, policy_number, status, premium_amount FROM policies"):
        if Policy.query.filter_by(policy_number=row["policy_number"]).first():
            continue
        mapped_customer_id = customer_map.get(row["customer_id"])
        if not mapped_customer_id:
            continue
        db.session.add(
            Policy(
                customer_id=mapped_customer_id,
                policy_number=row["policy_number"],
                status=row["status"] or "active",
                premium_amount=float(row["premium_amount"] or 0),
            )
        )

    db.session.commit()
    conn.close()
