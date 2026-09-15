import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from insurance.deduplication import deduplicate_records, find_duplicates
from insurance.export import export_duplicates
from insurance.risk_matching import is_duplicate


def test_is_duplicate_for_same_phone_name():
    left = {"name": "Ahmed Ali", "phone": "+966 500 000 001", "email": "ahmed@example.com"}
    right = {"name": "A. Ali", "phone": "966500000001", "email": "ahmed@example.com"}
    assert is_duplicate(left, right) is True


def test_deduplicate_records_groups_similar_entries():
    records = [
        {"name": "Ahmad Ali", "phone": "+966 500 000 001", "email": "ahmed@example.com"},
        {"name": "Ahmad A. Ali", "phone": "966500000001", "email": "ahmed@example.com"},
        {"name": "Nora Sami", "phone": "+966 500 000 002", "email": "nora@example.com"},
    ]

    groups = deduplicate_records(records, threshold=0.65)
    assert len(groups) == 2
    assert any(len(group) == 2 for group in groups)


def test_same_email_is_treated_as_duplicate_even_without_phone_match():
    left = {"name": "Samir Ali", "email": "samir@example.com"}
    right = {"name": "Samir A.", "email": "samir@example.com"}
    assert is_duplicate(left, right) is True


def test_find_duplicates_requires_multiple_records():
    records = [
        {"name": "Samir", "phone": "966500000003"},
        {"name": "Samir", "phone": "966500000003"},
    ]
    groups = find_duplicates(records, threshold=0.8)
    assert len(groups) == 1
    assert len(groups[0]) == 2


def test_export_duplicates_writes_csv(tmp_path):
    output = tmp_path / "dedup.csv"
    groups = [[{"name": "Ali", "phone": "966500000001"}, {"name": "Ali", "phone": "966500000001"}]]
    path = export_duplicates(groups, output)
    assert os.path.exists(path)
    assert path.endswith("dedup.csv")
