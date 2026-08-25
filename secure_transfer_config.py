"""Load bank-transfer identifiers without hardcoding or logging them."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass


_IBAN_PATTERN = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$")
_REFERENCE_PATTERN = re.compile(r"^[A-Za-z0-9._:/-]{1,80}$")


class ConfigurationError(RuntimeError):
    """Raised when required private configuration is missing or invalid."""


@dataclass(frozen=True)
class TransferConfig:
    iban: str
    transfer_reference: str


def _normalize_iban(value: str) -> str:
    return re.sub(r"\s+", "", value).upper()


def _has_valid_iban_checksum(iban: str) -> bool:
    rearranged = iban[4:] + iban[:4]
    expanded = "".join(
        str(ord(character) - 55) if character.isalpha() else character
        for character in rearranged
    )
    return int(expanded) % 97 == 1


def load_transfer_config() -> TransferConfig:
    """Read and validate private values supplied by the runtime environment."""
    iban = _normalize_iban(os.getenv("BANK_IBAN", ""))
    transfer_reference = os.getenv("BANK_TRANSFER_REFERENCE", "").strip()

    if not iban:
        raise ConfigurationError("BANK_IBAN is required")
    if not _IBAN_PATTERN.fullmatch(iban) or not _has_valid_iban_checksum(iban):
        raise ConfigurationError("BANK_IBAN is invalid")
    if not _REFERENCE_PATTERN.fullmatch(transfer_reference):
        raise ConfigurationError("BANK_TRANSFER_REFERENCE is missing or invalid")

    return TransferConfig(iban=iban, transfer_reference=transfer_reference)


if __name__ == "__main__":
    load_transfer_config()
    print("Private transfer configuration is valid; no values were logged.")
