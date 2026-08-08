#!/usr/bin/env python3
"""
query.py — Query insurance statement entries stored in SQLite.

Subcommands:
    summary      Totals and row count per account / period
    cheque       Lookup entries by cheque number
    returned     Show returned / bounced cheques
    duplicates   Find duplicate journal entries
    blank        Entries with blank note or cheque_no
    offsets      Debit/credit pairs that net to zero
    garage       Entries whose note contains garage-related keywords
    reused       Cheque numbers used more than once
    search       Full-text search across note / kind / journal_type
    range        Date-range filter
    sql          Run an arbitrary SELECT statement
"""

import argparse
import sqlite3
import sys
from typing import Any

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def open_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def print_rows(rows: list[sqlite3.Row], empty_msg: str = "لا توجد نتائج.") -> None:
    if not rows:
        print(empty_msg)
        return
    # Print header
    keys = rows[0].keys()
    widths = {k: max(len(k), max((len(str(r[k] or "")) for r in rows), default=0)) for k in keys}
    header = "  ".join(k.ljust(widths[k]) for k in keys)
    print(header)
    print("-" * len(header))
    for row in rows:
        print("  ".join(str(row[k] or "").ljust(widths[k]) for k in keys))
    print(f"\n({len(rows)} صف)")


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------

def cmd_summary(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    """Totals per account (optionally filtered by date range)."""
    where = "WHERE 1=1"
    params: list[Any] = []
    if args.account:
        where += " AND account = ?"
        params.append(args.account)
    if args.from_date:
        where += " AND iso_date >= ?"
        params.append(args.from_date)
    if args.to_date:
        where += " AND iso_date <= ?"
        params.append(args.to_date)

    rows = conn.execute(
        f"""
        SELECT account,
               currency,
               COUNT(*)          AS عدد_الصفوف,
               ROUND(SUM(COALESCE(debit,  0)), 2) AS مجموع_المدين,
               ROUND(SUM(COALESCE(credit, 0)), 2) AS مجموع_الدائن,
               MIN(iso_date)     AS من_تاريخ,
               MAX(iso_date)     AS إلى_تاريخ
        FROM entries
        {where}
        GROUP BY account, currency
        ORDER BY account, currency
        """,
        params,
    ).fetchall()
    print_rows(rows)


def cmd_cheque(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    """Look up entries by cheque number."""
    rows = conn.execute(
        "SELECT * FROM entries WHERE cheque_no = ? ORDER BY iso_date",
        (args.number,),
    ).fetchall()
    print_rows(rows)


def cmd_returned(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    """Show returned / bounced cheque entries."""
    keywords = ["مرتجع", "راجع", "returned", "bounced", "dishonoured", "dishonored"]
    like_clauses = " OR ".join("LOWER(note) LIKE ?" for _ in keywords)
    params = [f"%{k}%" for k in keywords]
    rows = conn.execute(
        f"SELECT * FROM entries WHERE ({like_clauses}) ORDER BY iso_date",
        params,
    ).fetchall()
    print_rows(rows)


def cmd_duplicates(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    """Find entries sharing the same journal_no within the same account."""
    rows = conn.execute(
        """
        SELECT account, journal_no, COUNT(*) AS التكرار,
               GROUP_CONCAT(id) AS المعرفات
        FROM entries
        WHERE journal_no IS NOT NULL
        GROUP BY account, journal_no
        HAVING COUNT(*) > 1
        ORDER BY التكرار DESC
        """,
    ).fetchall()
    print_rows(rows, "لا توجد تكرارات.")


def cmd_blank(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    """Entries with blank note AND blank cheque_no."""
    rows = conn.execute(
        """
        SELECT * FROM entries
        WHERE (note IS NULL OR TRIM(note) = '')
          AND (cheque_no IS NULL OR TRIM(cheque_no) = '')
        ORDER BY iso_date
        """,
    ).fetchall()
    print_rows(rows)


def cmd_offsets(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    """Debit/credit pairs on the same journal_no that net to zero."""
    rows = conn.execute(
        """
        SELECT account, journal_no,
               ROUND(SUM(COALESCE(debit,0)) - SUM(COALESCE(credit,0)), 4) AS الصافي,
               COUNT(*) AS الصفوف
        FROM entries
        WHERE journal_no IS NOT NULL
        GROUP BY account, journal_no
        HAVING ABS(ROUND(SUM(COALESCE(debit,0)) - SUM(COALESCE(credit,0)), 4)) < 0.01
           AND COUNT(*) >= 2
        ORDER BY account, journal_no
        """,
    ).fetchall()
    print_rows(rows, "لا توجد مقاصة.")


def cmd_garage(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    """Entries whose note contains garage/workshop keywords."""
    keywords = ["كراج", "ورشة", "garage", "workshop", "مركز صيانة", "بودي"]
    like_clauses = " OR ".join("LOWER(note) LIKE ?" for _ in keywords)
    params = [f"%{k}%" for k in keywords]
    rows = conn.execute(
        f"SELECT * FROM entries WHERE ({like_clauses}) ORDER BY iso_date",
        params,
    ).fetchall()
    print_rows(rows)


def cmd_reused(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    """Cheque numbers that appear more than once (possibly reused)."""
    rows = conn.execute(
        """
        SELECT account, cheque_no, COUNT(*) AS مرات_الاستخدام,
               MIN(iso_date) AS أول_استخدام, MAX(iso_date) AS آخر_استخدام
        FROM entries
        WHERE cheque_no IS NOT NULL AND TRIM(cheque_no) != ''
        GROUP BY account, cheque_no
        HAVING COUNT(*) > 1
        ORDER BY مرات_الاستخدام DESC
        """,
    ).fetchall()
    print_rows(rows, "لا توجد شيكات مُعاد استخدامها.")


def cmd_search(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    """Full-text search across note, kind, journal_type."""
    term = f"%{args.term}%"
    rows = conn.execute(
        """
        SELECT * FROM entries
        WHERE note         LIKE ?
           OR kind         LIKE ?
           OR journal_type LIKE ?
        ORDER BY iso_date
        """,
        (term, term, term),
    ).fetchall()
    print_rows(rows)


def cmd_range(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    """Filter entries by ISO date range."""
    params: list[Any] = []
    where = "WHERE 1=1"
    if args.from_date:
        where += " AND iso_date >= ?"
        params.append(args.from_date)
    if args.to_date:
        where += " AND iso_date <= ?"
        params.append(args.to_date)
    if args.account:
        where += " AND account = ?"
        params.append(args.account)
    rows = conn.execute(
        f"SELECT * FROM entries {where} ORDER BY iso_date",
        params,
    ).fetchall()
    print_rows(rows)


def cmd_sql(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    """Run an arbitrary SELECT statement against the database."""
    sql = args.statement.strip()
    if not sql.upper().startswith("SELECT"):
        print("خطأ: يُسمح فقط بجمل SELECT.", file=sys.stderr)
        sys.exit(1)
    rows = conn.execute(sql).fetchall()
    print_rows(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="استعلام قاعدة بيانات كشوف الحسابات التأمينية"
    )
    parser.add_argument(
        "--db", default="statements.db",
        help="مسار قاعدة البيانات SQLite (الافتراضي: statements.db)"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # summary
    p = sub.add_parser("summary", help="ملخص المجاميع لكل حساب")
    p.add_argument("--account")
    p.add_argument("--from-date", dest="from_date")
    p.add_argument("--to-date",   dest="to_date")

    # cheque
    p = sub.add_parser("cheque", help="بحث برقم الشيك")
    p.add_argument("number", help="رقم الشيك")

    # returned
    sub.add_parser("returned", help="الشيكات المرتجعة")

    # duplicates
    sub.add_parser("duplicates", help="قيود مكررة")

    # blank
    sub.add_parser("blank", help="صفوف بدون بيان أو رقم شيك")

    # offsets
    sub.add_parser("offsets", help="مقاصة مدين/دائن على نفس القيد")

    # garage
    sub.add_parser("garage", help="مدفوعات الكراجات والورش")

    # reused
    sub.add_parser("reused", help="شيكات مُعاد استخدامها")

    # search
    p = sub.add_parser("search", help="بحث نصي في البيانات")
    p.add_argument("term", help="النص المراد البحث عنه")

    # range
    p = sub.add_parser("range", help="تصفية بنطاق تاريخ")
    p.add_argument("--from-date", dest="from_date")
    p.add_argument("--to-date",   dest="to_date")
    p.add_argument("--account")

    # sql
    p = sub.add_parser("sql", help="تشغيل جملة SELECT مباشرة")
    p.add_argument("statement", help="جملة SELECT")

    return parser


HANDLERS = {
    "summary":    cmd_summary,
    "cheque":     cmd_cheque,
    "returned":   cmd_returned,
    "duplicates": cmd_duplicates,
    "blank":      cmd_blank,
    "offsets":    cmd_offsets,
    "garage":     cmd_garage,
    "reused":     cmd_reused,
    "search":     cmd_search,
    "range":      cmd_range,
    "sql":        cmd_sql,
}


def main():
    parser = build_parser()
    args = parser.parse_args()
    conn = open_db(args.db)
    try:
        HANDLERS[args.command](conn, args)
    except sqlite3.OperationalError as exc:
        print(f"خطأ في قاعدة البيانات: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
