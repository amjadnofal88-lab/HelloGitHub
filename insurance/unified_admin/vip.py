import uuid
from datetime import datetime

from flask import Blueprint, abort, g, jsonify, render_template, request
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from .auth_helpers import login_required
from .extensions import db
from .models import Installment, VipCard

vip_bp = Blueprint("vip", __name__, url_prefix="/vip")


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


@vip_bp.route("/cards", methods=["GET", "POST"])
@login_required
def cards():
    _enforce_write_role()
    if request.method == "POST":
        payload = request.get_json(silent=True) or request.form
        try:
            customer_id = _parse_int(payload, "customer_id")
            monthly_fee = _parse_float(payload, "monthly_fee", 0)
        except ValidationError:
            return _bad_request("invalid vip card payload")
        card = VipCard(
            customer_id=customer_id,
            card_number=payload.get("card_number") or f"VIP-{uuid.uuid4().hex[:8].upper()}",
            monthly_fee=monthly_fee,
            status=payload.get("status", "active"),
        )
        db.session.add(card)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return _bad_request("invalid or duplicate vip card data")

    rows = VipCard.query.order_by(VipCard.created_at.desc()).all()
    if request.headers.get("Accept") == "application/json" or request.is_json:
        return jsonify(
            [
                {
                    "id": c.id,
                    "customer_id": c.customer_id,
                    "card_number": c.card_number,
                    "monthly_fee": c.monthly_fee,
                    "status": c.status,
                }
                for c in rows
            ]
        )
    return render_template("vip_cards.html", cards=rows)


@vip_bp.route("/installments", methods=["GET", "POST"])
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
            module_type="vip",
            reference_type="vip_card",
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

    rows = Installment.query.filter_by(module_type="vip").order_by(Installment.due_date.desc()).all()
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
    return render_template("vip_installments.html", installments=rows)


@vip_bp.route("/api/reports")
@login_required
def reports_api():
    active_cards = VipCard.query.filter_by(status="active").count()
    total_fees = (
        VipCard.query.with_entities(func.coalesce(func.sum(VipCard.monthly_fee), 0.0))
        .filter(VipCard.status == "active")
        .scalar()
    )
    pending_installments = Installment.query.filter_by(module_type="vip", status="pending").count()
    return jsonify(
        {
            "active_vip_cards": active_cards,
            "total_monthly_fees": float(total_fees or 0.0),
            "pending_installments": pending_installments,
        }
    )
