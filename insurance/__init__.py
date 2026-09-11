"""Insurance data processing helpers for normalization, deduplication, risk matching, and export."""

from .deduplication import deduplicate_records, group_duplicates
from .export import export_records
from .normalization import (
    normalize_date,
    normalize_email,
    normalize_name,
    normalize_phone,
    normalize_text,
)
from .risk_matching import match_risk, risk_band, risk_score

__all__ = [
    "deduplicate_records",
    "group_duplicates",
    "export_records",
    "normalize_date",
    "normalize_email",
    "normalize_name",
    "normalize_phone",
    "normalize_text",
    "match_risk",
    "risk_band",
    "risk_score",
]
