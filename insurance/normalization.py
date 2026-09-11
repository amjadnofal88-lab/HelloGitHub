"""Normalization helpers for insurance customer and policy records."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any, Iterable


def normalize_text(value: Any) -> str:
    """Return a stable lowercase string with whitespace and punctuation normalized."""
    if value is None:
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[\W_]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_name(value: Any) -> str:
    """Normalize person names using a stable, whitespace-safe representation."""
    text = normalize_text(value)
    return re.sub(r"\s+", " ", text).strip()


def normalize_email(value: Any) -> str:
    """Normalize an email value for duplicate detection."""
    if value is None:
        return ""
    email = str(value).strip().lower()
    return email


def normalize_phone(value: Any) -> str:
    """Normalize a phone number to digits only, preserving a national code when present."""
    if value is None:
        return ""
    digits = re.sub(r"\D+", "", str(value))
    if not digits:
        return ""
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) > 10:
        return digits[-10:]
    return digits


def normalize_date(value: Any) -> str:
    """Parse common date strings and return ISO format when possible."""
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return text


def normalize_record(record: dict) -> dict:
    """Return a shallow copy of a record with common fields normalized in-place."""
    normalized = dict(record)
    for field in ("name", "customer_name", "policyholder", "holder"):
        if field in normalized:
            normalized[field] = normalize_name(normalized[field])
    for field in ("email", "customer_email"):
        if field in normalized:
            normalized[field] = normalize_email(normalized[field])
    for field in ("phone", "mobile", "telephone"):
        if field in normalized:
            normalized[field] = normalize_phone(normalized[field])
    for field in ("date_of_birth", "dob", "birth_date"):
        if field in normalized:
            normalized[field] = normalize_date(normalized[field])
    for field in ("policy_number", "policy_no", "policy"):
        if field in normalized:
            normalized[field] = normalize_text(normalized[field])
    return normalized


def common_key_fields() -> Iterable[str]:
    return ("name", "email", "phone", "date_of_birth", "policy_number")
