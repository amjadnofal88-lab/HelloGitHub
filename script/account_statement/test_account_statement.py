#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Tests for account_statement.py
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open

# Add the script directory to path so we can import the module
sys.path.insert(0, os.path.dirname(__file__))

import account_statement as as_module


class TestAuthHeaders(unittest.TestCase):
    def setUp(self):
        # Save original ACCOUNT state
        self._orig_token = as_module.ACCOUNT['token']

    def tearDown(self):
        as_module.ACCOUNT['token'] = self._orig_token

    def test_no_token_returns_empty_dict(self):
        as_module.ACCOUNT['token'] = ''
        self.assertEqual(as_module._auth_headers(), {})

    def test_with_token_returns_authorization_header(self):
        as_module.ACCOUNT['token'] = 'mytoken123'
        headers = as_module._auth_headers()
        self.assertEqual(headers, {'Authorization': 'token mytoken123'})

    def test_none_token_returns_empty_dict(self):
        as_module.ACCOUNT['token'] = None
        self.assertEqual(as_module._auth_headers(), {})


class TestGetUserProfile(unittest.TestCase):
    @patch('account_statement.requests.get')
    def test_success_returns_json(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'login': 'testuser', 'name': 'Test User'}
        mock_get.return_value = mock_response

        result = as_module.get_user_profile('testuser')
        self.assertEqual(result, {'login': 'testuser', 'name': 'Test User'})
        mock_get.assert_called_once()

    @patch('account_statement.requests.get')
    def test_failure_returns_none(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = as_module.get_user_profile('nonexistent')
        self.assertIsNone(result)

    @patch('account_statement.requests.get')
    def test_uses_correct_url(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        as_module.get_user_profile('octocat')
        call_url = mock_get.call_args[0][0]
        self.assertIn('/users/octocat', call_url)

    @patch('account_statement.requests.get')
    def test_server_error_returns_none(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = as_module.get_user_profile('testuser')
        self.assertIsNone(result)


class TestGetUserRepos(unittest.TestCase):
    @patch('account_statement.requests.get')
    def test_single_page_returns_sorted_repos(self, mock_get):
        repos = [
            {'name': 'repo-a', 'stargazers_count': 10},
            {'name': 'repo-b', 'stargazers_count': 50},
            {'name': 'repo-c', 'stargazers_count': 5},
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = [repos, []]
        mock_get.return_value = mock_response

        result = as_module.get_user_repos('testuser')
        self.assertEqual(result[0]['name'], 'repo-b')
        self.assertEqual(result[1]['name'], 'repo-a')
        self.assertEqual(result[2]['name'], 'repo-c')

    @patch('account_statement.requests.get')
    def test_respects_top_repos_limit(self, mock_get):
        orig_top = as_module.TOP_REPOS
        as_module.TOP_REPOS = 2
        try:
            repos = [
                {'name': 'r1', 'stargazers_count': 100},
                {'name': 'r2', 'stargazers_count': 80},
                {'name': 'r3', 'stargazers_count': 60},
            ]
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.side_effect = [repos, []]
            mock_get.return_value = mock_response

            result = as_module.get_user_repos('testuser')
            self.assertEqual(len(result), 2)
        finally:
            as_module.TOP_REPOS = orig_top

    @patch('account_statement.requests.get')
    def test_api_failure_returns_empty_list(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = as_module.get_user_repos('testuser')
        self.assertEqual(result, [])

    @patch('account_statement.requests.get')
    def test_pagination_fetches_all_pages(self, mock_get):
        # First page has 100 items (full page), second page has 10, then empty
        page1 = [{'name': 'repo{}'.format(i), 'stargazers_count': i} for i in range(100)]
        page2 = [{'name': 'extra{}'.format(i), 'stargazers_count': i + 200} for i in range(10)]

        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = page1

        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = page2

        mock_response_empty = MagicMock()
        mock_response_empty.status_code = 200
        mock_response_empty.json.return_value = []

        mock_get.side_effect = [mock_response1, mock_response2, mock_response_empty]

        orig_top = as_module.TOP_REPOS
        as_module.TOP_REPOS = 200
        try:
            result = as_module.get_user_repos('testuser')
            # Total 110 repos; top by stars are the page2 extras
            self.assertEqual(len(result), 110)
            # Highest star repo should be extra9 with stars 209
            self.assertEqual(result[0]['name'], 'extra9')
        finally:
            as_module.TOP_REPOS = orig_top

    @patch('account_statement.requests.get')
    def test_empty_response_returns_empty_list(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        result = as_module.get_user_repos('testuser')
        self.assertEqual(result, [])


class TestGetUserEvents(unittest.TestCase):
    @patch('account_statement.requests.get')
    def test_success_returns_events(self, mock_get):
        events = [{'type': 'PushEvent'}, {'type': 'WatchEvent'}]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = events
        mock_get.return_value = mock_response

        result = as_module.get_user_events('testuser')
        self.assertEqual(result, events)

    @patch('account_statement.requests.get')
    def test_failure_returns_empty_list(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        result = as_module.get_user_events('testuser')
        self.assertEqual(result, [])

    @patch('account_statement.requests.get')
    def test_uses_correct_url(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        as_module.get_user_events('octocat')
        call_url = mock_get.call_args[0][0]
        self.assertIn('/users/octocat/events/public', call_url)


class TestBuildReposRows(unittest.TestCase):
    def test_empty_list_returns_empty_string(self):
        result = as_module.build_repos_rows([])
        self.assertEqual(result, '')

    def test_single_repo_row(self):
        repos = [{
            'html_url': 'https://github.com/user/repo',
            'name': 'my-repo',
            'description': 'A test repo',
            'language': 'Python',
            'stargazers_count': 42,
            'forks_count': 7,
            'updated_at': '2024-01-15T10:00:00Z',
        }]
        result = as_module.build_repos_rows(repos)
        self.assertIn('my-repo', result)
        self.assertIn('A test repo', result)
        self.assertIn('Python', result)
        self.assertIn('42', result)
        self.assertIn('7', result)
        self.assertIn('2024-01-15', result)

    def test_html_special_chars_are_escaped(self):
        repos = [{
            'html_url': 'https://github.com/user/repo',
            'name': 'repo<script>',
            'description': '<b>bold</b> & "quoted"',
            'language': 'C++',
            'stargazers_count': 0,
            'forks_count': 0,
            'updated_at': '2024-01-01T00:00:00Z',
        }]
        result = as_module.build_repos_rows(repos)
        self.assertNotIn('<script>', result)
        self.assertIn('&lt;script&gt;', result)
        self.assertIn('&amp;', result)

    def test_none_fields_handled_gracefully(self):
        repos = [{
            'html_url': None,
            'name': None,
            'description': None,
            'language': None,
            'stargazers_count': 0,
            'forks_count': 0,
            'updated_at': None,
        }]
        # Should not raise
        result = as_module.build_repos_rows(repos)
        self.assertIsInstance(result, str)

    def test_missing_optional_fields_use_defaults(self):
        repos = [{}]
        result = as_module.build_repos_rows(repos)
        self.assertIsInstance(result, str)

    def test_multiple_repos_joined(self):
        repos = [
            {'html_url': 'https://github.com/u/r1', 'name': 'r1', 'description': '',
             'language': '', 'stargazers_count': 1, 'forks_count': 0, 'updated_at': '2024-01-01T00:00:00Z'},
            {'html_url': 'https://github.com/u/r2', 'name': 'r2', 'description': '',
             'language': '', 'stargazers_count': 2, 'forks_count': 0, 'updated_at': '2024-01-01T00:00:00Z'},
        ]
        result = as_module.build_repos_rows(repos)
        self.assertEqual(result.count('<tr>'), 2)


class TestBuildEventsRows(unittest.TestCase):
    def test_empty_list_returns_empty_string(self):
        result = as_module.build_events_rows([])
        self.assertEqual(result, '')

    def test_single_event_row(self):
        events = [{
            'created_at': '2024-03-10T14:30:00Z',
            'type': 'PushEvent',
            'repo': {'name': 'user/some-repo'},
        }]
        result = as_module.build_events_rows(events)
        self.assertIn('2024-03-10 14:30:00', result)
        self.assertIn('PushEvent', result)
        self.assertIn('user/some-repo', result)
        self.assertIn('https://github.com/user/some-repo', result)

    def test_html_special_chars_are_escaped(self):
        events = [{
            'created_at': '2024-01-01T00:00:00Z',
            'type': '<script>alert(1)</script>',
            'repo': {'name': 'user/repo&name'},
        }]
        result = as_module.build_events_rows(events)
        self.assertNotIn('<script>', result)
        self.assertIn('&lt;script&gt;', result)

    def test_missing_repo_uses_empty_url(self):
        events = [{
            'created_at': '2024-01-01T00:00:00Z',
            'type': 'PushEvent',
            'repo': {},
        }]
        result = as_module.build_events_rows(events)
        self.assertIsInstance(result, str)

    def test_missing_fields_handled(self):
        events = [{}]
        result = as_module.build_events_rows(events)
        self.assertIsInstance(result, str)

    def test_multiple_events_joined(self):
        events = [
            {'created_at': '2024-01-01T00:00:00Z', 'type': 'E1', 'repo': {'name': 'u/r1'}},
            {'created_at': '2024-01-02T00:00:00Z', 'type': 'E2', 'repo': {'name': 'u/r2'}},
        ]
        result = as_module.build_events_rows(events)
        self.assertEqual(result.count('<tr>'), 2)


class TestGenerateStatement(unittest.TestCase):
    @patch('account_statement.get_user_events')
    @patch('account_statement.get_user_repos')
    @patch('account_statement.get_user_profile')
    def test_returns_none_when_profile_missing(self, mock_profile, mock_repos, mock_events):
        mock_profile.return_value = None

        result = as_module.generate_statement('nonexistent')
        self.assertIsNone(result)
        mock_repos.assert_not_called()
        mock_events.assert_not_called()

    @patch('builtins.open', new_callable=mock_open)
    @patch('account_statement.get_user_events')
    @patch('account_statement.get_user_repos')
    @patch('account_statement.get_user_profile')
    def test_generates_html_file(self, mock_profile, mock_repos, mock_events, mock_file):
        mock_profile.return_value = {
            'login': 'testuser',
            'name': 'Test User',
            'avatar_url': 'https://avatars.example.com/u/1',
            'html_url': 'https://github.com/testuser',
            'bio': 'A developer',
            'followers': 100,
            'following': 50,
            'public_repos': 10,
            'location': 'Earth',
            'company': 'ACME',
        }
        mock_repos.return_value = []
        mock_events.return_value = []

        result = as_module.generate_statement('testuser', output_dir='/tmp')
        self.assertIsNotNone(result)
        self.assertIn('statement_testuser.html', result)
        mock_file.assert_called_once()
        written = mock_file().write.call_args[0][0]
        self.assertIn('testuser', written)
        self.assertIn('Test User', written)

    @patch('builtins.open', new_callable=mock_open)
    @patch('account_statement.get_user_events')
    @patch('account_statement.get_user_repos')
    @patch('account_statement.get_user_profile')
    def test_html_escapes_username(self, mock_profile, mock_repos, mock_events, mock_file):
        mock_profile.return_value = {
            'login': '<bad>',
            'name': '<script>alert(1)</script>',
            'avatar_url': '',
            'html_url': '',
            'bio': None,
            'followers': 0,
            'following': 0,
            'public_repos': 0,
            'location': None,
            'company': None,
        }
        mock_repos.return_value = []
        mock_events.return_value = []

        as_module.generate_statement('<bad>', output_dir='/tmp')
        written = mock_file().write.call_args[0][0]
        self.assertNotIn('<script>', written)

    @patch('builtins.open', new_callable=mock_open)
    @patch('account_statement.get_user_events')
    @patch('account_statement.get_user_repos')
    @patch('account_statement.get_user_profile')
    def test_uses_default_output_dir(self, mock_profile, mock_repos, mock_events, mock_file):
        mock_profile.return_value = {
            'login': 'user', 'name': 'User', 'avatar_url': '', 'html_url': '',
            'bio': None, 'followers': 0, 'following': 0, 'public_repos': 0,
            'location': None, 'company': None,
        }
        mock_repos.return_value = []
        mock_events.return_value = []

        result = as_module.generate_statement('user', output_dir=None)
        self.assertIsNotNone(result)
        self.assertTrue(result.endswith('statement_user.html'))


class TestMain(unittest.TestCase):
    @patch('account_statement.generate_statement')
    def test_single_username(self, mock_gen):
        mock_gen.return_value = '/tmp/statement_user.html'
        with patch('sys.argv', ['account_statement.py', 'octocat']):
            as_module.main()
        mock_gen.assert_called_once_with('octocat', output_dir=None)

    @patch('account_statement.generate_statement')
    def test_multiple_usernames(self, mock_gen):
        mock_gen.return_value = '/tmp/statement.html'
        with patch('sys.argv', ['account_statement.py', 'user1', 'user2', 'user3']):
            as_module.main()
        self.assertEqual(mock_gen.call_count, 3)

    @patch('account_statement.generate_statement')
    def test_output_dir_argument(self, mock_gen):
        mock_gen.return_value = '/output/statement_user.html'
        with patch('sys.argv', ['account_statement.py', '--output-dir', '/output', 'user1']):
            as_module.main()
        mock_gen.assert_called_once_with('user1', output_dir='/output')


if __name__ == '__main__':
    unittest.main()
