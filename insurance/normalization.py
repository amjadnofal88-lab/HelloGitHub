"""Normalization helpers for customer and policy records."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, Mapping


def normalize_text(value: Any, lower: bool = True) -> str:
    """Normalize text by trimming whitespace and collapsing repeated spaces."""
    if value is None:
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u200c", "")
    text = re.sub(r"\s+", " ", text)
    return text.lower() if lower else text


def normalize_name(value: Any) -> str:
    """Normalize a person or company name for comparison."""
    text = normalize_text(value)
    return re.sub(r"[^\w\s]", "", text).strip()


def normalize_phone(value: Any) -> str:
    """Normalize phone numbers to a compact digit string."""
    digits = re.sub(r"\D+", "", str(value or ""))
    return digits[-10:] if len(digits) > 10 else digits


def normalize_email(value: Any) -> str:
    """Normalize email addresses for deduplication."""
    return normalize_text(value).lower().strip()


def normalize_id(value: Any) -> str:
    """Normalize identifier-like values such as national IDs or customer refs."""
    text = str(value or "")
    text = re.sub(r"\s+", "", text)
    return text.strip().lower()


def normalize_record(record: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a normalized copy of a record ready for duplicate detection."""
    normalized = {}
    for key, value in record.items():
        key_name = str(key).strip()
        if key_name.lower() in {"name", "customer_name", "full_name", "insured_name"}:
            normalized[key_name] = normalize_name(value)
        elif key_name.lower() in {"phone", "mobile", "telephone", "tel"}:
            normalized[key_name] = normalize_phone(value)
        elif key_name.lower() in {"email", "e_mail"}:
            normalized[key_name] = normalize_email(value)
        elif key_name.lower() in {"id", "id_no", "national_id", "customer_id", "customer_ref"}:
            normalized[key_name] = normalize_id(value)
        else:
            normalized[key_name] = normalize_text(value)
    return normalized


def candidate_keys(record: Mapping[str, Any], fields: Iterable[str] | None = None) -> Dict[str, str]:
    """Build a compact comparison dictionary from the requested fields."""
    if fields is None:
        fields = ["name", "phone", "mobile", "email", "id", "id_no", "customer_id", "customer_ref"]
    values = {}
    for field in fields:
        if field in record:
            values[field] = normalize_record(record).get(field, "")
    return values
