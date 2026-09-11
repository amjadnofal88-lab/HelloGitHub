"""Duplicate detection helpers for insurance records."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Iterable, List, Sequence

from .normalization import (
    normalize_date,
    normalize_email,
    normalize_name,
    normalize_phone,
    normalize_text,
)


def _safe_value(record: dict, *keys: str) -> str:
    for key in keys:
        if key in record and record.get(key) not in (None, ""):
            return str(record.get(key))
    return ""


def _record_identity(record: dict) -> dict:
    return {
        "name": normalize_name(_safe_value(record, "name", "customer_name", "policyholder", "holder")),
        "email": normalize_email(_safe_value(record, "email", "customer_email")),
        "phone": normalize_phone(_safe_value(record, "phone", "mobile", "telephone")),
        "date_of_birth": normalize_date(_safe_value(record, "date_of_birth", "dob", "birth_date")),
        "policy_number": normalize_text(_safe_value(record, "policy_number", "policy_no", "policy")),
    }


def _similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _record_match_score(record_a: dict, record_b: dict) -> float:
    left = _record_identity(record_a)
    right = _record_identity(record_b)

    score = 0.0
    signal_count = 0

    for field in ("email", "phone", "policy_number", "date_of_birth"):
        if left.get(field) and right.get(field):
            signal_count += 1
            if left[field] == right[field]:
                score += 1.0
            else:
                score += max(0.0, 0.7 - _similarity(left[field], right[field]) * 0.7)

    if left.get("name") and right.get("name"):
        signal_count += 1
        name_score = 1.0 if left["name"] == right["name"] else _similarity(left["name"], right["name"])
        score += 1.5 * name_score

    return score / max(1, signal_count) if signal_count else 0.0


def deduplicate_records(records: Sequence[dict], threshold: float = 0.75) -> List[dict]:
    """Return a deduplicated list of records, merging near-duplicates into the first record.

    Records are considered duplicates when their normalized identity fields match closely
    enough, including exact email/phone/policy number matches or name similarity.
    """
    deduped: List[dict] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        merged = dict(record)
        matched = False
        for existing in deduped:
            score = _record_match_score(merged, existing)
            if score >= threshold:
                matched = True
                for key in merged:
                    if key not in existing or existing.get(key) in (None, ""):
                        existing[key] = merged.get(key)
                if "duplicates" not in existing:
                    existing["duplicates"] = [
                        {
                            "source": existing.get("source") or existing.get("id") or "record",
                            "record": dict(existing),
                        }
                    ]
                existing["duplicates"].append({
                    "source": merged.get("source") or merged.get("id") or "record",
                    "record": dict(merged),
                })
                break
        if not matched:
            deduped.append(merged)
    return deduped


def group_duplicates(records: Sequence[dict], threshold: float = 0.75) -> List[List[dict]]:
    """Group records by duplicate relationship and return each cluster as a list."""
    groups: List[List[dict]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        placed = False
        for group in groups:
            if any(_record_match_score(record, candidate) >= threshold for candidate in group):
                group.append(record)
                placed = True
                break
        if not placed:
            groups.append([record])
    return groups
