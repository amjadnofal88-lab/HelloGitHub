#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_policy_transfers.py — unit tests for policy_transfers.py

Mocks `ahleia_statement` so no real PDF or external module is needed.
Run with:  python -m pytest script/test_policy_transfers.py -v
"""
import os
import sys
import csv
import tempfile
import datetime
import unittest
from decimal import Decimal
from unittest.mock import patch, MagicMock

# ── stub out the external dependency before importing the module ──────────
ahleia_stub = MagicMock()
ahleia_stub.parse_statement = MagicMock()
ahleia_stub.enrich = lambda rows: rows
sys.modules['ahleia_statement'] = ahleia_stub

# now we can safely import
sys.path.insert(0, os.path.dirname(__file__))
import policy_transfers as pt


# ── helpers ───────────────────────────────────────────────────────────────
TODAY = datetime.date.today().strftime('%Y%m%d')

SAMPLE_ROWS = [
    {'policy_no': 'POL-001', 'type': 'DebitNote',  'debit': '1000.00', 'credit': '0',    'date': '2026-01-01'},
    {'policy_no': 'POL-001', 'type': 'CreditNote', 'debit': '0',       'credit': '200.00','date': '2026-01-05'},
    {'policy_no': 'POL-002', 'type': 'DebitNote',  'debit': '500.00',  'credit': '0',    'date': '2026-01-02'},
    {'policy_no': 'POL-003', 'type': 'DebitNote',  'debit': '100.00',  'credit': '0',    'date': '2026-01-03'},
    {'policy_no': 'POL-003', 'type': 'CreditNote', 'debit': '0',       'credit': '100.00','date': '2026-01-06'},  # net = 0 → excluded
    {'policy_no': '',        'type': 'DebitNote',  'debit': '999.00',  'credit': '0',    'date': '2026-01-07'},   # no policy_no → ignored
]

SAMPLE_INFO = {'account': '506322', 'from': '2026-01-01', 'to': '2026-01-31'}


class TestMoneyRounding(unittest.TestCase):
    def test_round_half_up(self):
        self.assertEqual(pt.money('0.005'), Decimal('0.01'))
        self.assertEqual(pt.money('0.004'), Decimal('0.00'))
        self.assertEqual(pt.money('1234.5678'), Decimal('1234.57'))


class TestPerPolicy(unittest.TestCase):
    def test_aggregation(self):
        pol = pt.per_policy(SAMPLE_ROWS)
        self.assertEqual(pol['POL-001']['dn'], Decimal('1000.00'))
        self.assertEqual(pol['POL-001']['cn'], Decimal('200.00'))
        self.assertEqual(pol['POL-002']['dn'], Decimal('500.00'))
        self.assertEqual(pol['POL-002']['cn'], Decimal('0'))

    def test_skips_empty_policy_no(self):
        pol = pt.per_policy(SAMPLE_ROWS)
        self.assertNotIn('', pol)

    def test_first_date_debit_only(self):
        pol = pt.per_policy(SAMPLE_ROWS)
        self.assertEqual(pol['POL-001']['first'], '2026-01-01')

    def test_net_zero_policy_present(self):
        pol = pt.per_policy(SAMPLE_ROWS)
        net = pol['POL-003']['dn'] - pol['POL-003']['cn']
        self.assertEqual(net, Decimal('0'))


class TestBuildOrders(unittest.TestCase):
    def _mock_parse(self, pdf_path):
        return SAMPLE_INFO, SAMPLE_ROWS

    def test_order_count_and_exclusions(self):
        ahleia_stub.parse_statement.side_effect = self._mock_parse
        info, rate, orders, excluded = pt.build_orders('dummy.pdf')
        # POL-001 net=800, POL-002 net=500 → 2 orders
        # POL-003 net=0 → excluded
        self.assertEqual(len(orders), 2)
        self.assertEqual(len(excluded), 1)

    def test_commission_rate_from_account(self):
        ahleia_stub.parse_statement.side_effect = self._mock_parse
        _, rate, orders, _ = pt.build_orders('dummy.pdf')
        self.assertEqual(rate, Decimal('0.25'))   # account 506322 → 25%

    def test_commission_amounts(self):
        ahleia_stub.parse_statement.side_effect = self._mock_parse
        _, _, orders, _ = pt.build_orders('dummy.pdf')
        amounts = {o['policy']: o['amount'] for o in orders}
        self.assertEqual(amounts['POL-001'], pt.money(Decimal('800') * Decimal('0.25')))
        self.assertEqual(amounts['POL-002'], pt.money(Decimal('500') * Decimal('0.25')))

    def test_reference_format(self):
        ahleia_stub.parse_statement.side_effect = self._mock_parse
        _, _, orders, _ = pt.build_orders('dummy.pdf')
        for o in orders:
            self.assertRegex(o['ref'], rf'^COMM-506322-{TODAY}-\d{{4}}$')

    def test_min_amount_aggregates_small_orders(self):
        ahleia_stub.parse_statement.side_effect = self._mock_parse
        # POL-002 commission = 125 < 200 → should be bundled
        _, _, orders, excluded = pt.build_orders('dummy.pdf', min_amount=Decimal('150'))
        policies = [o['policy'] for o in orders]
        self.assertNotIn('POL-002', policies)
        # a misc bundle order should appear
        self.assertTrue(any('مجمّعة' in str(o['policy']) for o in orders))

    def test_override_rate(self):
        ahleia_stub.parse_statement.side_effect = self._mock_parse
        _, rate, orders, _ = pt.build_orders('dummy.pdf', rate=Decimal('0.27'))
        self.assertEqual(rate, Decimal('0.27'))
        for o in orders:
            self.assertEqual(o['rate'], Decimal('0.27'))


class TestExport(unittest.TestCase):
    def _run_export(self):
        ahleia_stub.parse_statement.side_effect = lambda p: (SAMPLE_INFO, SAMPLE_ROWS)
        info, rate, orders, excluded = pt.build_orders('dummy.pdf')
        with tempfile.TemporaryDirectory() as td:
            xlsx = os.path.join(td, 'out.xlsx')
            csv_path = os.path.join(td, 'out.csv')
            total = pt.export(info, rate, orders, excluded, xlsx, csv_path)
            return total, xlsx, csv_path, orders

    def test_total_matches_sum_of_orders(self):
        ahleia_stub.parse_statement.side_effect = lambda p: (SAMPLE_INFO, SAMPLE_ROWS)
        info, rate, orders, excluded = pt.build_orders('dummy.pdf')
        with tempfile.TemporaryDirectory() as td:
            xlsx = os.path.join(td, 'out.xlsx')
            csv_path = os.path.join(td, 'out.csv')
            total = pt.export(info, rate, orders, excluded, xlsx, csv_path)
        expected = sum(o['amount'] for o in orders)
        self.assertEqual(total, expected)

    def test_csv_row_count(self):
        ahleia_stub.parse_statement.side_effect = lambda p: (SAMPLE_INFO, SAMPLE_ROWS)
        info, rate, orders, excluded = pt.build_orders('dummy.pdf')
        with tempfile.TemporaryDirectory() as td:
            xlsx = os.path.join(td, 'out.xlsx')
            csv_path = os.path.join(td, 'out.csv')
            pt.export(info, rate, orders, excluded, xlsx, csv_path)
            with open(csv_path, encoding='utf-8-sig') as fh:
                rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), len(orders))

    def test_csv_columns(self):
        ahleia_stub.parse_statement.side_effect = lambda p: (SAMPLE_INFO, SAMPLE_ROWS)
        info, rate, orders, excluded = pt.build_orders('dummy.pdf')
        with tempfile.TemporaryDirectory() as td:
            xlsx = os.path.join(td, 'out.xlsx')
            csv_path = os.path.join(td, 'out.csv')
            pt.export(info, rate, orders, excluded, xlsx, csv_path)
            with open(csv_path, encoding='utf-8-sig') as fh:
                reader = csv.DictReader(fh)
                cols = reader.fieldnames
        self.assertEqual(cols, ['REFERENCE', 'BENEFICIARY_NAME',
                                 'BENEFICIARY_IBAN', 'AMOUNT', 'CURRENCY', 'DETAILS'])

    def test_csv_iban_and_beneficiary(self):
        ahleia_stub.parse_statement.side_effect = lambda p: (SAMPLE_INFO, SAMPLE_ROWS)
        info, rate, orders, excluded = pt.build_orders('dummy.pdf')
        with tempfile.TemporaryDirectory() as td:
            xlsx = os.path.join(td, 'out.xlsx')
            csv_path = os.path.join(td, 'out.csv')
            pt.export(info, rate, orders, excluded, xlsx, csv_path)
            with open(csv_path, encoding='utf-8-sig') as fh:
                rows = list(csv.DictReader(fh))
        for row in rows:
            self.assertEqual(row['BENEFICIARY_IBAN'], pt.IBAN)
            self.assertEqual(row['BENEFICIARY_NAME'], pt.BENEFICIARY)
            self.assertEqual(row['CURRENCY'], 'ILS')

    def test_xlsx_created(self):
        ahleia_stub.parse_statement.side_effect = lambda p: (SAMPLE_INFO, SAMPLE_ROWS)
        info, rate, orders, excluded = pt.build_orders('dummy.pdf')
        with tempfile.TemporaryDirectory() as td:
            xlsx = os.path.join(td, 'out.xlsx')
            csv_path = os.path.join(td, 'out.csv')
            pt.export(info, rate, orders, excluded, xlsx, csv_path)
            self.assertTrue(os.path.exists(xlsx))


if __name__ == '__main__':
    unittest.main()
