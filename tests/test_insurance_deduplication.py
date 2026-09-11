import csv
import os
import tempfile
import unittest

from insurance import deduplicate_records, export_records, match_risk
from insurance.normalization import normalize_email, normalize_name, normalize_phone


class TestInsuranceNormalization(unittest.TestCase):
    def test_normalize_name(self):
        self.assertEqual(normalize_name("  JOHN  DOE  "), "john doe")

    def test_normalize_email(self):
        self.assertEqual(normalize_email("John@Example.com"), "john@example.com")

    def test_normalize_phone(self):
        self.assertEqual(normalize_phone("+1 (555) 123-4567"), "5551234567")


class TestInsuranceDeduplication(unittest.TestCase):
    def test_exact_duplicate_email_is_removed(self):
        records = [
            {"id": "A", "name": "Alice Smith", "email": "alice@example.com", "phone": "5551234567"},
            {"id": "B", "name": "Alice S.", "email": "alice@example.com", "phone": "5551234567"},
        ]
        result = deduplicate_records(records)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "A")

    def test_near_duplicate_name_is_grouped(self):
        records = [
            {"id": "A", "name": "John Doe", "email": "john@example.com"},
            {"id": "B", "name": "John  Doe", "email": "john-doe@example.com"},
        ]
        result = deduplicate_records(records, threshold=0.65)
        self.assertEqual(len(result), 1)


class TestInsuranceRiskMatching(unittest.TestCase):
    def test_risk_score_and_band(self):
        record = {"age": 22, "claim_count": 2, "coverage_amount": 300000, "policy_type": "auto"}
        result = match_risk(record)
        self.assertGreaterEqual(result["risk_score"], 40)
        self.assertIn(result["risk_band"], {"low", "medium", "high"})


class TestInsuranceExport(unittest.TestCase):
    def test_export_csv(self):
        records = [{"name": "Alice", "email": "alice@example.com"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "customers.csv")
            output = export_records(records, path)
            self.assertTrue(os.path.exists(output))
            with open(output, newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["name"], "Alice")


if __name__ == "__main__":
    unittest.main()
