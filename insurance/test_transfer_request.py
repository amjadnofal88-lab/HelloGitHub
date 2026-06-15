# -*- coding: utf-8 -*-
"""
Test suite for transfer request module.
Tests validation, monthly cap enforcement, edge cases, and beneficiary handling.
"""

import pytest
from datetime import date, timedelta
from dataclasses import replace

from insurance.transfer_request import (
    BeneficiaryAccount,
    TransferRequest,
    MONTHLY_CAP,
    AMJAD,
    request_monthly_transfer,
)


# ========== Beneficiary Tests ==========

class TestBeneficiaryAccount:
    """Tests for BeneficiaryAccount dataclass."""

    def test_beneficiary_creation(self):
        """Should create a beneficiary account with all fields."""
        b = BeneficiaryAccount(
            holder_name="أحمد محمد",
            national_id="123456789",
            account_number="999888",
            branch="عمّان",
        )
        assert b.holder_name == "أحمد محمد"
        assert b.national_id == "123456789"
        assert b.account_number == "999888"
        assert b.branch == "عمّان"

    def test_beneficiary_is_frozen(self):
        """Beneficiary should be immutable (frozen=True)."""
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            AMJAD.holder_name = "Other Name"

    def test_amjad_predefined_account(self):
        """Predefined AMJAD account should have correct data."""
        assert AMJAD.holder_name == "امجد محمود شعبان نوفل"
        assert AMJAD.national_id == "853403640"
        assert AMJAD.account_number == "668111"
        assert AMJAD.branch == "القصبة - رام الله"


# ========== TransferRequest Validation Tests ==========

class TestTransferRequestValidation:
    """Tests for TransferRequest validation rules."""

    def test_valid_transfer_request(self):
        """Should create a valid transfer request at or below the cap."""
        req = TransferRequest(
            beneficiary=AMJAD,
            amount=25_000,
            period=date(2025, 1, 15),
        )
        req.validate()  # Should not raise

    def test_amount_exactly_at_cap(self):
        """Should allow amount exactly equal to MONTHLY_CAP."""
        req = TransferRequest(
            beneficiary=AMJAD,
            amount=MONTHLY_CAP,
            period=date(2025, 1, 1),
        )
        req.validate()  # Should not raise

    def test_amount_exceeds_cap(self):
        """Should reject amount exceeding MONTHLY_CAP."""
        req = TransferRequest(
            beneficiary=AMJAD,
            amount=MONTHLY_CAP + 1,
            period=date(2025, 1, 1),
        )
        with pytest.raises(ValueError) as exc_info:
            req.validate()
        assert "يتجاوز السقف الشهري" in str(exc_info.value)
        assert str(MONTHLY_CAP) in str(exc_info.value)

    def test_amount_zero(self):
        """Should reject zero amount."""
        req = TransferRequest(
            beneficiary=AMJAD,
            amount=0,
            period=date(2025, 1, 1),
        )
        with pytest.raises(ValueError) as exc_info:
            req.validate()
        assert "يجب أن يكون أكبر من صفر" in str(exc_info.value)

    def test_amount_negative(self):
        """Should reject negative amount."""
        req = TransferRequest(
            beneficiary=AMJAD,
            amount=-100,
            period=date(2025, 1, 1),
        )
        with pytest.raises(ValueError) as exc_info:
            req.validate()
        assert "يجب أن يكون أكبر من صفر" in str(exc_info.value)

    def test_amount_very_small_positive(self):
        """Should allow very small positive amounts."""
        req = TransferRequest(
            beneficiary=AMJAD,
            amount=0.01,
            period=date(2025, 1, 1),
        )
        req.validate()  # Should not raise

    def test_amount_large_but_within_cap(self):
        """Should allow large amounts within cap."""
        req = TransferRequest(
            beneficiary=AMJAD,
            amount=49_999.99,
            period=date(2025, 1, 1),
        )
        req.validate()  # Should not raise


# ========== TransferRequest Summary Tests ==========

class TestTransferRequestSummary:
    """Tests for TransferRequest.summary() output."""

    def test_summary_format_arabic(self):
        """Summary should include amount, period, beneficiary name, and account."""
        req = TransferRequest(
            beneficiary=AMJAD,
            amount=30_000,
            period=date(2025, 3, 15),
        )
        summary = req.summary()
        assert "30,000" in summary or "30000" in summary
        assert "03/2025" in summary
        assert "امجد محمود شعبان نوفل" in summary
        assert "668111" in summary
        assert "القصبة - رام الله" in summary

    def test_summary_with_note(self):
        """Summary should be generated even if note is present."""
        req = TransferRequest(
            beneficiary=AMJAD,
            amount=10_000,
            period=date(2025, 6, 1),
            note="دفعة شهرية",
        )
        summary = req.summary()
        assert "10,000" in summary or "10000" in summary

    def test_summary_different_beneficiary(self):
        """Summary should adapt to different beneficiary."""
        other = BeneficiaryAccount(
            holder_name="علي أحمد",
            national_id="987654321",
            account_number="111222",
            branch="عمّان",
        )
        req = TransferRequest(
            beneficiary=other,
            amount=5_000,
            period=date(2025, 1, 10),
        )
        summary = req.summary()
        assert "علي أحمد" in summary
        assert "111222" in summary


# ========== request_monthly_transfer Helper Tests ==========

class TestRequestMonthlyTransferHelper:
    """Tests for the request_monthly_transfer() helper function."""

    def test_helper_with_valid_amount(self):
        """Helper should create and validate a request with valid amount."""
        req = request_monthly_transfer(20_000)
        assert req.amount == 20_000
        assert req.beneficiary == AMJAD
        assert req.period is not None

    def test_helper_uses_today_as_default_period(self):
        """Helper should use today's date if no period specified."""
        req = request_monthly_transfer(15_000)
        assert req.period.month == date.today().month
        assert req.period.year == date.today().year

    def test_helper_accepts_custom_period(self):
        """Helper should accept a custom period."""
        custom_date = date(2025, 6, 15)
        req = request_monthly_transfer(10_000, period=custom_date)
        assert req.period == custom_date

    def test_helper_accepts_note(self):
        """Helper should accept and store a note."""
        req = request_monthly_transfer(
            25_000,
            note="عمولات شهرية"
        )
        assert req.note == "عمولات شهرية"

    def test_helper_rejects_invalid_amount(self):
        """Helper should reject invalid amounts during validation."""
        with pytest.raises(ValueError):
            request_monthly_transfer(MONTHLY_CAP + 100)

    def test_helper_rejects_zero_amount(self):
        """Helper should reject zero amount."""
        with pytest.raises(ValueError):
            request_monthly_transfer(0)

    def test_helper_at_cap(self):
        """Helper should accept amount exactly at cap."""
        req = request_monthly_transfer(MONTHLY_CAP)
        assert req.amount == MONTHLY_CAP


# ========== Edge Cases and Integration Tests ==========

class TestEdgeCases:
    """Tests for edge cases and integration scenarios."""

    def test_monthly_cap_is_correct_value(self):
        """MONTHLY_CAP should be 50,000."""
        assert MONTHLY_CAP == 50_000

    def test_transfer_request_note_defaults_to_empty(self):
        """TransferRequest note should default to empty string."""
        req = TransferRequest(
            beneficiary=AMJAD,
            amount=1_000,
            period=date.today(),
        )
        assert req.note == ""

    def test_float_precision_at_cap(self):
        """Should handle float precision near cap boundary."""
        # Just barely under cap
        req1 = TransferRequest(
            beneficiary=AMJAD,
            amount=MONTHLY_CAP - 0.01,
            period=date.today(),
        )
        req1.validate()

        # Just barely over cap
        req2 = TransferRequest(
            beneficiary=AMJAD,
            amount=MONTHLY_CAP + 0.01,
            period=date.today(),
        )
        with pytest.raises(ValueError):
            req2.validate()

    def test_beneficiary_immutability_prevents_modification(self):
        """Frozen beneficiary should prevent field modification."""
        b = AMJAD
        # Attempt to modify should fail
        with pytest.raises(Exception):
            b.holder_name = "Modified"

    def test_multiple_periods_same_beneficiary(self):
        """Should support multiple transfer requests for same beneficiary."""
        req_jan = request_monthly_transfer(
            30_000,
            period=date(2025, 1, 1),
            note="January"
        )
        req_feb = request_monthly_transfer(
            40_000,
            period=date(2025, 2, 1),
            note="February"
        )
        assert req_jan.period.month == 1
        assert req_feb.period.month == 2
        assert req_jan.beneficiary == req_feb.beneficiary

    def test_different_dates_same_month_produce_same_month_in_summary(self):
        """Different dates in same month should produce same month in summary."""
        req1 = TransferRequest(
            beneficiary=AMJAD,
            amount=10_000,
            period=date(2025, 5, 1),
        )
        req2 = TransferRequest(
            beneficiary=AMJAD,
            amount=10_000,
            period=date(2025, 5, 31),
        )
        summary1 = req1.summary()
        summary2 = req2.summary()
        # Both should contain "05/2025"
        assert "05/2025" in summary1
        assert "05/2025" in summary2


# ========== Parametrized Tests ==========

class TestParametrized:
    """Parametrized tests for comprehensive coverage."""

    @pytest.mark.parametrize("amount", [
        1,
        100,
        1_000,
        10_000,
        25_000,
        49_999,
        50_000,
    ])
    def test_valid_amounts(self, amount):
        """All amounts from 1 to MONTHLY_CAP should be valid."""
        req = request_monthly_transfer(amount)
        assert req.amount == amount

    @pytest.mark.parametrize("amount", [
        -1,
        -100,
        -50_000,
        0,
        50_000.01,
        50_001,
        100_000,
    ])
    def test_invalid_amounts(self, amount):
        """All amounts outside [0, MONTHLY_CAP] should raise ValueError."""
        with pytest.raises(ValueError):
            request_monthly_transfer(amount)

    @pytest.mark.parametrize("year,month,day", [
        (2025, 1, 1),
        (2025, 6, 15),
        (2025, 12, 31),
        (2026, 2, 28),
    ])
    def test_various_dates(self, year, month, day):
        """Should accept various valid dates."""
        d = date(year, month, day)
        req = TransferRequest(
            beneficiary=AMJAD,
            amount=20_000,
            period=d,
        )
        req.validate()
        assert req.period == d


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
