import unittest

import commission_transfer as ct


class _TransferResult:
    def __init__(self):
        self.id = "tr_123"
        self.amount = 50000
        self.currency = "ils"
        self.destination = "acct_123"
        self.livemode = False


class _Transfers:
    def __init__(self):
        self.last_payload = None
        self.last_options = None

    def create(self, payload, options=None):
        self.last_payload = payload
        self.last_options = options
        return _TransferResult()


class _Client:
    def __init__(self):
        self.v1 = type("V1", (), {"transfers": _Transfers()})()


class _StripeError(Exception):
    pass


class _FailingTransfers:
    def create(self, payload, options=None):
        raise _StripeError("stripe failed")


class _FailingClient:
    def __init__(self):
        self.v1 = type("V1", (), {"transfers": _FailingTransfers()})()


class TestCommissionTransfer(unittest.TestCase):
    def test_success_with_ils_agorot(self):
        client = _Client()

        result = ct.transfer_commission(
            client=client,
            connected_account_id="acct_123",
            commission_id="AHLIA-2026-001",
            amount_minor=50000,
            currency="ILS",
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["currency"], "ils")
        self.assertEqual(client.v1.transfers.last_payload["amount"], 50000)
        self.assertEqual(client.v1.transfers.last_payload["currency"], "ils")
        self.assertEqual(
            client.v1.transfers.last_options["idempotency_key"],
            "commission:AHLIA-2026-001",
        )

    def test_rejects_non_ils_currency(self):
        client = _Client()
        with self.assertRaises(ValueError):
            ct.transfer_commission(
                client=client,
                connected_account_id="acct_123",
                commission_id="AHLIA-2026-001",
                amount_minor=100,
                currency="usd",
            )

    def test_rejects_invalid_amount(self):
        client = _Client()
        with self.assertRaises(ValueError):
            ct.transfer_commission(
                client=client,
                connected_account_id="acct_123",
                commission_id="AHLIA-2026-001",
                amount_minor=0,
            )

    def test_rejects_empty_commission_id(self):
        client = _Client()
        with self.assertRaises(ValueError):
            ct.transfer_commission(
                client=client,
                connected_account_id="acct_123",
                commission_id=" ",
                amount_minor=100,
            )

    def test_handles_stripe_error(self):
        original_stripe = ct.stripe
        try:
            ct.stripe = type("StripeModule", (), {"StripeError": _StripeError})
            result = ct.transfer_commission(
                client=_FailingClient(),
                connected_account_id="acct_123",
                commission_id="AHLIA-2026-001",
                amount_minor=100,
            )
            self.assertFalse(result["success"])
            self.assertIn("stripe failed", result["error"])
        finally:
            ct.stripe = original_stripe


if __name__ == "__main__":
    unittest.main(verbosity=2)
