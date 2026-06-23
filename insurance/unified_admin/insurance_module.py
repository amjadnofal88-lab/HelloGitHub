import uuid
from datetime import datetime

from flask import Blueprint, abort, g, jsonify, render_template, request
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from .auth_helpers import login_required
from .extensions import db
from .models import Customer, Installment, Policy

insurance_bp = Blueprint("insurance", __name__, url_prefix="/insurance")


class ValidationError(ValueError):
    pass


def _enforce_write_role():
    if request.method == "POST" and g.current_user.role != "admin":
        abort(403)


def _bad_request(message):
    return {"error": message}, 400


def _parse_int(payload, key):
    value = payload.get(key)
    if value in (None, ""):
        raise ValidationError(f"{key} is required")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{key} must be an integer") from exc


def _parse_float(payload, key, default=None):
    value = payload.get(key, default)
    if value in (None, "") and default is None:
        raise ValidationError(f"{key} is required")
    if value in (None, ""):
        value = default
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{key} must be a number") from exc


def _parse_due_date(payload):
    due_date = payload.get("due_date")
    if not due_date:
        raise ValidationError("due_date is required")
    try:
        return datetime.strptime(due_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationError("due_date must be YYYY-MM-DD") from exc


@insurance_bp.route("/customers", methods=["GET", "POST"])
@login_required
def customers():
    _enforce_write_role()
    if request.method == "POST":
        payload = request.get_json(silent=True) or request.form
        name = payload.get("name", "").strip()
        email = payload.get("email", "").strip()
        if not name:
            return _bad_request("name is required")
        if not email:
            return _bad_request("email is required")
        customer = Customer(
            name=name,
            email=email,
            phone=payload.get("phone"),
        )
        db.session.add(customer)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return _bad_request("invalid or duplicate customer data")

    rows = Customer.query.order_by(Customer.created_at.desc()).all()
    if request.headers.get("Accept") == "application/json" or request.is_json:
        return jsonify(
            [
                {"id": c.id, "name": c.name, "email": c.email, "phone": c.phone}
                for c in rows
            ]
        )
    return render_template("insurance_customers.html", customers=rows)


@insurance_bp.route("/policies", methods=["GET", "POST"])
@login_required
def policies():
    _enforce_write_role()
    if request.method == "POST":
        payload = request.get_json(silent=True) or request.form
        try:
            customer_id = _parse_int(payload, "customer_id")
            premium_amount = _parse_float(payload, "premium_amount", 0)
        except ValidationError:
            return _bad_request("invalid policy payload")
        policy = Policy(
            customer_id=customer_id,
            policy_number=payload.get("policy_number") or f"POL-{uuid.uuid4().hex[:8].upper()}",
            premium_amount=premium_amount,
            status=payload.get("status", "active"),
        )
        db.session.add(policy)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return _bad_request("invalid or duplicate policy data")

    rows = Policy.query.order_by(Policy.created_at.desc()).all()
    if request.headers.get("Accept") == "application/json" or request.is_json:
        return jsonify(
            [
                {
                    "id": p.id,
                    "customer_id": p.customer_id,
                    "policy_number": p.policy_number,
                    "status": p.status,
                    "premium_amount": p.premium_amount,
                }
                for p in rows
            ]
        )
    return render_template("insurance_policies.html", policies=rows)


@insurance_bp.route("/installments", methods=["GET", "POST"])
@login_required
def installments():
    _enforce_write_role()
    if request.method == "POST":
        payload = request.get_json(silent=True) or request.form
        try:
            customer_id = _parse_int(payload, "customer_id")
            reference_id = _parse_int(payload, "reference_id")
            amount = _parse_float(payload, "amount")
            due_date = _parse_due_date(payload)
        except ValidationError:
            return _bad_request("invalid installment payload")
        installment = Installment(
            customer_id=customer_id,
            module_type="insurance",
            reference_type="policy",
            reference_id=reference_id,
            amount=amount,
            due_date=due_date,
            status=payload.get("status", "pending"),
        )
        db.session.add(installment)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return _bad_request("invalid installment data")

    rows = Installment.query.filter_by(module_type="insurance").order_by(Installment.due_date.desc()).all()
    if request.headers.get("Accept") == "application/json" or request.is_json:
        return jsonify(
            [
                {
                    "id": i.id,
                    "customer_id": i.customer_id,
                    "reference_id": i.reference_id,
                    "amount": i.amount,
                    "due_date": i.due_date.isoformat(),
                    "status": i.status,
                }
                for i in rows
            ]
        )
    return render_template("insurance_installments.html", installments=rows)


@insurance_bp.route("/api/reports")
@login_required
def reports_api():
    active = Policy.query.filter_by(status="active").count()
    total_premium = (
        Policy.query.with_entities(func.coalesce(func.sum(Policy.premium_amount), 0.0))
        .filter(Policy.status == "active")
        .scalar()
    )
    pending_installments = Installment.query.filter_by(module_type="insurance", status="pending").count()

    return jsonify(
        {
            "active_policies": active,
            "total_active_premium": float(total_premium or 0.0),
            "pending_installments": pending_installments,
        }
    )
