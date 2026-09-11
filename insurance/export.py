"""Export helpers for insurance datasets."""

from __future__ import annotations

import csv
import json
import os
from typing import Iterable, Sequence


def export_records(records: Sequence[dict], output_path: str, fmt: str = "csv") -> str:
    """Export a sequence of dictionaries to CSV or JSON.

    Returns the normalized output path.
    """
    if not records:
        records = []

    directory = os.path.dirname(output_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    mode = (fmt or "csv").lower()
    if mode == "json":
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(list(records), handle, ensure_ascii=False, indent=2)
        return output_path

    fieldnames = []
    for record in records:
        if isinstance(record, dict):
            for key in record:
                if key not in fieldnames:
                    fieldnames.append(key)

    with open(output_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in records:
            if isinstance(row, dict):
                writer.writerow(row)
    return output_path
