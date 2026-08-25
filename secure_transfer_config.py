"""Secure transfer configuration validation.

This module validates required configuration values for a transfer setup.
It does not initiate or authorize any bank transfer.
"""

from __future__ import annotations

import os
from typing import Dict, Tuple

REQUIRED_VARS = ("BANK_IBAN", "BANK_TRANSFER_REFERENCE")


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    placeholders = {
        "",
        "your_iban_here",
        "your_transfer_reference_here",
        "changeme",
        "placeholder",
    }
    return normalized in placeholders


def validate_transfer_config() -> Tuple[bool, Dict[str, str]]:
    """Validate required env vars without exposing their values."""
    errors: Dict[str, str] = {}

    for key in REQUIRED_VARS:
        raw = os.getenv(key)
        if raw is None or not raw.strip():
            errors[key] = "missing"
            continue
        if _is_placeholder(raw):
            errors[key] = "placeholder"

    return (len(errors) == 0, errors)


def main() -> int:
    ok, errors = validate_transfer_config()
    if ok:
        print("Transfer configuration is valid.")
        return 0

    print("Transfer configuration is invalid.")
    for key, reason in sorted(errors.items()):
        print(f"- {key}: {reason}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
