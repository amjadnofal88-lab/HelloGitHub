from datetime import datetime

from .extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="employee")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(40))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Policy(db.Model):
    __tablename__ = "policies"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    policy_number = db.Column(db.String(40), unique=True, nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)
    premium_amount = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class VipCard(db.Model):
    __tablename__ = "vip_cards"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    card_number = db.Column(db.String(40), unique=True, nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)
    monthly_fee = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


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
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
