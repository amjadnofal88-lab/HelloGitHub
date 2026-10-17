from flask import Blueprint, current_app, jsonify, render_template, request

from .ai_service import AIService
from .auth_helpers import login_required
from .models import Claim, Customer, Policy, VipCard

ai_bp = Blueprint("ai", __name__, url_prefix="/ai")


def _service():
    return AIService(
        api_key=current_app.config.get("ANTHROPIC_API_KEY"),
        model=current_app.config.get("AI_MODEL", "claude-opus-5-5"),
    )


def _db_context():
    return {
        "customers": Customer.query.count(),
        "policies": Policy.query.count(),
        "active_policies": Policy.query.filter_by(status="active").count(),
        "vip_cards": VipCard.query.count(),
        "open_claims": Claim.query.filter_by(status="pending").count(),
    }


@ai_bp.route("/", methods=["GET"])
@login_required
def assistant_page():
    return render_template("ai_assistant.html")


@ai_bp.route("/chat", methods=["POST"])
@login_required
def chat():
    payload = request.get_json(silent=True) or request.form
    message = (payload.get("message") or "").strip()
    if not message:
        return {"error": "message is required"}, 400
    history = payload.get("history") if isinstance(payload, dict) else None
    return jsonify(_service().chat(message, history=history, context=_db_context()))


@ai_bp.route("/risk-score", methods=["POST"])
@login_required
def risk_score():
    payload = request.get_json(silent=True) or request.form.to_dict()
    return jsonify(_service().risk_score(payload))


@ai_bp.route("/claims-triage", methods=["POST"])
@login_required
def claims_triage():
    payload = request.get_json(silent=True) or request.form.to_dict()
    return jsonify(_service().triage_claim(payload))


@ai_bp.route("/extract-document", methods=["POST"])
@login_required
def extract_document():
    payload = request.get_json(silent=True) or request.form.to_dict()
    text = payload.get("text", "")
    return jsonify(_service().extract_document(text))
