from datetime import date

from flask import Blueprint, jsonify, render_template
from sqlalchemy import func

from .auth_helpers import login_required
from .models import Customer, Installment, Policy, VipCard

dashboard_bp = Blueprint("dashboard", __name__)


def _metrics():
    month_start = date.today().replace(day=1)

    total_customers = Customer.query.count()
    active_policies = Policy.query.filter_by(status="active").count()
    active_vip_cards = VipCard.query.filter_by(status="active").count()
    monthly_revenue = (
        Installment.query.with_entities(func.coalesce(func.sum(Installment.amount), 0.0))
        .filter(Installment.status == "paid", Installment.due_date >= month_start)
        .scalar()
    )
    pending_installments = Installment.query.filter_by(status="pending").count()

    return {
        "total_customers": total_customers,
        "active_policies": active_policies,
        "active_vip_cards": active_vip_cards,
        "monthly_revenue": float(monthly_revenue or 0.0),
        "pending_installments": pending_installments,
    }


@dashboard_bp.route("/")
@login_required
def index():
    return render_template("dashboard.html", metrics=_metrics())


@dashboard_bp.route("/api/dashboard")
@login_required
def dashboard_api():
    return jsonify(_metrics())
