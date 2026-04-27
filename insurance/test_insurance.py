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
        from premium import calculate_premium, build_policy_data, default_ai_recommendation
        data = build_policy_data("life", 100_000)
        ai = default_ai_recommendation("life", "2000-01-01")
        p = calculate_premium(data, ai)
        self.assertGreater(p, 0)

    def test_health_older(self):
        from premium import calculate_premium, build_policy_data, default_ai_recommendation
        data = build_policy_data("health", 50_000)
        ai_young = default_ai_recommendation("health", "2000-01-01")
        ai_old = default_ai_recommendation("health", "1955-01-01")
        p_young = calculate_premium(data, ai_young)
        p_old = calculate_premium(data, ai_old)
        self.assertGreater(p_old, p_young)

    def test_unknown_type(self):
        from premium import build_policy_data
        with self.assertRaises(ValueError):
            build_policy_data("spaceship", 100_000)

    def test_duration_scaling(self):
        from premium import calculate_premium, build_policy_data
        ai = {"recommended_multiplier": 1.0}
        data12 = build_policy_data("auto", 20_000, duration_months=12)
        data6 = build_policy_data("auto", 20_000, duration_months=6)
        p12 = calculate_premium(data12, ai)
        p6 = calculate_premium(data6, ai)
        self.assertAlmostEqual(p12, p6 * 2, places=1)

    def test_custom_ai_multiplier(self):
        from premium import calculate_premium, build_policy_data
        data = build_policy_data("auto", 100_000, duration_months=12)
        ai_low = {"recommended_multiplier": 0.8}
        ai_high = {"recommended_multiplier": 1.5}
        # auto base_rate=1.50, coverage_factor=1.0, duration_factor=1.0
        self.assertAlmostEqual(calculate_premium(data, ai_low), round(1.50 * 0.8, 2))
        self.assertAlmostEqual(calculate_premium(data, ai_high), round(1.50 * 1.5, 2))
        self.assertLess(calculate_premium(data, ai_low), calculate_premium(data, ai_high))


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
