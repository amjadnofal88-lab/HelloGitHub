"""Stripe commission transfer helper (ILS/agorot only)."""

from __future__ import annotations

from typing import Any, Dict

try:
    import stripe  # type: ignore
except ImportError:  # pragma: no cover - optional at runtime in this repo
    stripe = None


def transfer_commission(
    client: Any,
    connected_account_id: str,
    commission_id: str,
    amount_minor: int,
    currency: str = "ils",
) -> Dict[str, Any]:
    """
    Create a Stripe transfer for an insurance commission.

    amount_minor is in agorot (smallest ILS unit):
      50000 = 500.00 ILS

    Notes:
      - A preconfigured Stripe client must be injected via `client`.
      - The optional `stripe` import is used only to detect `stripe.StripeError`.
      - Stripe API errors are returned as {"success": False, "error": ...}.
      - Non-Stripe exceptions are re-raised.
    """

    if not isinstance(commission_id, str) or not commission_id.strip():
        raise ValueError("commission_id is required")

    if not isinstance(connected_account_id, str) or not connected_account_id.strip():
        raise ValueError("connected_account_id is required")

    if isinstance(amount_minor, bool) or not isinstance(amount_minor, int) or amount_minor <= 0:
        raise ValueError("Commission amount must be a positive integer in agorot")

    normalized_currency = (currency or "").strip().lower()
    if normalized_currency != "ils":
        raise ValueError("Only ILS currency is supported for agorot transfers")

    try:
        transfer = client.v1.transfers.create(
            {
                "amount": amount_minor,
                "currency": normalized_currency,
                "destination": connected_account_id,
                "description": f"Insurance commission {commission_id}",
                "transfer_group": f"COMMISSION_{commission_id}",
                "metadata": {
                    "commission_id": commission_id,
                    "payment_type": "insurance_commission",
                },
            },
            options={
                "idempotency_key": f"commission:{commission_id}",
            },
        )

        return {
            "success": True,
            "transfer_id": transfer.id,
            "amount": transfer.amount,
            "currency": transfer.currency,
            "destination": transfer.destination,
            "live_mode": transfer.livemode,
        }

    except Exception as exc:
        if stripe is not None and isinstance(exc, stripe.StripeError):
            return {"success": False, "error": str(exc)}
        raise
