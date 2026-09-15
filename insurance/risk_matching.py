"""Risk-scoring helpers for insurance record matching."""

from __future__ import annotations

import math
import re
from typing import Any, Mapping

from .normalization import normalize_email, normalize_id, normalize_name, normalize_phone


def _tokenize(text: str) -> set[str]:
    return {token for token in re.split(r"\W+", (text or "").lower()) if token}


def _jaccard_similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    left = _tokenize(a)
    right = _tokenize(b)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def name_similarity(a: Any, b: Any) -> float:
    left = normalize_name(a)
    right = normalize_name(b)
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0

    left_tokens = _tokenize(left)
    right_tokens = _tokenize(right)
    if left_tokens and right_tokens:
        left_ordered = [token for token in left.split() if token]
        right_ordered = [token for token in right.split() if token]
        last_left = left_ordered[-1] if left_ordered else ""
        last_right = right_ordered[-1] if right_ordered else ""
        if last_left and last_left == last_right:
            return 0.75
        if left_tokens == right_tokens:
            return 1.0
        base = _jaccard_similarity(left, right)
        if len(left_tokens & right_tokens) >= 1 and max(len(left_tokens), len(right_tokens)) > 1:
            base = max(base, 0.5)
        return base
    return 0.0


def phone_similarity(a: Any, b: Any) -> float:
    left = normalize_phone(a)
    right = normalize_phone(b)
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return 1.0 if left == right else 0.0


def email_similarity(a: Any, b: Any) -> float:
    left = normalize_email(a)
    right = normalize_email(b)
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return 1.0 if left == right else 0.0


def id_similarity(a: Any, b: Any) -> float:
    left = normalize_id(a)
    right = normalize_id(b)
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return 1.0 if left == right else 0.0


def calculate_match_score(record_a: Mapping[str, Any], record_b: Mapping[str, Any]) -> float:
    """Score likely duplicate matches from 0.0 to 1.0."""
    record_a = dict(record_a)
    record_b = dict(record_b)

    name_match = name_similarity(record_a.get("name") or record_a.get("customer_name"), record_b.get("name") or record_b.get("customer_name"))
    phone_match = phone_similarity(record_a.get("phone") or record_a.get("mobile"), record_b.get("phone") or record_b.get("mobile"))
    email_match = email_similarity(record_a.get("email"), record_b.get("email"))
    id_match = id_similarity(record_a.get("id") or record_a.get("id_no") or record_a.get("customer_id"), record_b.get("id") or record_b.get("id_no") or record_b.get("customer_id"))

    if email_match and (phone_match or id_match or name_match >= 0.5):
        return 0.95
    if phone_match and email_match:
        return 0.95
    if phone_match and id_match:
        return 0.92
    if email_match and name_match >= 0.5:
        return 0.9
    if email_match:
        return 0.88
    if id_match and name_match >= 0.5:
        return 0.9

    weights = {
        "name": 0.40,
        "phone": 0.25,
        "email": 0.20,
        "id": 0.15,
    }

    score = 0.0
    total = 0.0

    for key, weight in weights.items():
        left = record_a.get(key) if key in record_a else record_a.get("customer_name") if key == "name" else None
        right = record_b.get(key) if key in record_b else record_b.get("customer_name") if key == "name" else None
        if key == "name":
            s = name_match
        elif key == "phone":
            s = phone_match
        elif key == "email":
            s = email_match
        else:
            s = id_match
        score += s * weight
        total += weight

    if name_match > 0.75 and phone_match > 0.5:
        score += 0.10
        total += 0.10
    if name_match > 0.75 and id_match > 0.5:
        score += 0.10
        total += 0.10
    if email_match > 0.75 and name_match > 0.5:
        score += 0.10
        total += 0.10

    if total == 0:
        return 0.0
    return min(1.0, score / total)


def is_duplicate(record_a: Mapping[str, Any], record_b: Mapping[str, Any], threshold: float = 0.82) -> bool:
    """Return True when two records are similar enough to be duplicates."""
    return calculate_match_score(record_a, record_b) >= threshold
