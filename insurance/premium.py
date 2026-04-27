"""Premium calculation logic based on policy type and customer details."""

from dataclasses import dataclass
from datetime import date

# Base annual premium rates per 100,000 of coverage
BASE_RATES = {
    "life":     0.50,
    "health":   2.00,
    "auto":     1.50,
    "home":     0.80,
    "travel":   3.00,
}


@dataclass
class PolicyData:
    """Input data required to calculate a premium."""
    base_rate: float
    coverage_amount: float
    duration_months: int


# Age-based multipliers for life/health
def _age_multiplier(date_of_birth: str) -> float:
    if not date_of_birth:
        return 1.0
    try:
        dob = date.fromisoformat(date_of_birth)
    except ValueError:
        return 1.0
    age = (date.today() - dob).days // 365
    if age < 25:
        return 0.9
    if age < 40:
        return 1.0
    if age < 55:
        return 1.3
    if age < 65:
        return 1.7
    return 2.2


def build_policy_data(
    policy_type: str,
    coverage_amount: float,
    duration_months: int = 12,
) -> PolicyData:
    """Return a :class:`PolicyData` for the given policy parameters.

    Raises :exc:`ValueError` for unknown policy types.
    """
    policy_type = policy_type.lower()
    if policy_type not in BASE_RATES:
        raise ValueError(
            f"Unknown policy type '{policy_type}'. "
            f"Valid types: {', '.join(BASE_RATES)}"
        )
    return PolicyData(
        base_rate=BASE_RATES[policy_type],
        coverage_amount=coverage_amount,
        duration_months=duration_months,
    )


def default_ai_recommendation(
    policy_type: str,
    date_of_birth: str = None,
) -> dict:
    """Return a default AI recommendation dict using age-based risk scoring."""
    policy_type = policy_type.lower()
    if policy_type in ("life", "health"):
        multiplier = _age_multiplier(date_of_birth)
    else:
        multiplier = 1.0
    return {"recommended_multiplier": multiplier}


def calculate_premium(data: PolicyData, ai: dict) -> float:
    """Return the total premium for the given policy data and AI recommendation."""
    base_rate = data.base_rate
    risk_multiplier = ai["recommended_multiplier"]
    coverage_factor = data.coverage_amount / 100000
    duration_factor = data.duration_months / 12

    premium = (
        base_rate
        * risk_multiplier
        * coverage_factor
        * duration_factor
    )

    return round(premium, 2)
