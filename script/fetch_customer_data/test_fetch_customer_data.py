#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Tests for fetch_customer_data.py
"""
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from openpyxl import load_workbook

sys.path.insert(0, os.path.dirname(__file__))

import fetch_customer_data as module


class TestBuildHeaders(unittest.TestCase):
    def test_without_token(self):
        self.assertEqual(
            module.build_headers(),
            {'Accept': 'application/vnd.github.v3+json'},
        )

    def test_with_token(self):
        self.assertEqual(
            module.build_headers('abc'),
            {
                'Accept': 'application/vnd.github.v3+json',
                'Authorization': 'token abc',
            },
        )


class TestFindDataFiles(unittest.TestCase):
    @patch('fetch_customer_data.list_repo_files')
    def test_recursively_collects_supported_files(self, mock_list_repo_files):
        mock_list_repo_files.side_effect = [
            [
                {'type': 'file', 'name': 'README.md', 'path': 'README.md', 'size': 1},
                {'type': 'dir', 'name': 'data', 'path': 'data'},
                {'type': 'file', 'name': 'customers.json', 'path': 'customers.json', 'size': 10},
            ],
            [
                {'type': 'file', 'name': 'dump.db', 'path': 'data/dump.db', 'size': 20},
                {'type': 'file', 'name': 'notes.txt', 'path': 'data/notes.txt', 'size': 5},
            ],
        ]

        result = module.find_data_files('o', 'r')
        self.assertEqual(
            [item['path'] for item in result],
            ['data/dump.db', 'customers.json'],
        )


class TestExtractJsonRecords(unittest.TestCase):
    def test_extracts_list_payload(self):
        content = b'[{"name":"Alice"},{"name":"Bob"}]'
        result = module.extract_json_records(content)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'Alice')

    def test_prefers_customer_list_inside_dict(self):
        content = b'{"meta":{"ok":true},"customers":[{"name":"Alice"}]}'
        result = module.extract_json_records(content)
        self.assertEqual(result, [{'name': 'Alice'}])


class TestExtractCsvRecords(unittest.TestCase):
    def test_extracts_rows(self):
        content = 'name,email\nAlice,alice@example.com\n'.encode('utf-8')
        result = module.extract_csv_records(content)
        self.assertEqual(result, [{'name': 'Alice', 'email': 'alice@example.com'}])


class TestExtractSqliteRecords(unittest.TestCase):
    def test_reads_customers_table(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_file:
            temp_path = temp_file.name
        try:
            connection = sqlite3.connect(temp_path)
            connection.execute(
                'CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, email TEXT)'
            )
            connection.execute(
                'INSERT INTO customers (name, email) VALUES (?, ?)',
                ('Alice', 'alice@example.com'),
            )
            connection.commit()
            connection.close()

            with open(temp_path, 'rb') as handle:
                content = handle.read()

            result = module.extract_sqlite_records(content)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['name'], 'Alice')
            self.assertEqual(result[0]['_source_table'], 'customers')
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestDeduplicateRecords(unittest.TestCase):
    def test_removes_duplicates(self):
        records = [
            {'name': 'Alice', '_source_file': 'a.json'},
            {'name': 'Alice', '_source_file': 'a.json'},
            {'name': 'Bob', '_source_file': 'b.json'},
        ]
        result = module.deduplicate_records(records)
        self.assertEqual(len(result), 2)


class TestExportToExcel(unittest.TestCase):
    def test_writes_excel_file(self):
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            output_path = temp_file.name
        try:
            module.export_to_excel(
                [{'name': 'Alice', 'email': 'alice@example.com'}],
                output_path,
            )
            workbook = load_workbook(output_path)
            worksheet = workbook.active
            self.assertEqual(worksheet['A1'].value, 'name')
            self.assertEqual(worksheet['B2'].value, 'alice@example.com')
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestFetchCustomerRecords(unittest.TestCase):
    @patch('fetch_customer_data.download_file')
    @patch('fetch_customer_data.find_data_files')
    def test_fetches_and_enriches_records(self, mock_find_data_files, mock_download_file):
        mock_find_data_files.return_value = [
            {'name': 'customers.json', 'path': 'customers.json'}
        ]
        mock_download_file.return_value = b'[{"name":"Alice"}]'

        result = module.fetch_customer_records('o', 'r')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'Alice')
        self.assertEqual(result[0]['_source_file'], 'customers.json')
        self.assertEqual(result[0]['_source_type'], 'json')


class TestMain(unittest.TestCase):
    @patch('sys.argv', ['fetch_customer_data.py'])
    def test_parse_args_uses_master_by_default(self):
        args = module.parse_args()
        self.assertEqual(args.branch, 'master')

    @patch('fetch_customer_data.export_to_excel')
    @patch('fetch_customer_data.fetch_customer_records')
    @patch('fetch_customer_data.requests.get')
    @patch('fetch_customer_data.parse_args')
    def test_main_success(self, mock_parse_args, mock_get, mock_fetch, mock_export):
        mock_parse_args.return_value = MagicMock(
            owner='o',
            repo='r',
            branch='main',
            token='',
            output='/tmp/customers.xlsx',
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'full_name': 'o/r'}
        mock_get.return_value = mock_response
        mock_fetch.return_value = [{'name': 'Alice'}]

        result = module.main()
        self.assertEqual(result, 0)
        mock_export.assert_called_once()


if __name__ == '__main__':
    unittest.main()
