"""Basic reporting on policies and claims."""

from database import get_connection


def summary_report():
    with get_connection() as conn:
        total_customers = conn.execute(
            "SELECT COUNT(*) FROM customers"
        ).fetchone()[0]

        total_policies = conn.execute(
            "SELECT COUNT(*) FROM policies"
        ).fetchone()[0]

        active_policies = conn.execute(
            "SELECT COUNT(*) FROM policies WHERE status = 'active'"
        ).fetchone()[0]

        total_coverage = conn.execute(
            "SELECT COALESCE(SUM(coverage_amount), 0) FROM policies WHERE status = 'active'"
        ).fetchone()[0]

        total_premiums = conn.execute(
            "SELECT COALESCE(SUM(premium_amount), 0) FROM policies WHERE status = 'active'"
        ).fetchone()[0]

        total_claims = conn.execute(
            "SELECT COUNT(*) FROM claims"
        ).fetchone()[0]

        claims_by_status = conn.execute(
            "SELECT status, COUNT(*) as cnt, COALESCE(SUM(amount_claimed), 0) as total "
            "FROM claims GROUP BY status"
        ).fetchall()

    return {
        "total_customers": total_customers,
        "total_policies": total_policies,
        "active_policies": active_policies,
        "total_coverage": total_coverage,
        "total_premiums": total_premiums,
        "total_claims": total_claims,
        "claims_by_status": [dict(r) for r in claims_by_status],
    }


def policies_by_type_report():
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT policy_type,
                      COUNT(*) as count,
                      COALESCE(SUM(coverage_amount), 0) as total_coverage,
                      COALESCE(SUM(premium_amount), 0) as total_premiums
               FROM policies
               GROUP BY policy_type
               ORDER BY count DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


def top_claims_report(limit=10):
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT c.claim_number, c.claim_date, c.amount_claimed,
                      c.amount_approved, c.status,
                      p.policy_number, p.policy_type,
                      cu.name as customer_name
               FROM claims c
               JOIN policies p ON c.policy_id = p.id
               JOIN customers cu ON p.customer_id = cu.id
               ORDER BY c.amount_claimed DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
