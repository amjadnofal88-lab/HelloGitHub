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


def production_report(customer_name=None):
    """Return policy production statistics, optionally filtered by customer name.

    When *customer_name* is provided the search is case-insensitive and
    matches any customer whose name contains the given string.
    """
    with get_connection() as conn:
        if customer_name:
            rows = conn.execute(
                """SELECT cu.name as customer_name,
                          p.policy_type,
                          p.policy_number,
                          p.coverage_amount,
                          p.premium_amount,
                          p.start_date,
                          p.end_date,
                          p.status
                   FROM policies p
                   JOIN customers cu ON p.customer_id = cu.id
                   WHERE LOWER(cu.name) LIKE LOWER(?)
                   ORDER BY cu.name, p.start_date DESC""",
                (f"%{customer_name}%",),
            ).fetchall()
            totals = conn.execute(
                """SELECT COUNT(*) as total_policies,
                          COALESCE(SUM(p.coverage_amount), 0) as total_coverage,
                          COALESCE(SUM(p.premium_amount), 0) as total_premiums,
                          COUNT(CASE WHEN p.status = 'active' THEN 1 END) as active_policies
                   FROM policies p
                   JOIN customers cu ON p.customer_id = cu.id
                   WHERE LOWER(cu.name) LIKE LOWER(?)""",
                (f"%{customer_name}%",),
            ).fetchone()
        else:
            rows = conn.execute(
                """SELECT cu.name as customer_name,
                          p.policy_type,
                          p.policy_number,
                          p.coverage_amount,
                          p.premium_amount,
                          p.start_date,
                          p.end_date,
                          p.status
                   FROM policies p
                   JOIN customers cu ON p.customer_id = cu.id
                   ORDER BY cu.name, p.start_date DESC"""
            ).fetchall()
            totals = conn.execute(
                """SELECT COUNT(*) as total_policies,
                          COALESCE(SUM(coverage_amount), 0) as total_coverage,
                          COALESCE(SUM(premium_amount), 0) as total_premiums,
                          COUNT(CASE WHEN status = 'active' THEN 1 END) as active_policies
                   FROM policies"""
            ).fetchone()

    return {
        "policies": [dict(r) for r in rows],
        "totals": dict(totals),
    }


def loss_ratio_report():
    """Return standard and alternative (real) loss ratios.

    Standard loss ratio  = total amount_claimed  / total premiums (active policies) * 100
    Alternative real loss ratio = total amount_approved / total premiums (active policies) * 100

    The *alternative real loss ratio* reflects only what was actually paid out,
    giving a more conservative view of incurred losses.
    """
    with get_connection() as conn:
        premiums = conn.execute(
            "SELECT COALESCE(SUM(premium_amount), 0) FROM policies WHERE status = 'active'"
        ).fetchone()[0]

        claimed = conn.execute(
            "SELECT COALESCE(SUM(amount_claimed), 0) FROM claims"
        ).fetchone()[0]

        approved = conn.execute(
            "SELECT COALESCE(SUM(amount_approved), 0) FROM claims WHERE status = 'approved'"
        ).fetchone()[0]

        by_type = conn.execute(
            """SELECT p.policy_type,
                      COALESCE(SUM(p.premium_amount), 0)   as total_premiums,
                      COALESCE(SUM(c.amount_claimed), 0)   as total_claimed,
                      COALESCE(SUM(CASE WHEN c.status = 'approved'
                                        THEN c.amount_approved ELSE 0 END), 0) as total_approved
               FROM policies p
               LEFT JOIN claims c ON c.policy_id = p.id
               WHERE p.status = 'active'
               GROUP BY p.policy_type
               ORDER BY p.policy_type"""
        ).fetchall()

    def _ratio(numerator, denominator):
        return round(numerator / denominator * 100, 2) if denominator else None

    type_rows = []
    for r in by_type:
        row = dict(r)
        row["loss_ratio"] = _ratio(row["total_claimed"], row["total_premiums"])
        row["alternative_real_loss_ratio"] = _ratio(row["total_approved"], row["total_premiums"])
        type_rows.append(row)

    return {
        "total_premiums": premiums,
        "total_claimed": claimed,
        "total_approved": approved,
        "loss_ratio": _ratio(claimed, premiums),
        "alternative_real_loss_ratio": _ratio(approved, premiums),
        "by_policy_type": type_rows,
    }
