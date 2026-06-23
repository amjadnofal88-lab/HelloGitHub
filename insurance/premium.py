"""Premium calculation logic based on policy type and customer details."""

from datetime import date

# Base annual premium rates per 1000 of coverage
BASE_RATES = {
    "life":     0.50,
    "health":   2.00,
    "auto":     1.50,
    "home":     0.80,
    "travel":   3.00,
}

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


def calculate_premium(
    policy_type: str,
    coverage_amount: float,
    date_of_birth: str = None,
    duration_months: int = 12,
) -> float:
    """Return the total premium for the given policy parameters."""
    policy_type = policy_type.lower()
    if policy_type not in BASE_RATES:
        raise ValueError(
            f"Unknown policy type '{policy_type}'. "
            f"Valid types: {', '.join(BASE_RATES)}"
        )

    rate = BASE_RATES[policy_type]
    annual_premium = (coverage_amount / 1000) * rate

    if policy_type in ("life", "health"):
        annual_premium *= _age_multiplier(date_of_birth)

    # Scale by duration
    total = annual_premium * (duration_months / 12)
    return round(total, 2)
