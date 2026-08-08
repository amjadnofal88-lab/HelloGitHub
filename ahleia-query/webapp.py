#!/usr/bin/env python3
"""
webapp.py — Local Flask RTL Arabic UI for insurance statement queries.

Usage:
    python webapp.py [--db statements.db] [--port 5000]

Routes:
    /               Home / summary page
    /search         Full-text search
    /range          Date-range filter
    /cheques        Cheque lookup
    /returned       Returned cheques
    /duplicates     Duplicate journal numbers
    /blank          Blank notes / cheque numbers
    /offsets        Net-zero debit/credit pairs
    /garage         Garage / workshop payments
    /reused         Reused cheque numbers
    /sql            Raw SELECT interface
    /export         Redirect to report.py export
"""

import argparse
import sqlite3
import subprocess
import sys
from pathlib import Path

try:
    from flask import Flask, g, render_template_string, request, redirect, url_for
except ImportError:
    print("Flask غير مثبّت. شغّل: pip install flask", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = Flask(__name__)
DB_PATH = "statements.db"

BASE_STYLE = """
<style>
  body { direction: rtl; font-family: 'Segoe UI', Arial, sans-serif;
         margin: 0; background: #f4f7fb; color: #1a1a2e; }
  nav { background: #1F497D; padding: 0.6rem 1.2rem; display:flex; flex-wrap:wrap; gap:0.5rem; }
  nav a { color:#fff; text-decoration:none; padding:0.3rem 0.7rem;
          border-radius:4px; font-size:0.9rem; }
  nav a:hover { background:#16335a; }
  main { max-width: 1200px; margin: 1.5rem auto; padding: 0 1rem; }
  h1 { color: #1F497D; font-size: 1.4rem; margin-bottom: 1rem; }
  form { background:#fff; padding:1rem; border-radius:6px;
         box-shadow:0 1px 4px rgba(0,0,0,.12); margin-bottom:1.2rem; }
  form label { display:block; margin:.4rem 0 .15rem; font-weight:600; font-size:.9rem; }
  form input, form select, form textarea {
    width:100%; padding:.4rem .6rem; border:1px solid #c8d4e3;
    border-radius:4px; box-sizing:border-box; font-size:.9rem; }
  form button { margin-top:.6rem; background:#1F497D; color:#fff;
                border:none; padding:.5rem 1.2rem; border-radius:4px;
                cursor:pointer; font-size:.95rem; }
  form button:hover { background:#16335a; }
  table { width:100%; border-collapse:collapse; background:#fff;
          border-radius:6px; overflow:hidden;
          box-shadow:0 1px 4px rgba(0,0,0,.12); font-size:.85rem; }
  th { background:#1F497D; color:#fff; padding:.5rem .6rem; text-align:right; }
  td { padding:.4rem .6rem; border-bottom:1px solid #e0e8f0; }
  tr:nth-child(even) td { background:#dce6f1; }
  .count { color:#555; font-size:.85rem; margin-top:.5rem; }
  .empty { color:#888; font-style:italic; margin:1rem 0; }
  .error { color:#c00; background:#fff0f0; padding:.6rem; border-radius:4px; }
</style>
"""

NAV = """
<nav>
  <a href="/">الرئيسية</a>
  <a href="/search">بحث</a>
  <a href="/range">نطاق تاريخ</a>
  <a href="/cheques">الشيكات</a>
  <a href="/returned">المرتجعات</a>
  <a href="/duplicates">التكرارات</a>
  <a href="/blank">بدون بيان</a>
  <a href="/offsets">مقاصة</a>
  <a href="/garage">الكراجات</a>
  <a href="/reused">شيكات مُعادة</a>
  <a href="/sql">SQL مباشر</a>
</nav>
"""

def page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><title>{title}</title>{BASE_STYLE}</head>
<body>{NAV}<main><h1>{title}</h1>{body}</main></body>
</html>"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc=None):
    db = g.pop("db", None)
    if db:
        db.close()


def rows_to_html(rows, empty="لا توجد نتائج.") -> str:
    if not rows:
        return f'<p class="empty">{empty}</p>'
    keys = rows[0].keys()
    head = "".join(f"<th>{k}</th>" for k in keys)
    body = ""
    for row in rows:
        cells = "".join(f"<td>{row[k] if row[k] is not None else ''}</td>" for k in keys)
        body += f"<tr>{cells}</tr>"
    count = f'<p class="count">{len(rows)} صف</p>'
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>{count}"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    db = get_db()
    rows = db.execute("""
        SELECT account, currency,
               COUNT(*) AS عدد_الصفوف,
               ROUND(SUM(COALESCE(debit,0)),2)  AS مجموع_المدين,
               ROUND(SUM(COALESCE(credit,0)),2) AS مجموع_الدائن,
               MIN(iso_date) AS من_تاريخ, MAX(iso_date) AS إلى_تاريخ
        FROM entries
        GROUP BY account, currency ORDER BY account, currency
    """).fetchall()
    return page("ملخص الحسابات", rows_to_html(rows, "لا توجد بيانات — أضف ملفات PDF أولاً."))


@app.route("/search", methods=["GET", "POST"])
def search():
    html = """<form method="post">
      <label>كلمة البحث</label>
      <input name="term" value="{term}" placeholder="مثال: ورشة">
      <button type="submit">بحث</button>
    </form>"""
    result = ""
    term = ""
    if request.method == "POST":
        term = request.form.get("term", "").strip()
        if term:
            like = f"%{term}%"
            rows = get_db().execute(
                "SELECT * FROM entries WHERE note LIKE ? OR kind LIKE ? OR journal_type LIKE ? ORDER BY iso_date",
                (like, like, like),
            ).fetchall()
            result = rows_to_html(rows)
    return page("بحث نصي", html.format(term=term) + result)


@app.route("/range", methods=["GET", "POST"])
def date_range():
    html = """<form method="post">
      <label>من تاريخ</label><input name="from_date" type="date" value="{fd}">
      <label>إلى تاريخ</label><input name="to_date"   type="date" value="{td}">
      <label>الحساب (اختياري)</label><input name="account" value="{acc}">
      <button type="submit">تصفية</button>
    </form>"""
    result = ""
    fd = td = acc = ""
    if request.method == "POST":
        fd  = request.form.get("from_date", "")
        td  = request.form.get("to_date",   "")
        acc = request.form.get("account",   "").strip()
        conds, params = ["1=1"], []
        if fd:  conds.append("iso_date >= ?"); params.append(fd)
        if td:  conds.append("iso_date <= ?"); params.append(td)
        if acc: conds.append("account = ?");   params.append(acc)
        rows = get_db().execute(
            f"SELECT * FROM entries WHERE {' AND '.join(conds)} ORDER BY iso_date",
            params,
        ).fetchall()
        result = rows_to_html(rows)
    return page("نطاق تاريخ", html.format(fd=fd, td=td, acc=acc) + result)


@app.route("/cheques", methods=["GET", "POST"])
def cheques():
    html = """<form method="post">
      <label>رقم الشيك</label>
      <input name="number" value="{num}" placeholder="مثال: 123456">
      <button type="submit">بحث</button>
    </form>"""
    result = ""
    num = ""
    if request.method == "POST":
        num = request.form.get("number", "").strip()
        if num:
            rows = get_db().execute(
                "SELECT * FROM entries WHERE cheque_no = ? ORDER BY iso_date",
                (num,),
            ).fetchall()
            result = rows_to_html(rows)
        else:
            rows = get_db().execute(
                "SELECT * FROM entries WHERE cheque_no IS NOT NULL AND TRIM(cheque_no)!='' ORDER BY iso_date"
            ).fetchall()
            result = rows_to_html(rows)
    return page("الشيكات", html.format(num=num) + result)


@app.route("/returned")
def returned():
    keywords = ["مرتجع", "راجع", "returned", "bounced", "dishonoured", "dishonored"]
    like_clauses = " OR ".join("LOWER(note) LIKE ?" for _ in keywords)
    params = [f"%{k}%" for k in keywords]
    rows = get_db().execute(
        f"SELECT * FROM entries WHERE ({like_clauses}) ORDER BY iso_date", params
    ).fetchall()
    return page("الشيكات المرتجعة", rows_to_html(rows))


@app.route("/duplicates")
def duplicates():
    rows = get_db().execute("""
        SELECT account, journal_no, COUNT(*) AS التكرار, GROUP_CONCAT(id) AS المعرفات
        FROM entries WHERE journal_no IS NOT NULL
        GROUP BY account, journal_no HAVING COUNT(*) > 1
        ORDER BY التكرار DESC
    """).fetchall()
    return page("القيود المكررة", rows_to_html(rows, "لا توجد تكرارات."))


@app.route("/blank")
def blank():
    rows = get_db().execute("""
        SELECT * FROM entries
        WHERE (note IS NULL OR TRIM(note)='')
          AND (cheque_no IS NULL OR TRIM(cheque_no)='')
        ORDER BY iso_date
    """).fetchall()
    return page("صفوف بدون بيان", rows_to_html(rows))


@app.route("/offsets")
def offsets():
    rows = get_db().execute("""
        SELECT account, journal_no,
               ROUND(SUM(COALESCE(debit,0)) - SUM(COALESCE(credit,0)),4) AS الصافي,
               COUNT(*) AS الصفوف
        FROM entries WHERE journal_no IS NOT NULL
        GROUP BY account, journal_no
        HAVING ABS(الصافي) < 0.01 AND الصفوف >= 2
        ORDER BY account, journal_no
    """).fetchall()
    return page("مقاصة المدين/الدائن", rows_to_html(rows, "لا توجد مقاصة."))


@app.route("/garage")
def garage():
    keywords = ["كراج", "ورشة", "garage", "workshop", "مركز صيانة", "بودي"]
    like_clauses = " OR ".join("LOWER(note) LIKE ?" for _ in keywords)
    params = [f"%{k}%" for k in keywords]
    rows = get_db().execute(
        f"SELECT * FROM entries WHERE ({like_clauses}) ORDER BY iso_date", params
    ).fetchall()
    return page("مدفوعات الكراجات والورش", rows_to_html(rows))


@app.route("/reused")
def reused():
    rows = get_db().execute("""
        SELECT account, cheque_no, COUNT(*) AS مرات_الاستخدام,
               MIN(iso_date) AS أول_استخدام, MAX(iso_date) AS آخر_استخدام
        FROM entries
        WHERE cheque_no IS NOT NULL AND TRIM(cheque_no) != ''
        GROUP BY account, cheque_no HAVING COUNT(*) > 1
        ORDER BY مرات_الاستخدام DESC
    """).fetchall()
    return page("شيكات مُعاد استخدامها", rows_to_html(rows, "لا توجد شيكات مُعادة."))


@app.route("/sql", methods=["GET", "POST"])
def raw_sql():
    html = """<form method="post">
      <label>جملة SELECT</label>
      <textarea name="stmt" rows="4" placeholder="SELECT * FROM entries LIMIT 20">{stmt}</textarea>
      <button type="submit">تنفيذ</button>
    </form>"""
    result = ""
    stmt = ""
    error = ""
    if request.method == "POST":
        stmt = request.form.get("stmt", "").strip()
        if not stmt.upper().startswith("SELECT"):
            error = '<p class="error">يُسمح فقط بجمل SELECT.</p>'
        else:
            try:
                rows = get_db().execute(stmt).fetchall()
                result = rows_to_html(rows)
            except sqlite3.Error as exc:
                error = f'<p class="error">خطأ: {exc}</p>'
    return page("SQL مباشر", html.format(stmt=stmt) + error + result)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    global DB_PATH

    parser = argparse.ArgumentParser(description="واجهة ويب لكشوف الحسابات التأمينية")
    parser.add_argument("--db",   default="statements.db", help="مسار قاعدة البيانات")
    parser.add_argument("--port", type=int, default=5000,  help="منفذ الخادم")
    parser.add_argument("--host", default="127.0.0.1",     help="عنوان الاستماع")
    args = parser.parse_args()

    DB_PATH = args.db
    print(f"[webapp] يعمل على http://{args.host}:{args.port}  (قاعدة البيانات: {args.db})")
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
