"""
Tests for the Insurance Management System.
Run with: python test_insurance.py
"""

import os
import sys
import unittest
import tempfile

# Use an in-memory / temp DB for tests
import database
_original_db = database.DB_PATH


class BaseTest(unittest.TestCase):
    def setUp(self):
        # Redirect DB to a temporary file for isolation
        self._db_file = os.path.join(os.path.dirname(__file__), "_test_insurance.db")
        database.DB_PATH = self._db_file
        database.init_db()

    def tearDown(self):
        database.DB_PATH = _original_db
        if os.path.exists(self._db_file):
            os.remove(self._db_file)


class TestCustomer(BaseTest):
    def test_create_and_get(self):
        import customer as ops
        cid = ops.create_customer("Alice Smith", "alice@example.com", "555-0100")
        c = ops.get_customer(cid)
        self.assertEqual(c["name"], "Alice Smith")
        self.assertEqual(c["email"], "alice@example.com")

    def test_list(self):
        import customer as ops
        ops.create_customer("Bob", "bob@example.com")
        ops.create_customer("Charlie", "charlie@example.com")
        self.assertGreaterEqual(len(ops.list_customers()), 2)

    def test_update(self):
        import customer as ops
        cid = ops.create_customer("Dave", "dave@example.com")
        ops.update_customer(cid, phone="555-9999")
        c = ops.get_customer(cid)
        self.assertEqual(c["phone"], "555-9999")

    def test_delete(self):
        import customer as ops
        cid = ops.create_customer("Eve", "eve@example.com")
        ops.delete_customer(cid)
        self.assertIsNone(ops.get_customer(cid))

    def test_duplicate_email(self):
        import customer as ops
        ops.create_customer("Frank", "frank@example.com")
        with self.assertRaises(Exception):
            ops.create_customer("Frank2", "frank@example.com")


class TestPremium(BaseTest):
    def test_life_young(self):
        from premium import calculate_premium
        p = calculate_premium("life", 100_000, "2000-01-01")
        self.assertGreater(p, 0)

    def test_health_older(self):
        from premium import calculate_premium
        p_young = calculate_premium("health", 50_000, "2000-01-01")
        p_old = calculate_premium("health", 50_000, "1955-01-01")
        self.assertGreater(p_old, p_young)

    def test_unknown_type(self):
        from premium import calculate_premium
        with self.assertRaises(ValueError):
            calculate_premium("spaceship", 100_000)

    def test_duration_scaling(self):
        from premium import calculate_premium
        p12 = calculate_premium("auto", 20_000, duration_months=12)
        p6 = calculate_premium("auto", 20_000, duration_months=6)
        self.assertAlmostEqual(p12, p6 * 2, places=1)


class TestPolicy(BaseTest):
    def _make_customer(self):
        import customer as ops
        return ops.create_customer("Test User", "test@example.com")

    def test_create_and_get(self):
        import policy as ops
        cid = self._make_customer()
        pid, pnum = ops.create_policy(cid, "auto", 50_000, 750.0,
                                      "2024-01-01", "2025-01-01")
        p = ops.get_policy(pid)
        self.assertEqual(p["policy_type"], "auto")
        self.assertTrue(p["policy_number"].startswith("POL-"))

    def test_list_by_customer(self):
        import policy as ops
        cid = self._make_customer()
        ops.create_policy(cid, "life", 100_000, 500.0, "2024-01-01", "2025-01-01")
        ops.create_policy(cid, "health", 30_000, 300.0, "2024-01-01", "2025-01-01")
        self.assertEqual(len(ops.list_policies(customer_id=cid)), 2)

    def test_update_status(self):
        import policy as ops
        cid = self._make_customer()
        pid, _ = ops.create_policy(cid, "home", 200_000, 1600.0,
                                   "2024-01-01", "2025-01-01")
        ops.update_policy(pid, status="expired")
        self.assertEqual(ops.get_policy(pid)["status"], "expired")

    def test_delete(self):
        import policy as ops
        cid = self._make_customer()
        pid, _ = ops.create_policy(cid, "travel", 10_000, 300.0,
                                   "2024-01-01", "2024-06-01")
        ops.delete_policy(pid)
        self.assertIsNone(ops.get_policy(pid))


class TestClaims(BaseTest):
    def _make_policy(self):
        import customer as cust
        import policy as pol
        cid = cust.create_customer("Claimant", "claimant@example.com")
        pid, _ = pol.create_policy(cid, "auto", 50_000, 750.0,
                                   "2024-01-01", "2025-01-01")
        return pid

    def test_create_and_get(self):
        import claims as ops
        pid = self._make_policy()
        clm_id, clm_num = ops.create_claim(pid, "2024-06-01", "Accident", 5000.0)
        c = ops.get_claim(clm_id)
        self.assertEqual(c["amount_claimed"], 5000.0)
        self.assertEqual(c["status"], "pending")
        self.assertTrue(c["claim_number"].startswith("CLM-"))

    def test_approve(self):
        import claims as ops
        pid = self._make_policy()
        clm_id, _ = ops.create_claim(pid, "2024-06-01", "Theft", 8000.0)
        ops.update_claim(clm_id, status="approved", amount_approved=7500.0)
        c = ops.get_claim(clm_id)
        self.assertEqual(c["status"], "approved")
        self.assertEqual(c["amount_approved"], 7500.0)

    def test_list_by_policy(self):
        import claims as ops
        pid = self._make_policy()
        ops.create_claim(pid, "2024-06-01", "Claim 1", 1000.0)
        ops.create_claim(pid, "2024-07-01", "Claim 2", 2000.0)
        self.assertEqual(len(ops.list_claims(policy_id=pid)), 2)

    def test_delete(self):
        import claims as ops
        pid = self._make_policy()
        clm_id, _ = ops.create_claim(pid, "2024-06-01", "Test", 500.0)
        ops.delete_claim(clm_id)
        self.assertIsNone(ops.get_claim(clm_id))


class TestReports(BaseTest):
    def _seed(self):
        import customer as cust
        import policy as pol
        import claims as clm
        cid = cust.create_customer("Report User", "report@example.com")
        pid, _ = pol.create_policy(cid, "auto", 50_000, 750.0,
                                   "2024-01-01", "2025-01-01")
        clm.create_claim(pid, "2024-06-01", "Fender bender", 2000.0)

    def test_summary(self):
        import reports
        self._seed()
        r = reports.summary_report()
        self.assertGreaterEqual(r["total_customers"], 1)
        self.assertGreaterEqual(r["total_policies"], 1)
        self.assertGreaterEqual(r["total_claims"], 1)

    def test_policies_by_type(self):
        import reports
        self._seed()
        rows = reports.policies_by_type_report()
        self.assertGreater(len(rows), 0)

    def test_top_claims(self):
        import reports
        self._seed()
        rows = reports.top_claims_report(5)
        self.assertGreater(len(rows), 0)

    def test_production_report_all(self):
        import reports
        self._seed()
        r = reports.production_report()
        self.assertGreaterEqual(r["totals"]["total_policies"], 1)
        self.assertGreaterEqual(r["totals"]["total_premiums"], 0)
        self.assertGreater(len(r["policies"]), 0)

    def test_production_report_filtered(self):
        import reports
        self._seed()
        r = reports.production_report(customer_name="Report User")
        self.assertGreaterEqual(r["totals"]["total_policies"], 1)
        for pol in r["policies"]:
            self.assertIn("report user", pol["customer_name"].lower())

    def test_production_report_no_match(self):
        import reports
        self._seed()
        r = reports.production_report(customer_name="nobody xyz")
        self.assertEqual(r["totals"]["total_policies"], 0)
        self.assertEqual(r["policies"], [])

    def test_loss_ratio_report(self):
        import reports
        import claims as clm
        self._seed()
        # approve the seeded claim so alternative ratio is non-zero
        conn_claims = clm.list_claims()
        if conn_claims:
            clm.update_claim(conn_claims[0]["id"], status="approved",
                             amount_approved=conn_claims[0]["amount_claimed"])
        r = reports.loss_ratio_report()
        self.assertIn("total_premiums", r)
        self.assertIn("loss_ratio", r)
        self.assertIn("alternative_real_loss_ratio", r)
        self.assertIn("by_policy_type", r)
        if r["total_premiums"]:
            self.assertIsNotNone(r["loss_ratio"])
            self.assertIsNotNone(r["alternative_real_loss_ratio"])
            if r["loss_ratio"] is not None and r["alternative_real_loss_ratio"] is not None:
                self.assertGreaterEqual(r["loss_ratio"], r["alternative_real_loss_ratio"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
