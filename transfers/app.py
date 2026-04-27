"""Flask REST API for the Transfers service.

Endpoints
---------
POST /transfers
    Create a new money transfer.

    Request body (JSON):
        {
            "beneficiary_name": "<string>",
            "account_number":   "<string>",
            "amount":           <positive number>
        }

    Response 201:
        {
            "id":               <int>,
            "reference":        "<TXN-…>",
            "beneficiary_name": "<string>",
            "account_number":   "<string>",
            "amount":           <number>,
            "status":           "pending",
            "created_at":       "<ISO datetime>"
        }

GET /transfers
    List all transfers.
"""

from flask import Flask, request, jsonify

from database import init_db
import transfers as txn_ops

app = Flask(__name__)

# Initialise the database on startup
with app.app_context():
    init_db()


def _error(message: str, status: int):
    return jsonify({"error": message}), status


@app.post("/transfers")
def create_transfer():
    try:
        data = request.get_json(force=False, silent=False)
    except Exception:
        data = None
    if not isinstance(data, dict):
        return _error("Request body must be valid JSON with Content-Type: application/json.", 400)

    beneficiary_name = data.get("beneficiary_name")
    account_number = data.get("account_number")
    amount = data.get("amount")

    # --- Validation ---
    if not beneficiary_name or not str(beneficiary_name).strip():
        return _error("beneficiary_name is required.", 400)

    if not account_number or not str(account_number).strip():
        return _error("account_number is required.", 400)

    if amount is None:
        return _error("amount is required.", 400)

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return _error("amount must be a numeric value.", 400)

    if amount <= 0:
        return _error("amount must be greater than zero.", 400)

    # --- Persist ---
    transfer = txn_ops.create_transfer(
        beneficiary_name=str(beneficiary_name).strip(),
        account_number=str(account_number).strip(),
        amount=amount,
    )

    return jsonify(transfer), 201


@app.get("/transfers")
def list_transfers():
    return jsonify(txn_ops.list_transfers()), 200


if __name__ == "__main__":
    app.run(debug=False)
