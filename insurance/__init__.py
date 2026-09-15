"""Insurance data utilities."""

from .deduplication import deduplicate_insurance_records, deduplicate_records, find_duplicates
from .normalization import normalize_record, normalize_text
from .risk_matching import calculate_match_score, is_duplicate

__all__ = [
    "deduplicate_records",
    "deduplicate_insurance_records",
    "find_duplicates",
    "normalize_record",
    "normalize_text",
    "calculate_match_score",
    "is_duplicate",
]
