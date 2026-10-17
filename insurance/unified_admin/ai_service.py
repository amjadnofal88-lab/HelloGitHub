"""AI layer for the insurance platform.

Wraps the Anthropic SDK with graceful, deterministic fallbacks so every feature
keeps working when ANTHROPIC_API_KEY (or the `anthropic` package) is unavailable
— which is the case in offline/CI runs. Each public method returns plain dicts /
strings that the Flask layer can jsonify directly.
"""

import json
import logging
import re
from datetime import date, datetime

logger = logging.getLogger(__name__)

# Base annual rate per $1,000 of coverage, echoing the legacy premium engine.
_BASE_RATES = {
    "life": 0.5,
    "health": 2.0,
    "auto": 1.5,
    "home": 0.8,
    "commercial": 1.2,
    "travel": 3.0,
}

_HIGH_RISK_KEYWORDS = (
    "fraud", "arson", "fire", "total loss", "fatal", "injury",
    "lawsuit", "intentional", "dui", "theft",
)


def _age_from_dob(dob):
    if not dob:
        return None
    if isinstance(dob, str):
        try:
            dob = datetime.strptime(dob, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _age_multiplier(age):
    if age is None:
        return 1.0
    if age < 25:
        return 1.2
    if age < 40:
        return 1.0
    if age < 55:
        return 1.3
    if age < 65:
        return 1.7
    return 2.2


class AIService:
    def __init__(self, api_key=None, model="claude-opus-5-5"):
        self.model = model
        self._api_key = api_key
        self._client = None
        if api_key:
            try:
                import anthropic  # noqa: WPS433 (optional dependency)

                self._client = anthropic.Anthropic(api_key=api_key)
            except Exception as exc:  # pragma: no cover - import/credential issues
                logger.warning("Anthropic client unavailable, using fallbacks: %s", exc)
                self._client = None

    @property
    def enabled(self):
        return self._client is not None

    # --- low-level Claude call -------------------------------------------------
    def _complete(self, system, user, max_tokens=1024):
        """Return assistant text, or None if the live client is unavailable/fails."""
        if not self._client:
            return None
        try:
            resp = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
            return "\n".join(parts).strip()
        except Exception as exc:  # pragma: no cover - network/runtime failures
            logger.warning("Claude request failed, using fallback: %s", exc)
            return None

    def _complete_json(self, system, user, fallback, max_tokens=1024):
        text = self._complete(system + " Respond with a single JSON object only.", user, max_tokens)
        if not text:
            return fallback
        parsed = _extract_json(text)
        return parsed if parsed is not None else fallback

    # --- features --------------------------------------------------------------
    def chat(self, message, history=None, context=None):
        system = (
            "You are the assistant for Elite Insurance, an insurance admin platform. "
            "Help staff with questions about customers, policies, claims, premiums and "
            "coverage. Be concise and professional."
        )
        if context:
            system += f" Current platform data: {context}."
        convo = []
        for turn in history or []:
            role = turn.get("role")
            content = turn.get("content")
            if role in ("user", "assistant") and content:
                convo.append(f"{role}: {content}")
        convo.append(f"user: {message}")
        reply = self._complete(system, "\n".join(convo), max_tokens=1024)
        if reply:
            return {"reply": reply, "source": "ai"}
        return {"reply": _fallback_chat(message), "source": "fallback"}

    def risk_score(self, payload):
        policy_type = (payload.get("policy_type") or "auto").lower()
        coverage = float(payload.get("coverage_amount", payload.get("coverage", 10000)) or 10000)
        age = payload.get("age")
        if age is None:
            age = _age_from_dob(payload.get("dob"))

        fallback = _fallback_risk(policy_type, coverage, age)
        system = (
            "You are an insurance underwriting assistant. Estimate risk and a fair annual "
            "premium. Return JSON with keys: risk_score (0-100 integer), suggested_premium "
            "(number, USD), rationale (string)."
        )
        user = json.dumps(
            {"policy_type": policy_type, "coverage_amount": coverage, "age": age,
             "history": payload.get("history")}
        )
        result = self._complete_json(system, user, fallback)
        result.setdefault("source", "ai" if self.enabled else "fallback")
        return result

    def triage_claim(self, payload):
        amount = float(payload.get("amount", 0) or 0)
        description = payload.get("description", "") or ""
        fallback = _fallback_triage(amount, description)
        system = (
            "You are an insurance claims adjuster. Assess the claim and recommend one of "
            "'approve', 'review', or 'reject'. Return JSON with keys: recommendation, "
            "confidence (0-1 float), reasons (array of strings), extracted_fields (object)."
        )
        user = json.dumps(
            {"amount": amount, "description": description,
             "policy_number": payload.get("policy_number"),
             "holder_name": payload.get("holder_name")}
        )
        result = self._complete_json(system, user, fallback)
        result.setdefault("source", "ai" if self.enabled else "fallback")
        return result

    def extract_document(self, text):
        fallback = _fallback_extract(text or "")
        system = (
            "Extract structured insurance data from the document text. Return JSON with any "
            "of these keys you can find: name, dob (YYYY-MM-DD), email, phone, policy_type, "
            "policy_number, amount (number), address."
        )
        result = self._complete_json(system, text or "", fallback)
        if isinstance(result, dict):
            result.setdefault("source", "ai" if self.enabled else "fallback")
        return result


# --- module-level fallbacks ----------------------------------------------------
def _extract_json(text):
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except (ValueError, TypeError):
            return None
    return None


def _fallback_chat(message):
    return (
        "AI assistant is running in offline mode (no ANTHROPIC_API_KEY configured). "
        "I can still help you navigate the platform: use the dashboard for KPIs, and the "
        "Customers, Policies and Claims pages to manage records. "
        f"You asked: \"{(message or '').strip()[:200]}\"."
    )


def _fallback_risk(policy_type, coverage, age):
    base_rate = _BASE_RATES.get(policy_type, 1.0)
    multiplier = _age_multiplier(age)
    premium = round((coverage / 1000.0) * base_rate * multiplier, 2)
    # Normalise to a 0-100 risk score from the age multiplier and policy base rate.
    risk = min(100, int((multiplier - 0.8) * 40 + base_rate * 10))
    return {
        "risk_score": max(0, risk),
        "suggested_premium": premium,
        "rationale": (
            f"Deterministic estimate: base rate {base_rate}/$1k for {policy_type}, "
            f"age multiplier {multiplier} (age {age if age is not None else 'unknown'}), "
            f"coverage ${coverage:,.0f}."
        ),
    }


def _fallback_triage(amount, description):
    desc = (description or "").lower()
    flags = [kw for kw in _HIGH_RISK_KEYWORDS if kw in desc]
    if flags:
        recommendation, confidence = "review", 0.55
        reasons = [f"Description mentions risk keyword(s): {', '.join(flags)}."]
    elif amount >= 10000:
        recommendation, confidence = "review", 0.6
        reasons = [f"High claim amount (${amount:,.0f}) exceeds auto-approve threshold."]
    elif amount <= 0:
        recommendation, confidence = "reject", 0.7
        reasons = ["Claim amount is missing or non-positive."]
    else:
        recommendation, confidence = "approve", 0.75
        reasons = [f"Low amount (${amount:,.0f}) and no risk keywords detected."]
    return {
        "recommendation": recommendation,
        "confidence": confidence,
        "reasons": reasons,
        "extracted_fields": {"amount": amount, "keywords": flags},
    }


def _fallback_extract(text):
    out = {}
    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    if email:
        out["email"] = email.group(0)
    phone = re.search(r"\+?\d[\d\s().-]{7,}\d", text)
    if phone:
        out["phone"] = phone.group(0).strip()
    dob = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if dob:
        out["dob"] = dob.group(1)
    amount = re.search(r"\$\s*([\d,]+(?:\.\d{2})?)", text)
    if amount:
        out["amount"] = float(amount.group(1).replace(",", ""))
    policy = re.search(r"\bPOL-[\w-]+\b", text, re.IGNORECASE)
    if policy:
        out["policy_number"] = policy.group(0).upper()
    for ptype in _BASE_RATES:
        if re.search(rf"\b{ptype}\b", text, re.IGNORECASE):
            out["policy_type"] = ptype
            break
    return out
