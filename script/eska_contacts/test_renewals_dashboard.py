#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""Tests for renewals_dashboard.py."""

import unittest
from unittest.mock import patch

import pandas as pd

import renewals_dashboard as module


class TestPhoneAndMasking(unittest.TestCase):
    def test_normalize_phone_local_default_970(self):
        self.assertEqual(module.normalize_phone('0599123456', '970'), '+970599123456')

    def test_normalize_phone_keeps_international_972(self):
        self.assertEqual(module.normalize_phone('+972599123456', '970'), '+972599123456')

    def test_mask_phone(self):
        self.assertEqual(module.mask_phone('+970599123456'), '970*******56')

    def test_mask_email(self):
        self.assertEqual(module.mask_email('mohammad@example.com'), 'm******d@example.com')


class TestPriorityAndMessage(unittest.TestCase):
    def test_priority_buckets(self):
        self.assertEqual(module.classify_priority(5), 'عاجل')
        self.assertEqual(module.classify_priority(60), 'قريب')
        self.assertEqual(module.classify_priority(140), 'لاحق')

    def test_build_message_contains_key_fields(self):
        row = {
            'customer_name': 'أحمد',
            'policy_number': 'P-123',
            'company': 'شركة الاختبار',
            'expiry_date_str': '2026-10-10',
        }
        msg = module.build_message(row)
        self.assertIn('أحمد', msg)
        self.assertIn('P-123', msg)
        self.assertIn('2026-10-10', msg)


class TestBuildDataset(unittest.TestCase):
    def test_build_dataset_filters_and_enriches_contacts(self):
        today = module.date.today()
        within_window = (today + module.timedelta(days=10)).strftime('%d/%m/%Y')
        outside_window = (today + module.timedelta(days=500)).strftime('%d/%m/%Y')

        input_df = pd.DataFrame({
            'رقم الوثيقة': ['A1', 'A2'],
            'اسم العميل': ['عميل 1', 'عميل 2'],
            'شركة التأمين': ['شركة ألف', 'شركة باء'],
            'تاريخ الانتهاء': [within_window, outside_window],
        })
        contacts_df = pd.DataFrame({
            'رقم الوثيقة': ['A1'],
            'اسم العميل': ['عميل 1'],
            'رقم الجوال': ['0599123456'],
            'البريد الإلكتروني': ['user1@example.com'],
        })

        rows, summary = module.build_dataset(
            input_df=input_df,
            contacts_df=contacts_df,
            days=365,
            company_filter='',
            country_code='970',
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['policy_number'], 'A1')
        self.assertTrue(rows[0]['phone'].startswith('+970'))
        self.assertEqual(summary['total'], 1)
        self.assertEqual(summary['contact_ratio'], 100.0)


class TestParseArgs(unittest.TestCase):
    def test_days_must_be_positive(self):
        with self.assertRaises(SystemExit):
            with patch('sys.argv', ['renewals_dashboard.py', 'a.xls', '--days', '0']):
                module.parse_args()


if __name__ == '__main__':
    unittest.main()
