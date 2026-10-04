"""Insurance record deduplication helpers.

The module is intentionally lightweight and deterministic so it can be validated in
small unit tests without external dependencies.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, List, Mapping, Sequence

from .normalization import normalize_record
from .risk_matching import calculate_match_score, is_duplicate


def deduplicate_records(
    records: Iterable[Mapping[str, Any]],
    *,
    key_fields: Sequence[str] | None = None,
    threshold: float = 0.82,
    min_group_size: int = 1,
) -> List[List[dict]]:
    """Group likely duplicates together.

    Each group is returned as a list of original record dictionaries. The function
    is intentionally conservative: it groups two records only when the similarity
    score meets the provided threshold.
    """
    items = [dict(record) for record in records]
    groups: List[List[dict]] = []
    matched = [False] * len(items)

    for index, record in enumerate(items):
        if matched[index]:
            continue
        current_group = [record]
        matched[index] = True

        for other_index, other in enumerate(items[index + 1 :], start=index + 1):
            if matched[other_index]:
                continue
            candidate = other
            score = calculate_match_score(
                normalize_record(record),
                normalize_record(candidate),
            )
            if score >= threshold:
                current_group.append(candidate)
                matched[other_index] = True

        if len(current_group) >= min_group_size:
            groups.append(current_group)

    return groups


def deduplicate_insurance_records(
    records: Iterable[Mapping[str, Any]],
    *,
    threshold: float = 0.82,
    min_group_size: int = 1,
) -> List[List[dict]]:
    """Compatibility wrapper for insurance-specific deduplication."""
    return deduplicate_records(records, threshold=threshold, min_group_size=min_group_size)


def find_duplicates(
    records: Iterable[Mapping[str, Any]],
    *,
    threshold: float = 0.82,
    min_group_size: int = 2,
) -> List[List[dict]]:
    """Return only groups with two or more likely duplicates."""
    return deduplicate_records(records, threshold=threshold, min_group_size=min_group_size)


__all__ = [
    "deduplicate_records",
    "deduplicate_insurance_records",
    "find_duplicates",
]
