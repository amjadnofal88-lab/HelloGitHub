# Secure transfer configuration

This example keeps the IBAN and transfer reference out of Git history and logs.
It validates configuration only; it does not initiate or authorize a bank transfer.

1. Commit `secure_transfer_config.py`, `.gitignore`, and this README.
2. Keep `.env.example` as placeholders only.
3. In the GitHub repository, create Actions secrets named `BANK_IBAN` and
   `BANK_TRANSFER_REFERENCE`.
4. If desired, copy `github-actions-secret-example.yml` to
   `.github/workflows/validate-transfer-config.yml`.

Never print either value, place it in an issue, or commit it to a tracked file.
