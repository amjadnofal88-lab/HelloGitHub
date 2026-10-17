import unittest

from werkzeug.security import generate_password_hash

from unified_admin import create_app
from unified_admin.extensions import db
from unified_admin.models import Claim, User


class BaseCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        # Force AI offline-fallback mode regardless of the ambient environment.
        self.app.config["ANTHROPIC_API_KEY"] = None
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def _login_admin(self, password="admin123"):
        with self.app.app_context():
            User.query.delete()
            db.session.commit()
        resp = self.client.post(
            "/auth/bootstrap-admin", json={"username": "admin", "password": password}
        )
        self.assertIn(resp.status_code, (201, 409))
        login = self.client.post(
            "/auth/login", data={"username": "admin", "password": password}, follow_redirects=False
        )
        self.assertEqual(login.status_code, 302)

    def _login_employee(self, password="employee123"):
        with self.app.app_context():
            db.session.add(
                User(
                    username="employee",
                    password_hash=generate_password_hash(password),
                    role="employee",
                )
            )
            db.session.commit()
        login = self.client.post(
            "/auth/login", data={"username": "employee", "password": password}, follow_redirects=False
        )
        self.assertEqual(login.status_code, 302)


class ClaimsTestCase(BaseCase):
    def _create_claim(self, **overrides):
        body = {
            "holder_name": "John Smith",
            "policy_number": "POL-2024-0001",
            "date_filed": "2024-05-10",
            "amount": 4500,
            "description": "Rear-end collision.",
        }
        body.update(overrides)
        return self.client.post("/insurance/claims", json=body)

    def test_create_and_list_claims(self):
        self._login_admin()
        resp = self._create_claim()
        self.assertEqual(resp.status_code, 200)
        listing = self.client.get("/insurance/claims", headers={"Accept": "application/json"})
        data = listing.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["holder_name"], "John Smith")
        self.assertEqual(data[0]["status"], "pending")
        self.assertTrue(data[0]["claim_number"].startswith("CLM-"))

    def test_status_filter(self):
        self._login_admin()
        self._create_claim()
        pending = self.client.get(
            "/insurance/claims?status=pending", headers={"Accept": "application/json"}
        )
        self.assertEqual(len(pending.get_json()), 1)
        approved = self.client.get(
            "/insurance/claims?status=approved", headers={"Accept": "application/json"}
        )
        self.assertEqual(len(approved.get_json()), 0)

    def test_status_workflow(self):
        self._login_admin()
        self._create_claim()
        with self.app.app_context():
            number = Claim.query.first().claim_number

        ok = self.client.patch(f"/insurance/claims/{number}/status", json={"status": "approved"})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.get_json()["status"], "approved")

        paid = self.client.patch(f"/insurance/claims/{number}/status", json={"status": "paid"})
        self.assertEqual(paid.status_code, 200)

    def test_illegal_transition_rejected(self):
        self._login_admin()
        self._create_claim()
        with self.app.app_context():
            number = Claim.query.first().claim_number
        # pending -> paid is not allowed (must go through approved).
        bad = self.client.patch(f"/insurance/claims/{number}/status", json={"status": "paid"})
        self.assertEqual(bad.status_code, 409)

    def test_employee_cannot_create_claim(self):
        self._login_employee()
        resp = self._create_claim()
        self.assertEqual(resp.status_code, 403)


class CustomerPolicyMutationTestCase(BaseCase):
    def test_customer_edit_and_delete(self):
        self._login_admin()
        self.client.post(
            "/insurance/customers",
            json={"name": "Jane", "email": "jane@example.com", "dob": "1990-01-01", "address": "1 St"},
        )
        rows = self.client.get("/insurance/customers", headers={"Accept": "application/json"}).get_json()
        cid = rows[0]["id"]
        self.assertEqual(rows[0]["dob"], "1990-01-01")

        upd = self.client.put(f"/insurance/customers/{cid}", json={"phone": "555"})
        self.assertEqual(upd.status_code, 200)
        self.assertEqual(upd.get_json()["phone"], "555")

        delete = self.client.delete(f"/insurance/customers/{cid}")
        self.assertEqual(delete.status_code, 200)
        rows = self.client.get("/insurance/customers", headers={"Accept": "application/json"}).get_json()
        self.assertEqual(len(rows), 0)

    def test_policy_new_fields_roundtrip(self):
        self._login_admin()
        self.client.post(
            "/insurance/policies",
            json={
                "holder_name": "Bob",
                "policy_type": "auto",
                "effective_date": "2024-01-01",
                "expiry_date": "2025-01-01",
                "premium_amount": 1200,
                "status": "active",
            },
        )
        rows = self.client.get("/insurance/policies", headers={"Accept": "application/json"}).get_json()
        self.assertEqual(rows[0]["holder_name"], "Bob")
        self.assertEqual(rows[0]["policy_type"], "auto")
        self.assertEqual(rows[0]["effective_date"], "2024-01-01")

    def test_employee_cannot_delete_policy(self):
        self._login_admin()
        self.client.post("/insurance/policies", json={"holder_name": "X", "premium_amount": 10})
        pid = self.client.get("/insurance/policies", headers={"Accept": "application/json"}).get_json()[0]["id"]
        # switch to an employee session
        self._login_employee()
        resp = self.client.delete(f"/insurance/policies/{pid}")
        self.assertEqual(resp.status_code, 403)


class DashboardSummaryTestCase(BaseCase):
    def test_summary_shape(self):
        self._login_admin()
        self.client.post(
            "/insurance/policies",
            json={"holder_name": "A", "policy_type": "auto", "premium_amount": 100, "status": "active"},
        )
        self.client.post(
            "/insurance/claims",
            json={"holder_name": "A", "policy_number": "POL-X", "amount": 500, "date_filed": "2024-01-01"},
        )
        resp = self.client.get("/insurance/api/dashboard-summary")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        for key in ("total_policies", "active_policies", "open_claims", "expiring_soon",
                    "recent_policies", "recent_claims"):
            self.assertIn(key, data)
        self.assertEqual(data["total_policies"], 1)
        self.assertEqual(data["active_policies"], 1)
        self.assertEqual(data["open_claims"], 1)

    def test_paid_and_pending_totals(self):
        self._login_admin()
        self.client.post("/insurance/claims", json={"holder_name": "A", "amount": 500})
        self.client.post(
            "/insurance/claims", json={"holder_name": "B", "amount": 1000, "claim_number": "CLM-PAY-1"}
        )
        self.client.patch("/insurance/claims/CLM-PAY-1/status", json={"status": "approved"})
        self.client.patch("/insurance/claims/CLM-PAY-1/status", json={"status": "paid"})

        data = self.client.get("/insurance/api/dashboard-summary").get_json()
        self.assertEqual(data["pending_total"], 500.0)
        self.assertEqual(data["paid_total"], 1000.0)


class AigRouteTestCase(BaseCase):
    def test_login_page_public(self):
        resp = self.client.get("/aig/SSO/Login/GUI/Frmlogin.html")
        self.assertEqual(resp.status_code, 200)

    def test_dashboard_requires_login(self):
        resp = self.client.get("/aig/Insurance/GUI/FrmInsurance.html", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

    def test_dashboard_served_when_logged_in(self):
        self._login_admin()
        resp = self.client.get("/aig/Insurance/GUI/FrmInsurance.html")
        self.assertEqual(resp.status_code, 200)


class AiFallbackTestCase(BaseCase):
    def test_chat_fallback(self):
        self._login_admin()
        resp = self.client.post("/ai/chat", json={"message": "How many policies?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["source"], "fallback")
        self.assertTrue(data["reply"])

    def test_chat_requires_message(self):
        self._login_admin()
        resp = self.client.post("/ai/chat", json={})
        self.assertEqual(resp.status_code, 400)

    def test_risk_score_fallback(self):
        self._login_admin()
        resp = self.client.post(
            "/ai/risk-score", json={"policy_type": "auto", "coverage_amount": 50000, "age": 30}
        )
        data = resp.get_json()
        self.assertEqual(data["source"], "fallback")
        self.assertIn("suggested_premium", data)
        self.assertIn("risk_score", data)
        self.assertGreater(data["suggested_premium"], 0)

    def test_claims_triage_fallback(self):
        self._login_admin()
        resp = self.client.post(
            "/ai/claims-triage", json={"amount": 50000, "description": "possible fraud and arson"}
        )
        data = resp.get_json()
        self.assertEqual(data["recommendation"], "review")
        self.assertIn("reasons", data)

    def test_extract_document_fallback(self):
        self._login_admin()
        text = "Name: Jane Doe, email jane@example.com, DOB 1990-05-01, policy POL-2024-9999, amount $1,200"
        resp = self.client.post("/ai/extract-document", json={"text": text})
        data = resp.get_json()
        self.assertEqual(data.get("email"), "jane@example.com")
        self.assertEqual(data.get("dob"), "1990-05-01")
        self.assertEqual(data.get("policy_number"), "POL-2024-9999")
        self.assertEqual(data.get("amount"), 1200.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
