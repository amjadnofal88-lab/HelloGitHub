import os
import unittest
from datetime import date
from unittest.mock import patch

from werkzeug.security import check_password_hash, generate_password_hash

from unified_admin import create_app
from unified_admin.extensions import db
from unified_admin.models import Customer, Installment, Policy, User, VipCard


class BootstrapAdminTestCase(unittest.TestCase):
    """Tests for secure bootstrap admin password handling."""

    def test_no_hardcoded_password_in_source(self):
        """Ensure no hardcoded 'admin123' password exists in the module."""
        import unified_admin
        source = open(unified_admin.__file__).read()
        # Check that the literal hardcoded password is not in the source
        self.assertNotIn("admin123", source, 
                        "Hardcoded password 'admin123' found in unified_admin/__init__.py")

    def test_bootstrap_respects_initial_admin_password_env_var(self):
        """Verify that INITIAL_ADMIN_PASSWORD environment variable is used if set."""
        test_password = "MySecurePassword123!"
        with patch.dict(os.environ, {"INITIAL_ADMIN_PASSWORD": test_password}):
            app = create_app("testing")
            with app.app_context():
                admin_user = User.query.filter_by(username="admin").first()
                self.assertIsNotNone(admin_user, "Admin user should be created")
                # Verify the password hash matches the env var password
                self.assertTrue(check_password_hash(admin_user.password_hash, test_password),
                               "Admin password should match INITIAL_ADMIN_PASSWORD env var")

    def test_bootstrap_generates_random_password_when_env_var_not_set(self):
        """Verify that a secure random password is generated when INITIAL_ADMIN_PASSWORD is not set."""
        # Ensure the env var is not set
        with patch.dict(os.environ, {}, clear=False):
            if "INITIAL_ADMIN_PASSWORD" in os.environ:
                del os.environ["INITIAL_ADMIN_PASSWORD"]
            
            app = create_app("testing")
            with app.app_context():
                admin_user = User.query.filter_by(username="admin").first()
                self.assertIsNotNone(admin_user, "Admin user should be created")
                # Verify that the password hash is set (not empty)
                self.assertTrue(admin_user.password_hash, "Password hash should not be empty")
                # Verify it's not the old hardcoded password
                self.assertFalse(check_password_hash(admin_user.password_hash, "admin123"),
                                "Admin password should NOT be the old hardcoded 'admin123'")

    def test_bootstrap_warning_logged_when_using_generated_password(self):
        """Verify that a warning is logged when falling back to generated password."""
        with patch.dict(os.environ, {}, clear=False):
            if "INITIAL_ADMIN_PASSWORD" in os.environ:
                del os.environ["INITIAL_ADMIN_PASSWORD"]
            
            with patch('unified_admin.logger') as mock_logger:
                app = create_app("testing")
                # Check that warning was called
                mock_logger.warning.assert_called()
                call_args = mock_logger.warning.call_args[0][0]
                self.assertIn("No INITIAL_ADMIN_PASSWORD environment variable set", call_args)
                self.assertIn("Generated bootstrap admin password", call_args)


class UnifiedAdminTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def _bootstrap_and_login(self, password="admin123"):
        with self.app.app_context():
            User.query.delete()
            db.session.commit()
        resp = self.client.post("/auth/bootstrap-admin", json={"username": "admin", "password": password})
        self.assertIn(resp.status_code, (201, 409))
        login = self.client.post("/auth/login", data={"username": "admin", "password": password}, follow_redirects=False)
        self.assertEqual(login.status_code, 302)

    def test_login_required(self):
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.location)

    def test_dashboard_metrics(self):
        self._bootstrap_and_login()
        with self.app.app_context():
            customer = Customer(name="A", email="a@example.com", phone="1")
            db.session.add(customer)
            db.session.flush()
            policy = Policy(customer_id=customer.id, policy_number="POL-00000001", status="active", premium_amount=100)
            card = VipCard(customer_id=customer.id, card_number="VIP-00000001", status="active", monthly_fee=50)
            db.session.add_all([policy, card])
            db.session.flush()
            db.session.add_all(
                [
                    Installment(
                        customer_id=customer.id,
                        module_type="insurance",
                        reference_type="policy",
                        reference_id=policy.id,
                        amount=100,
                        due_date=date.today(),
                        status="paid",
                    ),
                    Installment(
                        customer_id=customer.id,
                        module_type="vip",
                        reference_type="vip_card",
                        reference_id=card.id,
                        amount=50,
                        due_date=date.today(),
                        status="pending",
                    ),
                ]
            )
            db.session.commit()

        resp = self.client.get("/api/dashboard")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["total_customers"], 1)
        self.assertEqual(data["active_policies"], 1)
        self.assertEqual(data["active_vip_cards"], 1)
        self.assertEqual(data["pending_installments"], 1)

    def test_insurance_vip_and_exports(self):
        self._bootstrap_and_login()
        self.client.post(
            "/insurance/customers",
            json={"name": "Customer 1", "email": "c1@example.com", "phone": "123"},
        )
        customers_resp = self.client.get("/insurance/customers", headers={"Accept": "application/json"})
        customer_id = customers_resp.get_json()[0]["id"]

        self.client.post(
            "/insurance/policies",
            json={"customer_id": customer_id, "policy_number": "POL-TEST001", "premium_amount": 200},
        )
        policies_resp = self.client.get("/insurance/policies", headers={"Accept": "application/json"})
        policy_id = policies_resp.get_json()[0]["id"]

        self.client.post(
            "/insurance/installments",
            json={"customer_id": customer_id, "reference_id": policy_id, "amount": 200, "due_date": "2026-06-15"},
        )

        self.client.post(
            "/vip/cards",
            json={"customer_id": customer_id, "card_number": "VIP-TEST001", "monthly_fee": 80},
        )
        cards_resp = self.client.get("/vip/cards", headers={"Accept": "application/json"})
        card_id = cards_resp.get_json()[0]["id"]

        self.client.post(
            "/vip/installments",
            json={"customer_id": customer_id, "reference_id": card_id, "amount": 80, "due_date": "2026-06-20"},
        )

        ins_report = self.client.get("/insurance/api/reports")
        vip_report = self.client.get("/vip/api/reports")
        self.assertEqual(ins_report.status_code, 200)
        self.assertEqual(vip_report.status_code, 200)

        xlsx = self.client.get("/reports/export/insurance.xlsx")
        pdf = self.client.get("/reports/export/dashboard.pdf")
        self.assertEqual(xlsx.status_code, 200)
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf.mimetype, "application/pdf")

    def test_employee_cannot_create_records(self):
        with self.app.app_context():
            db.session.add(
                User(
                    username="employee",
                    password_hash=generate_password_hash("employee123"),
                    role="employee",
                )
            )
            db.session.commit()

        login = self.client.post(
            "/auth/login",
            data={"username": "employee", "password": "employee123"},
            follow_redirects=False,
        )
        self.assertEqual(login.status_code, 302)

        response = self.client.post(
            "/insurance/customers",
            json={"name": "Unauthorized", "email": "u@example.com"},
        )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
