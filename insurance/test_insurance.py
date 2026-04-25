"""
Tests for the Insurance Management System.
Run with: python test_insurance.py
"""

import os
import sys
import unittest
import tempfile
from datetime import date

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

    def test_get_nonexistent(self):
        import customer as ops
        self.assertIsNone(ops.get_customer(99999))

    def test_get_by_email(self):
        import customer as ops
        cid = ops.create_customer("Grace", "grace@example.com")
        c = ops.get_customer_by_email("grace@example.com")
        self.assertIsNotNone(c)
        self.assertEqual(c["id"], cid)
        self.assertEqual(c["name"], "Grace")

    def test_get_by_email_nonexistent(self):
        import customer as ops
        self.assertIsNone(ops.get_customer_by_email("nobody@example.com"))

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

    def test_update_multiple_fields(self):
        import customer as ops
        cid = ops.create_customer("Hank", "hank@example.com")
        ops.update_customer(cid, name="Henry", address="123 Main St",
                            date_of_birth="1990-05-15")
        c = ops.get_customer(cid)
        self.assertEqual(c["name"], "Henry")
        self.assertEqual(c["address"], "123 Main St")
        self.assertEqual(c["date_of_birth"], "1990-05-15")

    def test_update_no_valid_fields(self):
        import customer as ops
        cid = ops.create_customer("Ivy", "ivy@example.com")
        result = ops.update_customer(cid, nonexistent_field="value")
        self.assertFalse(result)

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

    def test_cascade_delete_removes_policies(self):
        import customer as cust
        import policy as pol
        cid = cust.create_customer("Cascade", "cascade@example.com")
        pid, _ = pol.create_policy(cid, "auto", 10_000, 200.0,
                                   "2024-01-01", "2025-01-01")
        cust.delete_customer(cid)
        self.assertIsNone(pol.get_policy(pid))


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

    def test_no_dob_returns_neutral_multiplier(self):
        from premium import calculate_premium
        # No DOB: age multiplier is 1.0 (neutral), matching an age 25-39 customer
        dob_neutral = date(date.today().year - 30, 1, 1).isoformat()
        p_no_dob = calculate_premium("life", 100_000, None, 12)
        p_age25_39 = calculate_premium("life", 100_000, dob_neutral, 12)
        self.assertAlmostEqual(p_no_dob, p_age25_39, places=2)

    def test_invalid_dob_returns_neutral_multiplier(self):
        from premium import calculate_premium
        # Invalid date string falls back to multiplier 1.0
        p_invalid = calculate_premium("life", 100_000, "not-a-date", 12)
        p_neutral = calculate_premium("life", 100_000, None, 12)
        self.assertAlmostEqual(p_invalid, p_neutral, places=2)

    def test_age_under_25_multiplier(self):
        from premium import calculate_premium
        # age ~16 -> multiplier 0.9 (cheaper than 25-39)
        dob_teen = date(date.today().year - 16, 1, 1).isoformat()
        dob_adult = date(date.today().year - 30, 1, 1).isoformat()
        p_teen = calculate_premium("life", 100_000, dob_teen, 12)
        p_adult = calculate_premium("life", 100_000, dob_adult, 12)
        self.assertLess(p_teen, p_adult)

    def test_age_40_to_54_multiplier(self):
        from premium import calculate_premium
        # age ~48 -> multiplier 1.3 (more expensive than 25-39)
        dob_mid = date(date.today().year - 48, 1, 1).isoformat()
        dob_young = date(date.today().year - 30, 1, 1).isoformat()
        p_mid = calculate_premium("health", 100_000, dob_mid, 12)
        p_young = calculate_premium("health", 100_000, dob_young, 12)
        self.assertGreater(p_mid, p_young)

    def test_age_55_to_64_multiplier(self):
        from premium import calculate_premium
        # age ~60 -> multiplier 1.7 (more expensive than 40-54)
        dob_senior = date(date.today().year - 60, 1, 1).isoformat()
        dob_mid = date(date.today().year - 48, 1, 1).isoformat()
        p_senior = calculate_premium("health", 100_000, dob_senior, 12)
        p_mid = calculate_premium("health", 100_000, dob_mid, 12)
        self.assertGreater(p_senior, p_mid)

    def test_all_policy_types(self):
        from premium import calculate_premium
        for ptype in ("life", "health", "auto", "home", "travel"):
            p = calculate_premium(ptype, 50_000)
            self.assertGreater(p, 0, msg=f"Premium for {ptype} should be positive")

    def test_age_multiplier_not_applied_to_auto_home_travel(self):
        from premium import calculate_premium
        # For auto/home/travel the age multiplier is never applied
        dob_young = date(date.today().year - 16, 1, 1).isoformat()
        dob_old = date(date.today().year - 70, 1, 1).isoformat()
        p_young = calculate_premium("auto", 20_000, dob_young, 12)
        p_old = calculate_premium("auto", 20_000, dob_old, 12)
        self.assertAlmostEqual(p_young, p_old, places=2)

    def test_policy_type_case_insensitive(self):
        from premium import calculate_premium
        p_lower = calculate_premium("auto", 20_000, duration_months=12)
        p_upper = calculate_premium("AUTO", 20_000, duration_months=12)
        self.assertAlmostEqual(p_lower, p_upper, places=2)


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

    def test_default_status_is_active(self):
        import policy as ops
        cid = self._make_customer()
        pid, _ = ops.create_policy(cid, "home", 100_000, 800.0,
                                   "2024-01-01", "2025-01-01")
        self.assertEqual(ops.get_policy(pid)["status"], "active")

    def test_get_nonexistent(self):
        import policy as ops
        self.assertIsNone(ops.get_policy(99999))

    def test_get_by_number(self):
        import policy as ops
        cid = self._make_customer()
        pid, pnum = ops.create_policy(cid, "life", 200_000, 1000.0,
                                      "2024-01-01", "2025-01-01")
        p = ops.get_policy_by_number(pnum)
        self.assertIsNotNone(p)
        self.assertEqual(p["id"], pid)

    def test_get_by_number_nonexistent(self):
        import policy as ops
        self.assertIsNone(ops.get_policy_by_number("POL-DOESNOTEXIST"))

    def test_list_all(self):
        import policy as ops
        cid = self._make_customer()
        ops.create_policy(cid, "auto", 20_000, 300.0, "2024-01-01", "2025-01-01")
        all_policies = ops.list_policies()
        self.assertGreaterEqual(len(all_policies), 1)

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

    def test_update_coverage_and_premium(self):
        import policy as ops
        cid = self._make_customer()
        pid, _ = ops.create_policy(cid, "travel", 10_000, 300.0,
                                   "2024-01-01", "2024-06-01")
        ops.update_policy(pid, coverage_amount=15_000, premium_amount=450.0)
        p = ops.get_policy(pid)
        self.assertEqual(p["coverage_amount"], 15_000)
        self.assertEqual(p["premium_amount"], 450.0)

    def test_update_no_valid_fields(self):
        import policy as ops
        cid = self._make_customer()
        pid, _ = ops.create_policy(cid, "auto", 20_000, 300.0,
                                   "2024-01-01", "2025-01-01")
        result = ops.update_policy(pid, nonexistent_field="value")
        self.assertFalse(result)

    def test_delete(self):
        import policy as ops
        cid = self._make_customer()
        pid, _ = ops.create_policy(cid, "travel", 10_000, 300.0,
                                   "2024-01-01", "2024-06-01")
        ops.delete_policy(pid)
        self.assertIsNone(ops.get_policy(pid))

    def test_cascade_delete_removes_claims(self):
        import policy as pol
        import claims as clm
        cid = self._make_customer()
        pid, _ = pol.create_policy(cid, "auto", 50_000, 750.0,
                                   "2024-01-01", "2025-01-01")
        clm_id, _ = clm.create_claim(pid, "2024-06-01", "Accident", 3000.0)
        pol.delete_policy(pid)
        self.assertIsNone(clm.get_claim(clm_id))


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

    def test_get_nonexistent(self):
        import claims as ops
        self.assertIsNone(ops.get_claim(99999))

    def test_get_by_number(self):
        import claims as ops
        pid = self._make_policy()
        clm_id, clm_num = ops.create_claim(pid, "2024-06-01", "Fire", 10_000.0)
        c = ops.get_claim_by_number(clm_num)
        self.assertIsNotNone(c)
        self.assertEqual(c["id"], clm_id)

    def test_get_by_number_nonexistent(self):
        import claims as ops
        self.assertIsNone(ops.get_claim_by_number("CLM-DOESNOTEXIST"))

    def test_list_all(self):
        import claims as ops
        pid = self._make_policy()
        ops.create_claim(pid, "2024-06-01", "Claim A", 1000.0)
        all_claims = ops.list_claims()
        self.assertGreaterEqual(len(all_claims), 1)

    def test_approve(self):
        import claims as ops
        pid = self._make_policy()
        clm_id, _ = ops.create_claim(pid, "2024-06-01", "Theft", 8000.0)
        ops.update_claim(clm_id, status="approved", amount_approved=7500.0)
        c = ops.get_claim(clm_id)
        self.assertEqual(c["status"], "approved")
        self.assertEqual(c["amount_approved"], 7500.0)

    def test_reject(self):
        import claims as ops
        pid = self._make_policy()
        clm_id, _ = ops.create_claim(pid, "2024-06-01", "Dispute", 2000.0)
        ops.update_claim(clm_id, status="rejected")
        self.assertEqual(ops.get_claim(clm_id)["status"], "rejected")

    def test_update_description(self):
        import claims as ops
        pid = self._make_policy()
        clm_id, _ = ops.create_claim(pid, "2024-06-01", "Initial desc", 500.0)
        ops.update_claim(clm_id, description="Updated description")
        self.assertEqual(ops.get_claim(clm_id)["description"], "Updated description")

    def test_update_no_valid_fields(self):
        import claims as ops
        pid = self._make_policy()
        clm_id, _ = ops.create_claim(pid, "2024-06-01", "Test", 100.0)
        result = ops.update_claim(clm_id, nonexistent_field="value")
        self.assertFalse(result)

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

    def test_summary_empty_db(self):
        import reports
        r = reports.summary_report()
        self.assertEqual(r["total_customers"], 0)
        self.assertEqual(r["total_policies"], 0)
        self.assertEqual(r["total_claims"], 0)
        self.assertEqual(r["total_coverage"], 0)
        self.assertEqual(r["total_premiums"], 0)
        self.assertEqual(r["claims_by_status"], [])

    def test_summary(self):
        import reports
        self._seed()
        r = reports.summary_report()
        self.assertGreaterEqual(r["total_customers"], 1)
        self.assertGreaterEqual(r["total_policies"], 1)
        self.assertGreaterEqual(r["total_claims"], 1)
        self.assertGreater(r["total_coverage"], 0)
        self.assertGreater(r["total_premiums"], 0)

    def test_summary_claims_by_status(self):
        import reports
        import claims as clm
        self._seed()
        pid = clm.list_claims()[0]["policy_id"]
        clm_id, _ = clm.create_claim(pid, "2024-07-01", "Another claim", 500.0)
        clm.update_claim(clm_id, status="approved", amount_approved=400.0)
        r = reports.summary_report()
        statuses = {row["status"] for row in r["claims_by_status"]}
        self.assertIn("pending", statuses)
        self.assertIn("approved", statuses)

    def test_policies_by_type(self):
        import reports
        self._seed()
        rows = reports.policies_by_type_report()
        self.assertGreater(len(rows), 0)

    def test_policies_by_type_multiple_types(self):
        import customer as cust
        import policy as pol
        import reports
        cid = cust.create_customer("Multi Policy User", "multi@example.com")
        pol.create_policy(cid, "auto", 20_000, 300.0, "2024-01-01", "2025-01-01")
        pol.create_policy(cid, "home", 150_000, 1200.0, "2024-01-01", "2025-01-01")
        pol.create_policy(cid, "life", 200_000, 800.0, "2024-01-01", "2025-01-01")
        rows = reports.policies_by_type_report()
        types_in_report = {r["policy_type"] for r in rows}
        self.assertIn("auto", types_in_report)
        self.assertIn("home", types_in_report)
        self.assertIn("life", types_in_report)

    def test_top_claims(self):
        import reports
        self._seed()
        rows = reports.top_claims_report(5)
        self.assertGreater(len(rows), 0)

    def test_top_claims_limit(self):
        import customer as cust
        import policy as pol
        import claims as clm
        import reports
        cid = cust.create_customer("Top Claims User", "topclaims@example.com")
        pid, _ = pol.create_policy(cid, "auto", 50_000, 750.0,
                                   "2024-01-01", "2025-01-01")
        for i in range(5):
            clm.create_claim(pid, "2024-06-01", f"Claim {i}", float((i + 1) * 1000))
        rows = reports.top_claims_report(3)
        self.assertEqual(len(rows), 3)

    def test_top_claims_empty_db(self):
        import reports
        rows = reports.top_claims_report(10)
        self.assertEqual(rows, [])

    def test_policies_by_type_empty_db(self):
        import reports
        rows = reports.policies_by_type_report()
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
