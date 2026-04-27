from decimal import Decimal
from typing import Optional


def calculate_premium(base_rate: Decimal, coverage_amount: Decimal, risk_factor: Optional[float] = 1.0) -> Decimal:
    """Calculate the insurance premium for a given coverage amount and risk factor."""
    return base_rate * coverage_amount * Decimal(str(risk_factor))
