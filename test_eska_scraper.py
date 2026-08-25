#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""Tests for eska_scraper.py."""
import unittest
from unittest.mock import patch

import eska_scraper as module


class TestParseDate(unittest.TestCase):
    def test_valid_date(self):
        value = module.parse_date('2026-01-01')
        self.assertEqual(str(value), '2026-01-01')

    def test_invalid_date_raises(self):
        with self.assertRaises(SystemExit):
            with patch('sys.argv', ['eska_scraper.py', '--from', '2026-13-99', '--to', '2026-01-01']):
                module.parse_args()


class TestRequireUrl(unittest.TestCase):
    def test_empty_url_raises(self):
        with self.assertRaises(ValueError):
            module.require_url('')


class TestParseArgs(unittest.TestCase):
    def test_inspect_only_is_allowed(self):
        with patch('sys.argv', ['eska_scraper.py', '--inspect']):
            args = module.parse_args()
        self.assertTrue(args.inspect)

    def test_missing_dates_without_inspect_errors(self):
        with self.assertRaises(SystemExit):
            with patch('sys.argv', ['eska_scraper.py']):
                module.parse_args()


if __name__ == '__main__':
    unittest.main()
