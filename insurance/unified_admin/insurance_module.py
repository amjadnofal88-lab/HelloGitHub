import uuid
from datetime import date, datetime, timedelta

from flask import Blueprint, abort, g, jsonify, render_template, request
from sqlalchemy import func

from .auth_helpers import login_required
from .extensions import db
from .models import Claim, Customer, Installment, Policy

insurance_bp = Blueprint("insurance", __name__, url_prefix="/insurance")


def _enforce_write_role():
    if request.method in ("POST", "PUT", "DELETE") and g.current_user.role != "admin":
        abort(403)


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _serialize_customer(c):
    return {
        "id": c.id,
        "name": c.name,
        "email": c.email,
        "phone": c.phone,
        "dob": c.dob.isoformat() if c.dob else None,
        "address": c.address,
    }


def _serialize_policy(p):
    return {
        "id": p.id,
        "customer_id": p.customer_id,
        "holder_name": p.holder_name,
        "policy_number": p.policy_number,
        "policy_type": p.policy_type,
        "effective_date": p.effective_date.isoformat() if p.effective_date else None,
        "expiry_date": p.expiry_date.isoformat() if p.expiry_date else None,
        "status": p.status,
        "premium_amount": p.premium_amount,
    }


def _wants_json():
    return request.headers.get("Accept") == "application/json" or request.is_json


@insurance_bp.route("/customers", methods=["GET", "POST"])
@login_required
def customers():
    _enforce_write_role()
    if request.method == "POST":
        payload = request.get_json(silent=True) or request.form
        customer = Customer(
            name=payload.get("name", "").strip(),
            email=payload.get("email", "").strip(),
            phone=payload.get("phone"),
            dob=_parse_date(payload.get("dob")),
            address=payload.get("address"),
        )
        db.session.add(customer)
        db.session.commit()

    rows = Customer.query.order_by(Customer.created_at.desc()).all()
    if _wants_json():
        return jsonify([_serialize_customer(c) for c in rows])
    return render_template("insurance_customers.html", customers=rows)


@insurance_bp.route("/customers/<int:customer_id>", methods=["PUT", "DELETE"])
@login_required
def customer_detail(customer_id):
    _enforce_write_role()
    customer = db.session.get(Customer, customer_id)
    if not customer:
        return {"error": "Customer not found"}, 404

    if request.method == "DELETE":
        db.session.delete(customer)
        db.session.commit()
        return {"message": "deleted"}, 200

    payload = request.get_json(silent=True) or request.form
    if payload.get("name") is not None:
        customer.name = payload.get("name", "").strip()
    if payload.get("email") is not None:
        customer.email = payload.get("email", "").strip()
    if "phone" in payload:
        customer.phone = payload.get("phone")
    if "dob" in payload:
        customer.dob = _parse_date(payload.get("dob"))
    if "address" in payload:
        customer.address = payload.get("address")
    db.session.commit()
    return jsonify(_serialize_customer(customer))


@insurance_bp.route("/policies", methods=["GET", "POST"])
@login_required
def policies():
    _enforce_write_role()
    if request.method == "POST":
        payload = request.get_json(silent=True) or request.form
        policy = Policy(
            customer_id=int(payload["customer_id"]) if payload.get("customer_id") else None,
            holder_name=(payload.get("holder_name") or "").strip() or None,
            policy_number=payload.get("policy_number")
            or f"POL-{uuid.uuid4().hex[:8].upper()}",
            policy_type=payload.get("policy_type"),
            effective_date=_parse_date(payload.get("effective_date")),
            expiry_date=_parse_date(payload.get("expiry_date")),
            premium_amount=float(payload.get("premium_amount", 0) or 0),
            status=payload.get("status", "active"),
        )
        db.session.add(policy)
        db.session.commit()

    rows = Policy.query.order_by(Policy.created_at.desc()).all()
    if _wants_json():
        return jsonify([_serialize_policy(p) for p in rows])
    return render_template("insurance_policies.html", policies=rows)


@insurance_bp.route("/policies/<int:policy_id>", methods=["PUT", "DELETE"])
@login_required
def policy_detail(policy_id):
    _enforce_write_role()
    policy = db.session.get(Policy, policy_id)
    if not policy:
        return {"error": "Policy not found"}, 404

    if request.method == "DELETE":
        db.session.delete(policy)
        db.session.commit()
        return {"message": "deleted"}, 200

    payload = request.get_json(silent=True) or request.form
    if "holder_name" in payload:
        policy.holder_name = (payload.get("holder_name") or "").strip() or None
    if "policy_type" in payload:
        policy.policy_type = payload.get("policy_type")
    if "effective_date" in payload:
        policy.effective_date = _parse_date(payload.get("effective_date"))
    if "expiry_date" in payload:
        policy.expiry_date = _parse_date(payload.get("expiry_date"))
    if payload.get("premium_amount") is not None:
        policy.premium_amount = float(payload.get("premium_amount") or 0)
    if payload.get("status") is not None:
        policy.status = payload.get("status")
    db.session.commit()
    return jsonify(_serialize_policy(policy))


@insurance_bp.route("/installments", methods=["GET", "POST"])
@login_required
def installments():
    _enforce_write_role()
    if request.method == "POST":
        payload = request.get_json(silent=True) or request.form
        installment = Installment(
            customer_id=int(payload["customer_id"]),
            module_type="insurance",
            reference_type="policy",
            reference_id=int(payload["reference_id"]),
            amount=float(payload["amount"]),
            due_date=datetime.strptime(payload["due_date"], "%Y-%m-%d").date(),
            status=payload.get("status", "pending"),
        )
        db.session.add(installment)
        db.session.commit()

    rows = Installment.query.filter_by(module_type="insurance").order_by(Installment.due_date.desc()).all()
    if _wants_json():
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


@insurance_bp.route("/api/dashboard-summary")
@login_required
def dashboard_summary():
    """KPI shape consumed by the AIG dashboard (FrmInsurance.html)."""
    today = date.today()
    soon = today + timedelta(days=30)

    total_policies = Policy.query.count()
    active_policies = Policy.query.filter_by(status="active").count()
    open_claims = Claim.query.filter_by(status="pending").count()
    expiring_soon = Policy.query.filter(
        Policy.status == "active",
        Policy.expiry_date.isnot(None),
        Policy.expiry_date >= today,
        Policy.expiry_date <= soon,
    ).count()

    recent_policies = Policy.query.order_by(Policy.created_at.desc()).limit(5).all()
    recent_claims = Claim.query.order_by(Claim.created_at.desc()).limit(5).all()

    return jsonify(
        {
            "total_policies": total_policies,
            "active_policies": active_policies,
            "open_claims": open_claims,
            "expiring_soon": expiring_soon,
            "recent_policies": [_serialize_policy(p) for p in recent_policies],
            "recent_claims": [
                {
                    "claim_number": c.claim_number,
                    "holder_name": c.holder_name,
                    "policy_number": c.policy_number,
                    "date_filed": c.date_filed.isoformat() if c.date_filed else None,
                    "amount": c.amount,
                    "status": c.status,
                }
                for c in recent_claims
            ],
        }
    )
