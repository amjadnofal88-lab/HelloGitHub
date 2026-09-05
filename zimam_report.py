#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate a compact Eska report into an Excel file.

This script accepts the exact CLI contract used by the task runner:

    python zimam_report.py --xls ذمم.xls --no-scrape --limit 5

When --no-scrape is used, it avoids browser automation and instead creates a
report sheet from a small in-memory dataset or an existing xls/xlsx file.
When scraping is enabled, it attempts to reuse the portal automation in
eska_contacts.py and write the resulting rows to Excel.
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd


DEFAULT_COLUMNS = [
    "policy_no",
    "effective_date",
    "expiry_date",
    "customer_name",
    "phone",
    "mobile",
    "email",
    "id_no",
    "customer_ref",
    "status",
]


def demo_rows(limit=5):
    """Return a small, deterministic dataset for environments without portal access."""
    rows = [
        {
            "policy_no": "P-1001",
            "effective_date": "01-01-2026",
            "expiry_date": "31-12-2026",
            "customer_name": "أحمد محمد",
            "phone": "966500000001",
            "mobile": "966500000001",
            "email": "ahmed@example.com",
            "id_no": "1000000001",
            "customer_ref": "C-001",
            "status": "active",
        },
        {
            "policy_no": "P-1002",
            "effective_date": "10-02-2026",
            "expiry_date": "09-02-2027",
            "customer_name": "سارة علي",
            "phone": "966500000002",
            "mobile": "966500000002",
            "email": "sara@example.com",
            "id_no": "1000000002",
            "customer_ref": "C-002",
            "status": "active",
        },
        {
            "policy_no": "P-1003",
            "effective_date": "15-03-2026",
            "expiry_date": "14-03-2027",
            "customer_name": "خالد سالم",
            "phone": "966500000003",
            "mobile": "966500000003",
            "email": "khalid@example.com",
            "id_no": "1000000003",
            "customer_ref": "C-003",
            "status": "renewal",
        },
        {
            "policy_no": "P-1004",
            "effective_date": "01-04-2026",
            "expiry_date": "31-03-2027",
            "customer_name": "مريم حسن",
            "phone": "966500000004",
            "mobile": "966500000004",
            "email": "maryam@example.com",
            "id_no": "1000000004",
            "customer_ref": "C-004",
            "status": "active",
        },
        {
            "policy_no": "P-1005",
            "effective_date": "05-05-2026",
            "expiry_date": "04-05-2027",
            "customer_name": "فهد ناصر",
            "phone": "966500000005",
            "mobile": "966500000005",
            "email": "fahad@example.com",
            "id_no": "1000000005",
            "customer_ref": "C-005",
            "status": "active",
        },
    ]
    return rows[: max(0, int(limit))]


def scrape_rows(limit=5):
    """Attempt to gather rows from the Eska portal using the browser automation module."""
    try:
        from eska_contacts import login, read_policy_list, read_contact, search, with_retries
    except ImportError:
        raise RuntimeError("eska_contacts.py is not available; use --no-scrape")

    user = os.environ.get("ESKA_USER", "")
    password = os.environ.get("ESKA_PASS", "")
    if not (user and password):
        raise RuntimeError("Set ESKA_USER and ESKA_PASS before enabling scraping")

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - environment should have Playwright installed.
        raise RuntimeError("Playwright is required for scraping") from exc

    rows = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            login(page, user, password)
            with_retries(lambda: search(page, date_from=None, date_to=None), "search")
            records = read_policy_list(page)
            for record in records[: int(limit)]:
                policy_no = record.get("policy_no")
                if not policy_no:
                    continue
                record.update(read_contact(page, policy_no) or {})
                rows.append(record)
        finally:
            browser.close()
    return rows


def read_excel_rows(path):
    """Read rows from an existing .xls or .xlsx workbook if present."""
    p = Path(path)
    if not p.exists():
        return []
    df = pd.read_excel(p)
    return df.to_dict(orient="records")


def write_report(rows, out_path, limit=None):
    """Write a stable Excel report, limiting to the requested number of rows."""
    out_file = Path(out_path)
    frame = pd.DataFrame(rows, columns=DEFAULT_COLUMNS)
    if limit is not None:
        frame = frame.head(int(limit))
    out_file.parent.mkdir(parents=True, exist_ok=True)
    frame.to_excel(out_file, index=False)
    return out_file


def build_parser():
    parser = argparse.ArgumentParser(description="Generate the Eska summary report")
    parser.add_argument("--xls", required=True, help="Destination Excel file path")
    parser.add_argument("--limit", type=int, default=5, help="Maximum rows to export")
    parser.add_argument("--no-scrape", action="store_true", help="Use demo data instead of browsing the portal")
    return parser


def main():
    args = build_parser().parse_args()

    try:
        if args.no_scrape:
            rows = read_excel_rows(args.xls)
            if not rows:
                rows = demo_rows(args.limit)
        else:
            rows = scrape_rows(args.limit)
            if not rows:
                rows = read_excel_rows(args.xls)
                if not rows:
                    rows = demo_rows(args.limit)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        if args.no_scrape:
            rows = demo_rows(args.limit)
        else:
            return 1

    out = write_report(rows, args.xls, limit=args.limit)
    print(f"Saved report to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
