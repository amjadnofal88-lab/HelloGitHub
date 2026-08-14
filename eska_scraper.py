#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""ESKA scraper with Playwright inspect/bootstrap mode and date-range export."""
import argparse
import os
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.eska_storage_state.json')


class Config:
    def __init__(self):
        load_dotenv()
        self.url = os.getenv('ESKA_URL', '').strip()
        self.transactions_url = os.getenv('ESKA_TRANSACTIONS_URL', '').strip()
        self.user = os.getenv('ESKA_USER', '').strip()
        self.password = os.getenv('ESKA_PASS', '')
        self.user_selector = os.getenv('ESKA_USER_SELECTOR', 'input[name="username"], input[type="email"], #username')
        self.pass_selector = os.getenv('ESKA_PASS_SELECTOR', 'input[name="password"], input[type="password"], #password')
        self.login_button_selector = os.getenv('ESKA_LOGIN_BUTTON_SELECTOR', 'button[type="submit"], button:has-text("Login"), button:has-text("Sign in")')
        self.from_selector = os.getenv('ESKA_FROM_SELECTOR', 'input[name="from"], input[name="date_from"], input[name="start_date"]')
        self.to_selector = os.getenv('ESKA_TO_SELECTOR', 'input[name="to"], input[name="date_to"], input[name="end_date"]')
        self.submit_selector = os.getenv('ESKA_SUBMIT_SELECTOR', 'button[type="submit"], button:has-text("Search"), button:has-text("Filter")')
        self.table_selector = os.getenv('ESKA_TABLE_SELECTOR', 'table')


def parse_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError('Invalid date "{}". Use YYYY-MM-DD.'.format(value)) from exc


def parse_args():
    parser = argparse.ArgumentParser(description='ESKA scraper using Playwright + pandas export.')
    parser.add_argument('--inspect', action='store_true', help='Open browser for first-time manual login and save storage state.')
    parser.add_argument('--from', dest='date_from', type=parse_date, help='Start date (YYYY-MM-DD).')
    parser.add_argument('--to', dest='date_to', type=parse_date, help='End date (YYYY-MM-DD).')
    parser.add_argument('--output', default='', help='Output Excel path (default: eska_YYYY-MM-DD_YYYY-MM-DD.xlsx).')
    args = parser.parse_args()
    if not args.inspect and (not args.date_from or not args.date_to):
        parser.error(
            'Both --from and --to are required for scraping. '
            'Run with --inspect first if you have not bootstrapped session state yet.'
        )
    return args


def require_url(url):
    if not url:
        raise ValueError('ESKA_URL is required. Export it or put it in .env.')


def save_manual_session(config):
    require_url(config.url)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, devtools=True)
        try:
            context = browser.new_context()
            page = context.new_page()
            page.goto(config.url, wait_until='domcontentloaded')
            print('Browser opened. Complete login manually, then press Enter here to save session...')
            input()
            context.storage_state(path=STATE_FILE)
            print('Saved storage state to {}'.format(STATE_FILE))
        finally:
            browser.close()


def first_visible(page, selector_group, timeout_ms=7000):
    selectors = [part.strip() for part in selector_group.split(',') if part.strip()]
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state='visible', timeout=timeout_ms)
            return locator
        except PlaywrightTimeoutError:
            continue
    raise RuntimeError('No visible selector matched: {}'.format(selector_group))


def attempt_login(page, config):
    if not (config.user and config.password):
        return False
    try:
        user_input = first_visible(page, config.user_selector)
        pass_input = first_visible(page, config.pass_selector)
        user_input.fill(config.user)
        pass_input.fill(config.password)
        login_btn = first_visible(page, config.login_button_selector)
        login_btn.click()
        page.wait_for_load_state('networkidle', timeout=15000)
        return True
    except Exception as exc:
        raise RuntimeError('Unable to complete login flow: {}'.format(exc)) from exc


def extract_table(page, table_selector):
    page.wait_for_selector(table_selector, timeout=15000)
    data = page.locator(table_selector).first.evaluate(
        """(table) => {
            const rows = Array.from(table.querySelectorAll('tr'));
            if (!rows.length) return [];
            const headerCells = Array.from(rows[0].querySelectorAll('th,td'));
            const headers = headerCells.map((h, i) => (h.innerText || '').trim() || `column_${i + 1}`);
            const out = [];
            for (const row of rows.slice(1)) {
                const cells = Array.from(row.querySelectorAll('td,th'));
                if (!cells.length) continue;
                const record = {};
                headers.forEach((name, idx) => {
                    record[name] = ((cells[idx] && cells[idx].innerText) || '').trim();
                });
                const nonEmpty = Object.values(record).some(v => v !== '');
                if (nonEmpty) out.push(record);
            }
            return out;
        }"""
    )
    return data


def run_date_range_scrape(config, date_from, date_to, output_path):
    require_url(config.url)
    if date_from > date_to:
        raise ValueError('--from must be less than or equal to --to.')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context_kwargs = {}
            state_exists = os.path.exists(STATE_FILE)
            if state_exists:
                context_kwargs['storage_state'] = STATE_FILE
            context = browser.new_context(**context_kwargs)
            page = context.new_page()

            page.goto(config.url, wait_until='domcontentloaded')

            if config.user and config.password:
                try:
                    attempt_login(page, config)
                finally:
                    config.password = ''

            if config.transactions_url:
                page.goto(config.transactions_url, wait_until='domcontentloaded')

            first_visible(page, config.from_selector).fill(date_from.strftime('%Y-%m-%d'))
            first_visible(page, config.to_selector).fill(date_to.strftime('%Y-%m-%d'))
            first_visible(page, config.submit_selector).click()
            page.wait_for_load_state('networkidle', timeout=20000)

            rows = extract_table(page, config.table_selector)
            if not rows:
                raise RuntimeError('No rows found for the selected range.')

            dataframe = pd.DataFrame(rows)
            dataframe.to_excel(output_path, index=False)
            print('Exported {} rows to {}'.format(len(dataframe.index), output_path))

            context.storage_state(path=STATE_FILE)
        finally:
            browser.close()


def main():
    args = parse_args()
    config = Config()

    if args.inspect:
        save_manual_session(config)
        return 0

    output_path = args.output or 'eska_{}_{}.xlsx'.format(
        args.date_from.strftime('%Y-%m-%d'), args.date_to.strftime('%Y-%m-%d')
    )

    run_date_range_scrape(config, args.date_from, args.date_to, output_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
