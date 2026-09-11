"""Risk scoring helpers for insurance customers and policies."""

from __future__ import annotations

import math
from typing import Any, Dict

from .normalization import normalize_date


def _to_years(age_value: Any) -> int:
    if age_value is None:
        return 0
    raw = str(age_value).strip()
    if raw.isdigit():
        return int(raw)
    try:
        dob = normalize_date(age_value)
        if not dob:
            return 0
        from datetime import date

        today = date.today()
        birth = date.fromisoformat(dob)
        return max(0, today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day)))
    except ValueError:
        return 0


def risk_score(record: Dict[str, Any]) -> int:
    """Calculate a simple risk score on a 0-100 scale from a record."""
    score = 0
    age = _to_years(record.get("age"))
    if age and age < 25:
        score += 20
    elif age and age > 60:
        score += 15

    claim_count = int(record.get("claim_count") or 0)
    score += min(claim_count * 15, 30)

    coverage = float(record.get("coverage_amount") or 0)
    if coverage > 250000:
        score += 15
    elif coverage > 100000:
        score += 10

    policy_type = str(record.get("policy_type") or "").lower()
    if policy_type in {"auto", "travel"}:
        score += 10
    elif policy_type in {"life", "health"}:
        score += 5

    return min(100, max(0, score))


def risk_band(score: int) -> str:
    if score >= 75:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def match_risk(record: Dict[str, Any]) -> Dict[str, Any]:
    """Return a risk summary dict with score and band."""
    score = risk_score(record)
    return {"risk_score": score, "risk_band": risk_band(score)}
