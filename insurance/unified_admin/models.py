from datetime import datetime, timezone

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="employee")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(40))
    dob = db.Column(db.Date)
    address = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class Policy(db.Model):
    __tablename__ = "policies"

    id = db.Column(db.Integer, primary_key=True)
    # Nullable so holder-name-centric policies (from the AIG UI) can be stored
    # without first resolving a Customer row.
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True)
    holder_name = db.Column(db.String(120))
    policy_number = db.Column(db.String(40), unique=True, nullable=False)
    policy_type = db.Column(db.String(40))
    effective_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date)
    status = db.Column(db.String(20), default="active", nullable=False)
    premium_amount = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class Claim(db.Model):
    __tablename__ = "claims"

    id = db.Column(db.Integer, primary_key=True)
    claim_number = db.Column(db.String(40), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True)
    holder_name = db.Column(db.String(120))
    policy_number = db.Column(db.String(40))
    date_filed = db.Column(db.Date)
    amount = db.Column(db.Float, nullable=False, default=0)
    description = db.Column(db.Text)
    # Workflow: pending -> approved|rejected ; approved -> paid
    status = db.Column(db.String(20), default="pending", nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class VipCard(db.Model):
    __tablename__ = "vip_cards"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    card_number = db.Column(db.String(40), unique=True, nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)
    monthly_fee = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class Installment(db.Model):
    __tablename__ = "installments"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    module_type = db.Column(db.String(20), nullable=False)  # insurance or vip
    reference_type = db.Column(db.String(20), nullable=False)  # policy or vip_card
    reference_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
