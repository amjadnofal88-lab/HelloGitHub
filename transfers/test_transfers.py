"""Unit tests for the Transfers REST API."""

import json
import os
import sys
import tempfile
import unittest

# Ensure the transfers package directory is on the path
sys.path.insert(0, os.path.dirname(__file__))

# Redirect the database to a temporary file so each test gets a clean slate
import database

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_db_fd)
database.DB_PATH = _db_path

import app as transfers_app


class TransfersAPITestCase(unittest.TestCase):
    def setUp(self):
        # Drop and recreate the transfers table before each test
        with database.get_connection() as conn:
            conn.execute("DROP TABLE IF EXISTS transfers")
            conn.commit()
        database.init_db()
        self.client = transfers_app.app.test_client()

    # ------------------------------------------------------------------
    # POST /transfers — success cases
    # ------------------------------------------------------------------

    def test_create_transfer_success(self):
        payload = {
            "beneficiary_name": "امجد محمود نوفل",
            "account_number": "668111",
            "amount": 6000000,
        }
        resp = self.client.post(
            "/transfers",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.get_json()
        self.assertIn("id", body)
        self.assertIn("reference", body)
        self.assertTrue(body["reference"].startswith("TXN-"))
        self.assertEqual(body["beneficiary_name"], "امجد محمود نوفل")
        self.assertEqual(body["account_number"], "668111")
        self.assertEqual(body["amount"], 6000000.0)
        self.assertEqual(body["status"], "pending")
        self.assertIn("created_at", body)

    def test_create_transfer_float_amount(self):
        payload = {
            "beneficiary_name": "Alice",
            "account_number": "ACC-001",
            "amount": 99.50,
        }
        resp = self.client.post(
            "/transfers",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["amount"], 99.50)

    def test_create_transfer_string_amount(self):
        """amount may be passed as a numeric string."""
        payload = {
            "beneficiary_name": "Bob",
            "account_number": "ACC-002",
            "amount": "1500",
        }
        resp = self.client.post(
            "/transfers",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)

    # ------------------------------------------------------------------
    # POST /transfers — validation errors
    # ------------------------------------------------------------------

    def test_missing_beneficiary_name(self):
        resp = self.client.post(
            "/transfers",
            data=json.dumps({"account_number": "ACC-003", "amount": 100}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("beneficiary_name", resp.get_json()["error"])

    def test_missing_account_number(self):
        resp = self.client.post(
            "/transfers",
            data=json.dumps({"beneficiary_name": "Carol", "amount": 100}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("account_number", resp.get_json()["error"])

    def test_missing_amount(self):
        resp = self.client.post(
            "/transfers",
            data=json.dumps(
                {"beneficiary_name": "Dave", "account_number": "ACC-004"}
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("amount", resp.get_json()["error"])

    def test_zero_amount(self):
        resp = self.client.post(
            "/transfers",
            data=json.dumps(
                {"beneficiary_name": "Eve", "account_number": "ACC-005", "amount": 0}
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_negative_amount(self):
        resp = self.client.post(
            "/transfers",
            data=json.dumps(
                {
                    "beneficiary_name": "Frank",
                    "account_number": "ACC-006",
                    "amount": -500,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_non_numeric_amount(self):
        resp = self.client.post(
            "/transfers",
            data=json.dumps(
                {
                    "beneficiary_name": "Grace",
                    "account_number": "ACC-007",
                    "amount": "not-a-number",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_no_json_body(self):
        resp = self.client.post("/transfers", data="plain text")
        self.assertEqual(resp.status_code, 400)

    # ------------------------------------------------------------------
    # GET /transfers
    # ------------------------------------------------------------------

    def test_list_transfers_empty(self):
        resp = self.client.get("/transfers")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json(), list)

    def test_list_transfers_after_create(self):
        payload = {
            "beneficiary_name": "Hana",
            "account_number": "ACC-008",
            "amount": 250,
        }
        self.client.post(
            "/transfers",
            data=json.dumps(payload),
            content_type="application/json",
        )
        resp = self.client.get("/transfers")
        self.assertEqual(resp.status_code, 200)
        transfers = resp.get_json()
        self.assertGreaterEqual(len(transfers), 1)


if __name__ == "__main__":
    unittest.main()
