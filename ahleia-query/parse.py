#!/usr/bin/env python3
"""
parse.py — Parse insurance account-statement PDFs into SQLite.

Usage:
    python parse.py <pdf_file> [<pdf_file> ...] --db statements.db

Strategy:
    1. Try pdftotext (poppler-utils) for fast text extraction.
    2. Fall back to pdfplumber if pdftotext is unavailable or yields no text.
"""

import argparse
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Optional

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

# ---------------------------------------------------------------------------
# SQLite helpers
# ---------------------------------------------------------------------------

DDL = """
CREATE TABLE IF NOT EXISTS entries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source       TEXT    NOT NULL,
    account      TEXT,
    date         TEXT,
    iso_date     TEXT,
    journal_no   TEXT,
    journal_type TEXT,
    kind         TEXT,
    cheque_no    TEXT,
    note         TEXT,
    amount       REAL,
    currency     TEXT,
    debit        REAL,
    credit       REAL,
    balance      REAL
);
"""


def open_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(DDL)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_via_pdftotext(pdf_path: str) -> Optional[str]:
    """Use the system pdftotext binary (poppler-utils)."""
    if not shutil.which("pdftotext"):
        return None
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", pdf_path, "-"],
            capture_output=True, text=True, timeout=60
        )
        text = result.stdout.strip()
        return text if text else None
    except Exception:
        return None


def extract_via_pdfplumber(pdf_path: str) -> Optional[str]:
    """Use pdfplumber as fallback."""
    if not HAS_PDFPLUMBER:
        return None
    try:
        import pdfplumber as _pp
        pages = []
        with _pp.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    pages.append(t)
        return "\n".join(pages) if pages else None
    except Exception:
        return None


def extract_text(pdf_path: str) -> str:
    text = extract_via_pdftotext(pdf_path)
    if not text:
        text = extract_via_pdfplumber(pdf_path)
    if not text:
        raise RuntimeError(f"Could not extract text from '{pdf_path}'")
    return text


# ---------------------------------------------------------------------------
# Date normalisation
# ---------------------------------------------------------------------------

def to_iso_date(raw: str) -> Optional[str]:
    """Convert common Arabic/Gulf date formats to ISO-8601 (YYYY-MM-DD)."""
    raw = raw.strip()
    # DD/MM/YYYY or DD-MM-YYYY
    m = re.match(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$", raw)
    if m:
        d, mo, y = m.groups()
        return f"{y}-{mo.zfill(2)}-{d.zfill(2)}"
    # YYYY/MM/DD or YYYY-MM-DD
    m = re.match(r"^(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})$", raw)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{mo.zfill(2)}-{d.zfill(2)}"
    return None


# ---------------------------------------------------------------------------
# Amount parsing
# ---------------------------------------------------------------------------

def parse_amount(raw: str) -> Optional[float]:
    """Strip thousand separators and parse to float."""
    raw = raw.strip().replace(",", "").replace(" ", "")
    if not raw or raw == "-":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Row parsing
# ---------------------------------------------------------------------------

# A rough heuristic pattern for a statement line:
# date  journal_no  [journal_type]  [kind]  [cheque_no]  note  amount  currency
#   debit  credit  balance
# Real-world PDFs vary widely; this pattern handles common Gulf insurer formats.

_DATE_RE = re.compile(r"\d{1,2}[/\-]\d{1,2}[/\-]\d{4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2}")
_AMOUNT_RE = re.compile(r"[\d,]+(?:\.\d+)?")
_CURRENCY_RE = re.compile(r"\b(SAR|AED|KWD|BHD|QAR|OMR|USD|EUR|GBP)\b")


def _split_amounts(tokens: list[str]) -> list[float]:
    amounts = []
    for tok in tokens:
        v = parse_amount(tok)
        if v is not None:
            amounts.append(v)
    return amounts


def parse_line(line: str, account: str, source: str) -> Optional[dict]:
    """
    Attempt to parse one text line as a statement entry.
    Returns a dict ready for DB insertion, or None if the line is not a data row.
    """
    line = line.strip()
    if not line:
        return None

    # Must contain a date to be a data row
    date_match = _DATE_RE.search(line)
    if not date_match:
        return None

    raw_date = date_match.group()
    iso_date = to_iso_date(raw_date)

    # Detect currency
    curr_match = _CURRENCY_RE.search(line)
    currency = curr_match.group(1) if curr_match else None

    # Collect all numeric tokens (likely amounts)
    tokens = line.split()
    numeric_tokens = [t for t in tokens if _AMOUNT_RE.fullmatch(t.replace(",", ""))]
    amounts = _split_amounts(numeric_tokens)

    # Heuristic: last 3 numerics → debit, credit, balance; earlier ones → amount
    debit = credit = balance = amount = None
    if len(amounts) >= 3:
        balance = amounts[-1]
        credit  = amounts[-2]
        debit   = amounts[-3]
        amount  = amounts[-4] if len(amounts) >= 4 else None
    elif len(amounts) == 2:
        credit, balance = amounts
    elif len(amounts) == 1:
        amount = amounts[0]

    # Journal number: first token that looks like a numeric ID after the date
    post_date = line[date_match.end():].strip()
    tokens_after = post_date.split()
    journal_no = None
    journal_type = None
    kind = None
    cheque_no = None

    for i, tok in enumerate(tokens_after):
        if re.fullmatch(r"\d{4,}", tok):
            if journal_no is None:
                journal_no = tok
            elif cheque_no is None:
                cheque_no = tok
            continue
        if re.fullmatch(r"[A-Za-z\u0600-\u06FF]{2,}", tok):
            if journal_type is None:
                journal_type = tok
            elif kind is None:
                kind = tok

    # Note: everything that is not date/amounts/journal tokens
    note_parts = []
    for tok in tokens_after:
        if tok in (journal_no or "", cheque_no or "", journal_type or "", kind or ""):
            continue
        if _AMOUNT_RE.fullmatch(tok.replace(",", "")):
            continue
        if currency and tok == currency:
            continue
        note_parts.append(tok)
    note = " ".join(note_parts).strip() or None

    return {
        "source":       source,
        "account":      account,
        "date":         raw_date,
        "iso_date":     iso_date,
        "journal_no":   journal_no,
        "journal_type": journal_type,
        "kind":         kind,
        "cheque_no":    cheque_no,
        "note":         note,
        "amount":       amount,
        "currency":     currency,
        "debit":        debit,
        "credit":       credit,
        "balance":      balance,
    }


# ---------------------------------------------------------------------------
# Account detection
# ---------------------------------------------------------------------------

_ACCOUNT_RE = re.compile(
    r"(?:account|حساب|رقم الحساب)[^\d]*(\d[\d\-]+)",
    re.IGNORECASE
)


def detect_account(text: str) -> str:
    m = _ACCOUNT_RE.search(text)
    return m.group(1) if m else "UNKNOWN"


# ---------------------------------------------------------------------------
# PDF ingestion
# ---------------------------------------------------------------------------

def ingest_pdf(pdf_path: str, conn: sqlite3.Connection) -> int:
    source = Path(pdf_path).name
    print(f"[parse] Processing: {source}")

    text = extract_text(pdf_path)
    account = detect_account(text)

    rows = []
    for line in text.splitlines():
        entry = parse_line(line, account, source)
        if entry:
            rows.append(entry)

    if not rows:
        print(f"[parse] WARNING: No entries found in {source}")
        return 0

    conn.executemany(
        """
        INSERT INTO entries
            (source, account, date, iso_date, journal_no, journal_type,
             kind, cheque_no, note, amount, currency, debit, credit, balance)
        VALUES
            (:source, :account, :date, :iso_date, :journal_no, :journal_type,
             :kind, :cheque_no, :note, :amount, :currency, :debit, :credit, :balance)
        """,
        rows,
    )
    conn.commit()
    print(f"[parse] Inserted {len(rows)} entries from {source}")
    return len(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Parse insurance account-statement PDFs into SQLite."
    )
    parser.add_argument("pdfs", nargs="+", help="PDF files to parse")
    parser.add_argument(
        "--db", default="statements.db",
        help="SQLite database path (default: statements.db)"
    )
    args = parser.parse_args()

    conn = open_db(args.db)
    total = 0
    errors = []
    for pdf in args.pdfs:
        try:
            total += ingest_pdf(pdf, conn)
        except Exception as exc:
            print(f"[parse] ERROR processing {pdf}: {exc}", file=sys.stderr)
            errors.append(pdf)
    conn.close()

    print(f"\n[parse] Done — {total} total entries inserted, {len(errors)} file(s) failed.")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
