# -*- coding: utf-8 -*-
"""
طلب تحويل مبالغ شهرية لا تزيد عن 50,000 إلى حساب محدد.
Monthly transfer request — capped at 50,000 per month.
"""

from dataclasses import dataclass, field
from datetime import date


# الحد الأقصى للتحويل في الشهر الواحد
MONTHLY_CAP = 50_000  # بالعملة المعتمدة (ش.إ / ILS)


@dataclass(frozen=True)
class BeneficiaryAccount:
    """بيانات الحساب المستفيد."""
    holder_name: str          # اسم صاحب الحساب
    national_id: str          # رقم الهوية
    account_number: str       # رقم الحساب
    branch: str               # الفرع


@dataclass
class TransferRequest:
    """طلب تحويل لشهر معيّن."""
    beneficiary: BeneficiaryAccount
    amount: float             # المبلغ المطلوب تحويله
    period: date              # الشهر (يكفي أي يوم ضمن الشهر)
    note: str = ""

    def validate(self) -> None:
        """يتحقق من القيود قبل تنفيذ التحويل."""
        if self.amount <= 0:
            raise ValueError("المبلغ يجب أن يكون أكبر من صفر.")
        if self.amount > MONTHLY_CAP:
            raise ValueError(
                f"المبلغ {self.amount:,.0f} يتجاوز السقف الشهري "
                f"{MONTHLY_CAP:,.0f}."
            )

    def summary(self) -> str:
        return (
            f"تحويل {self.amount:,.0f} عن شهر "
            f"{self.period.strftime('%m/%Y')} "
            f"إلى {self.beneficiary.holder_name} "
            f"(حساب {self.beneficiary.account_number} - "
            f"{self.beneficiary.branch})."
        )


# حساب امجد محمود شعبان نوفل
AMJAD = BeneficiaryAccount(
    holder_name="امجد محمود شعبان نوفل",
    national_id="853403640",
    account_number="668111",
    branch="القصبة - رام الله",
)


def request_monthly_transfer(amount: float, period: date | None = None,
                             note: str = "") -> TransferRequest:
    """ينشئ طلب تحويل شهري ويتحقق من السقف (50,000)."""
    req = TransferRequest(
        beneficiary=AMJAD,
        amount=amount,
        period=period or date.today(),
        note=note,
    )
    req.validate()
    return req


if __name__ == "__main__":
    # مثال: طلب تحويل 50,000 لهذا الشهر
    req = request_monthly_transfer(50_000, note="عمولات وساطة")
    print(req.summary())
    print("رقم الهوية:", req.beneficiary.national_id)
