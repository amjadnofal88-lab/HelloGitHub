#!/usr/bin/env python3
"""Insurance Management System — CLI interface."""

import sys
from datetime import date, datetime

from database import init_db
import customer as cust_ops
import policy as pol_ops
import claims as clm_ops
import premium as prem_ops
import reports as rep_ops


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _input(prompt):
    return input(prompt).strip()


def _confirm(msg="Are you sure? (y/N): "):
    return _input(msg).lower() == "y"


def _fmt_date():
    return date.today().isoformat()


def _print_table(rows, columns):
    if not rows:
        print("  (no records found)")
        return
    widths = {col: len(col) for col in columns}
    for row in rows:
        for col in columns:
            widths[col] = max(widths[col], len(str(row.get(col, ""))))
    header = " | ".join(col.ljust(widths[col]) for col in columns)
    sep = "-+-".join("-" * widths[col] for col in columns)
    print(header)
    print(sep)
    for row in rows:
        print(" | ".join(str(row.get(col, "")).ljust(widths[col]) for col in columns))


# ---------------------------------------------------------------------------
# Customer menu
# ---------------------------------------------------------------------------

def menu_customers():
    while True:
        print("\n=== Customer Management ===")
        print("  1. List customers")
        print("  2. Add customer")
        print("  3. View customer")
        print("  4. Update customer")
        print("  5. Delete customer")
        print("  0. Back")
        choice = _input("Choice: ")

        if choice == "1":
            customers = cust_ops.list_customers()
            _print_table(customers, ["id", "name", "email", "phone", "date_of_birth"])

        elif choice == "2":
            name = _input("Name: ")
            email = _input("Email: ")
            phone = _input("Phone (optional): ") or None
            dob = _input("Date of birth (YYYY-MM-DD, optional): ") or None
            address = _input("Address (optional): ") or None
            try:
                cid = cust_ops.create_customer(name, email, phone, dob, address)
                print(f"✓ Customer created with ID {cid}")
            except Exception as e:
                print(f"✗ Error: {e}")

        elif choice == "3":
            cid = _input("Customer ID: ")
            c = cust_ops.get_customer(int(cid))
            if c:
                for k, v in c.items():
                    print(f"  {k}: {v}")
            else:
                print("Customer not found.")

        elif choice == "4":
            cid = _input("Customer ID to update: ")
            c = cust_ops.get_customer(int(cid))
            if not c:
                print("Customer not found.")
                continue
            print("Leave blank to keep existing value.")
            name = _input(f"Name [{c['name']}]: ") or c["name"]
            email = _input(f"Email [{c['email']}]: ") or c["email"]
            phone = _input(f"Phone [{c['phone']}]: ") or c["phone"]
            dob = _input(f"DOB [{c['date_of_birth']}]: ") or c["date_of_birth"]
            address = _input(f"Address [{c['address']}]: ") or c["address"]
            cust_ops.update_customer(int(cid), name=name, email=email,
                                     phone=phone, date_of_birth=dob, address=address)
            print("✓ Customer updated.")

        elif choice == "5":
            cid = _input("Customer ID to delete: ")
            if _confirm():
                cust_ops.delete_customer(int(cid))
                print("✓ Customer deleted.")

        elif choice == "0":
            break


# ---------------------------------------------------------------------------
# Policy menu
# ---------------------------------------------------------------------------

def menu_policies():
    while True:
        print("\n=== Policy Management ===")
        print("  1. List all policies")
        print("  2. List policies for a customer")
        print("  3. Add policy")
        print("  4. View policy")
        print("  5. Update policy status")
        print("  6. Delete policy")
        print("  0. Back")
        choice = _input("Choice: ")

        if choice == "1":
            policies = pol_ops.list_policies()
            _print_table(policies, ["id", "policy_number", "policy_type",
                                    "coverage_amount", "premium_amount",
                                    "start_date", "end_date", "status"])

        elif choice == "2":
            cid = _input("Customer ID: ")
            policies = pol_ops.list_policies(customer_id=int(cid))
            _print_table(policies, ["id", "policy_number", "policy_type",
                                    "coverage_amount", "premium_amount", "status"])

        elif choice == "3":
            cid = _input("Customer ID: ")
            c = cust_ops.get_customer(int(cid))
            if not c:
                print("Customer not found.")
                continue

            print(f"Policy types: life, health, auto, home, travel")
            ptype = _input("Policy type: ").lower()
            coverage = float(_input("Coverage amount: "))
            start = _input(f"Start date [{_fmt_date()}]: ") or _fmt_date()
            end = _input("End date (YYYY-MM-DD): ")

            # Calculate duration in months
            try:
                s = date.fromisoformat(start)
                e = date.fromisoformat(end)
                months = max(1, (e.year - s.year) * 12 + (e.month - s.month))
            except ValueError:
                months = 12

            try:
                calculated = prem_ops.calculate_premium(
                    ptype, coverage, c.get("date_of_birth"), months
                )
                print(f"  Calculated premium: ${calculated:.2f}")
                use_calc = _input("Use calculated premium? (Y/n): ").lower()
                if use_calc != "n":
                    premium = calculated
                else:
                    premium = float(_input("Enter premium amount: "))

                pid, pnum = pol_ops.create_policy(
                    int(cid), ptype, coverage, premium, start, end
                )
                print(f"✓ Policy created: {pnum} (ID {pid})")
            except Exception as e:
                print(f"✗ Error: {e}")

        elif choice == "4":
            pid = _input("Policy ID: ")
            p = pol_ops.get_policy(int(pid))
            if p:
                for k, v in p.items():
                    print(f"  {k}: {v}")
            else:
                print("Policy not found.")

        elif choice == "5":
            pid = _input("Policy ID: ")
            print("Statuses: active, expired, cancelled, suspended")
            status = _input("New status: ")
            pol_ops.update_policy(int(pid), status=status)
            print("✓ Policy updated.")

        elif choice == "6":
            pid = _input("Policy ID to delete: ")
            if _confirm():
                pol_ops.delete_policy(int(pid))
                print("✓ Policy deleted.")

        elif choice == "0":
            break


# ---------------------------------------------------------------------------
# Claims menu
# ---------------------------------------------------------------------------

def menu_claims():
    while True:
        print("\n=== Claims Management ===")
        print("  1. List all claims")
        print("  2. List claims for a policy")
        print("  3. File new claim")
        print("  4. View claim")
        print("  5. Update claim (approve / reject)")
        print("  6. Delete claim")
        print("  0. Back")
        choice = _input("Choice: ")

        if choice == "1":
            claims = clm_ops.list_claims()
            _print_table(claims, ["id", "claim_number", "policy_id",
                                  "claim_date", "amount_claimed",
                                  "amount_approved", "status"])

        elif choice == "2":
            pid = _input("Policy ID: ")
            claims = clm_ops.list_claims(policy_id=int(pid))
            _print_table(claims, ["id", "claim_number", "claim_date",
                                  "amount_claimed", "amount_approved", "status"])

        elif choice == "3":
            pid = _input("Policy ID: ")
            p = pol_ops.get_policy(int(pid))
            if not p:
                print("Policy not found.")
                continue
            claim_date = _input(f"Claim date [{_fmt_date()}]: ") or _fmt_date()
            description = _input("Description: ")
            amount = float(_input("Amount claimed: "))
            try:
                cid, cnum = clm_ops.create_claim(int(pid), claim_date, description, amount)
                print(f"✓ Claim filed: {cnum} (ID {cid})")
            except Exception as e:
                print(f"✗ Error: {e}")

        elif choice == "4":
            cid = _input("Claim ID: ")
            c = clm_ops.get_claim(int(cid))
            if c:
                for k, v in c.items():
                    print(f"  {k}: {v}")
            else:
                print("Claim not found.")

        elif choice == "5":
            cid = _input("Claim ID: ")
            c = clm_ops.get_claim(int(cid))
            if not c:
                print("Claim not found.")
                continue
            print(f"Current status: {c['status']}, Amount claimed: {c['amount_claimed']}")
            print("Statuses: approved, rejected, pending, under_review")
            status = _input("New status: ")
            approved = None
            if status == "approved":
                approved = float(_input(f"Amount approved [{c['amount_claimed']}]: ")
                                 or c["amount_claimed"])
            clm_ops.update_claim(int(cid), status=status, amount_approved=approved)
            print("✓ Claim updated.")

        elif choice == "6":
            cid = _input("Claim ID to delete: ")
            if _confirm():
                clm_ops.delete_claim(int(cid))
                print("✓ Claim deleted.")

        elif choice == "0":
            break


# ---------------------------------------------------------------------------
# Premium calculator
# ---------------------------------------------------------------------------

def menu_premium():
    print("\n=== Premium Calculator ===")
    print(f"Policy types: life, health, auto, home, travel")
    ptype = _input("Policy type: ").lower()
    coverage = float(_input("Coverage amount ($): "))
    dob = _input("Customer date of birth (YYYY-MM-DD, optional): ") or None
    months = int(_input("Policy duration in months [12]: ") or 12)
    try:
        result = prem_ops.calculate_premium(ptype, coverage, dob, months)
        print(f"\n  Estimated premium: ${result:.2f} for {months} months")
    except ValueError as e:
        print(f"✗ {e}")


# ---------------------------------------------------------------------------
# Reports menu
# ---------------------------------------------------------------------------

def menu_reports():
    while True:
        print("\n=== Reports ===")
        print("  1. Summary report")
        print("  2. Policies by type")
        print("  3. Top claims")
        print("  0. Back")
        choice = _input("Choice: ")

        if choice == "1":
            r = rep_ops.summary_report()
            print(f"\n  Customers          : {r['total_customers']}")
            print(f"  Total policies     : {r['total_policies']}")
            print(f"  Active policies    : {r['active_policies']}")
            print(f"  Total coverage     : ${r['total_coverage']:,.2f}")
            print(f"  Total premiums     : ${r['total_premiums']:,.2f}")
            print(f"  Total claims       : {r['total_claims']}")
            print("\n  Claims by status:")
            for row in r["claims_by_status"]:
                print(f"    {row['status']:<15}: {row['cnt']} claims  "
                      f"(${row['total']:,.2f} claimed)")

        elif choice == "2":
            rows = rep_ops.policies_by_type_report()
            _print_table(rows, ["policy_type", "count", "total_coverage", "total_premiums"])

        elif choice == "3":
            limit = int(_input("How many top claims to show [10]: ") or 10)
            rows = rep_ops.top_claims_report(limit)
            _print_table(rows, ["claim_number", "customer_name", "policy_type",
                                "amount_claimed", "amount_approved", "status"])

        elif choice == "0":
            break


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    init_db()
    print("\n╔══════════════════════════════════════╗")
    print("║   Insurance Management System v1.0   ║")
    print("╚══════════════════════════════════════╝")

    while True:
        print("\n=== Main Menu ===")
        print("  1. Customer Management")
        print("  2. Policy Management")
        print("  3. Claims Management")
        print("  4. Premium Calculator")
        print("  5. Reports")
        print("  0. Exit")
        choice = _input("Choice: ")

        if choice == "1":
            menu_customers()
        elif choice == "2":
            menu_policies()
        elif choice == "3":
            menu_claims()
        elif choice == "4":
            menu_premium()
        elif choice == "5":
            menu_reports()
        elif choice == "0":
            print("Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice, please try again.")


if __name__ == "__main__":
    main()
