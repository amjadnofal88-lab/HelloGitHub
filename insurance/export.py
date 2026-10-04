"""Export duplicate-detection results."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, List, Sequence


def export_groups(groups: Iterable[Sequence[dict]], output_path: str | Path) -> str:
    """Write deduplicated groups to a CSV file and return the path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    rows: List[dict] = []
    for idx, group in enumerate(groups, start=1):
        for record in group:
            merged = dict(record)
            merged["_group_id"] = idx
            rows.append(merged)

    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return str(path)


def export_duplicates(groups: Iterable[Sequence[dict]], output_path: str | Path) -> str:
    """Compatibility alias for export_groups()."""
    return export_groups(groups, output_path)
