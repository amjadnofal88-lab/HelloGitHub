import uuid
from datetime import date, datetime

from flask import Blueprint, abort, g, jsonify, request
from sqlalchemy import or_

from .auth_helpers import login_required
from .extensions import db
from .models import Claim

claims_bp = Blueprint("claims", __name__, url_prefix="/insurance")

# Allowed status transitions for the claim workflow.
_TRANSITIONS = {
    "pending": {"approved", "rejected"},
    "approved": {"paid"},
    "rejected": set(),
    "paid": set(),
}


def _enforce_write_role():
    if request.method in ("POST", "PATCH", "PUT", "DELETE") and g.current_user.role != "admin":
        abort(403)


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _serialize(claim):
    return {
        "id": claim.id,
        "claim_number": claim.claim_number,
        "customer_id": claim.customer_id,
        "holder_name": claim.holder_name,
        "policy_number": claim.policy_number,
        "date_filed": claim.date_filed.isoformat() if claim.date_filed else None,
        "amount": claim.amount,
        "description": claim.description,
        "status": claim.status,
    }


@claims_bp.route("/claims", methods=["GET", "POST"])
@login_required
def claims():
    _enforce_write_role()
    if request.method == "POST":
        payload = request.get_json(silent=True) or request.form
        year = (_parse_date(payload.get("date_filed")) or date.today()).year
        claim = Claim(
            claim_number=payload.get("claim_number")
            or f"CLM-{year}-{uuid.uuid4().hex[:6].upper()}",
            customer_id=int(payload["customer_id"]) if payload.get("customer_id") else None,
            holder_name=(payload.get("holder_name") or "").strip() or None,
            policy_number=(payload.get("policy_number") or "").strip() or None,
            date_filed=_parse_date(payload.get("date_filed")) or date.today(),
            amount=float(payload.get("amount", 0) or 0),
            description=payload.get("description"),
            status=payload.get("status", "pending"),
        )
        db.session.add(claim)
        db.session.commit()

    query = Claim.query
    status_filter = request.args.get("status")
    if status_filter:
        query = query.filter_by(status=status_filter)
    search = request.args.get("q")
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Claim.claim_number.ilike(like),
                Claim.holder_name.ilike(like),
                Claim.policy_number.ilike(like),
            )
        )
    rows = query.order_by(Claim.created_at.desc()).all()

    if request.headers.get("Accept") == "application/json" or request.is_json:
        return jsonify([_serialize(c) for c in rows])
    # No standalone Jinja template for claims; the AIG page consumes JSON.
    return jsonify([_serialize(c) for c in rows])


@claims_bp.route("/claims/<claim_number>/status", methods=["PATCH"])
@login_required
def update_claim_status(claim_number):
    _enforce_write_role()
    claim = Claim.query.filter_by(claim_number=claim_number).first()
    if not claim:
        return {"error": "Claim not found"}, 404

    payload = request.get_json(silent=True) or request.form
    new_status = (payload.get("status") or "").strip().lower()
    if new_status not in _TRANSITIONS:
        return {"error": f"Unknown status '{new_status}'"}, 400
    if new_status not in _TRANSITIONS.get(claim.status, set()):
        return {
            "error": f"Illegal transition {claim.status} -> {new_status}"
        }, 409

    claim.status = new_status
    db.session.commit()
    return jsonify(_serialize(claim))
