#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Tests for github_bot.py
"""
import os
import sys
import datetime
import unittest
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.dirname(__file__))

import github_bot as bot_module


class TestGetData(unittest.TestCase):
    @patch('github_bot.requests.get')
    def test_success_returns_json(self, mock_get):
        events = [{'type': 'WatchEvent'}, {'type': 'PushEvent'}]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = events
        mock_get.return_value = mock_response

        result = bot_module.get_data(page=1)
        self.assertEqual(result, events)

    @patch('github_bot.requests.get')
    def test_failure_returns_empty_list(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        result = bot_module.get_data(page=1)
        self.assertEqual(result, [])

    @patch('github_bot.requests.get')
    def test_page_parameter_included_in_url(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        bot_module.get_data(page=3)
        call_url = mock_get.call_args[0][0]
        self.assertIn('page=3', call_url)

    @patch('github_bot.requests.get')
    def test_default_page_is_one(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        bot_module.get_data()
        call_url = mock_get.call_args[0][0]
        self.assertIn('page=1', call_url)


class TestGetAllData(unittest.TestCase):
    @patch('github_bot.get_data')
    def test_aggregates_ten_pages(self, mock_get_data):
        mock_get_data.return_value = [{'type': 'PushEvent'}]

        result = bot_module.get_all_data()
        self.assertEqual(mock_get_data.call_count, 10)
        self.assertEqual(len(result), 10)

    @patch('github_bot.get_data')
    def test_skips_empty_pages(self, mock_get_data):
        mock_get_data.side_effect = [
            [{'type': 'PushEvent'}],
            [],
            [{'type': 'WatchEvent'}],
        ] + [[] for _ in range(7)]

        result = bot_module.get_all_data()
        # Empty pages return [] which is falsy, so only truthy pages are extended
        self.assertEqual(len(result), 2)

    @patch('github_bot.get_data')
    def test_all_pages_empty_returns_empty_list(self, mock_get_data):
        mock_get_data.return_value = []
        result = bot_module.get_all_data()
        self.assertEqual(result, [])


class TestCheckCondition(unittest.TestCase):
    def setUp(self):
        # Use a non-empty username to avoid '' being in every string
        self._orig_username = bot_module.ACCOUNT['username']
        bot_module.ACCOUNT['username'] = 'testbot'

    def tearDown(self):
        bot_module.ACCOUNT['username'] = self._orig_username

    def _make_event(self, event_type, action, repo_name, hours_ago=1):
        """Helper to build a synthetic event."""
        create_time = datetime.datetime.utcnow() - datetime.timedelta(hours=hours_ago)
        # Subtract 8 hours because check_condition adds 8 hours to created_at
        create_time_utc = create_time - datetime.timedelta(hours=8)
        return {
            'type': event_type,
            'created_at': create_time_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'payload': {'action': action},
            'repo': {'name': repo_name},
            'actor': {'login': 'someuser'},
        }

    def test_watch_event_started_recent_passes(self):
        event = self._make_event('WatchEvent', 'started', 'other/repo', hours_ago=2)
        result = bot_module.check_condition(event)
        self.assertTrue(result)

    def test_watch_event_adds_date_time_field(self):
        event = self._make_event('WatchEvent', 'started', 'other/repo', hours_ago=2)
        bot_module.check_condition(event)
        self.assertIn('date_time', event)

    def test_non_watch_event_fails(self):
        event = self._make_event('PushEvent', 'started', 'other/repo', hours_ago=2)
        result = bot_module.check_condition(event)
        self.assertFalse(result)

    def test_watch_event_not_started_fails(self):
        event = self._make_event('WatchEvent', 'other_action', 'other/repo', hours_ago=2)
        result = bot_module.check_condition(event)
        # When type is WatchEvent but action isn't 'started', outer if is true but
        # inner if is false, so function returns None (implicit)
        self.assertIsNone(result)

    def test_old_event_fails(self):
        # Event 3 days ago with DAY=1 threshold
        orig_day = bot_module.DAY
        bot_module.DAY = 1
        try:
            event = self._make_event('WatchEvent', 'started', 'other/repo', hours_ago=3 * 24)
            result = bot_module.check_condition(event)
            self.assertFalse(result)
        finally:
            bot_module.DAY = orig_day

    def test_own_repo_excluded(self):
        event = self._make_event('WatchEvent', 'started', 'testbot/my-repo', hours_ago=2)
        result = bot_module.check_condition(event)
        # Own repo name contains ACCOUNT['username'], so inner if fails → returns None
        self.assertIsNone(result)


class TestAnalyze(unittest.TestCase):
    def setUp(self):
        self._orig_username = bot_module.ACCOUNT['username']
        bot_module.ACCOUNT['username'] = 'testbot'

    def tearDown(self):
        bot_module.ACCOUNT['username'] = self._orig_username

    def _make_event(self, event_type, action, repo_name, hours_ago=1):
        create_time = datetime.datetime.utcnow() - datetime.timedelta(hours=hours_ago)
        create_time_utc = create_time - datetime.timedelta(hours=8)
        return {
            'type': event_type,
            'created_at': create_time_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'payload': {'action': action},
            'repo': {'name': repo_name},
        }

    def test_filters_non_matching_events(self):
        events = [
            self._make_event('PushEvent', 'started', 'u/r1'),
            self._make_event('WatchEvent', 'started', 'u/r2'),
        ]
        result = bot_module.analyze(events)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['repo']['name'], 'u/r2')

    def test_empty_input_returns_empty(self):
        result = bot_module.analyze([])
        self.assertEqual(result, [])

    def test_all_matching_returned(self):
        events = [
            self._make_event('WatchEvent', 'started', 'u/r1'),
            self._make_event('WatchEvent', 'started', 'u/r2'),
        ]
        result = bot_module.analyze(events)
        self.assertEqual(len(result), 2)


class TestGetStars(unittest.TestCase):
    def _make_watch_event(self, user, repo_name, repo_url, date_time):
        return {
            'actor': {
                'login': user,
                'avatar_url': 'https://avatars.example.com/{}'.format(user),
            },
            'repo': {
                'name': repo_name,
                'url': repo_url,
            },
            'date_time': date_time,
        }

    @patch('github_bot.requests.get')
    def test_fetches_and_returns_project_info(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {'stargazers_count': 200}
        mock_get.return_value = mock_response

        data = [self._make_watch_event('user1', 'user1/repo', 'https://api.github.com/repos/user1/repo', '2024-01-01 10:00:00')]
        result = bot_module.get_stars(data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['repo_stars'], 200)
        self.assertEqual(result[0]['user'], 'user1')
        self.assertEqual(result[0]['repo_name'], 'user1/repo')

    @patch('github_bot.requests.get')
    def test_filters_out_repos_below_stars_threshold(self, mock_get):
        orig_stars = bot_module.STARS
        bot_module.STARS = 100
        try:
            mock_response = MagicMock()
            mock_response.json.return_value = {'stargazers_count': 50}
            mock_get.return_value = mock_response

            data = [self._make_watch_event('user1', 'user1/repo', 'https://api.github.com/repos/user1/repo', '2024-01-01 10:00:00')]
            result = bot_module.get_stars(data)
            self.assertEqual(result, [])
        finally:
            bot_module.STARS = orig_stars

    @patch('github_bot.requests.get')
    def test_includes_repos_at_or_above_threshold(self, mock_get):
        orig_stars = bot_module.STARS
        bot_module.STARS = 100
        try:
            mock_response = MagicMock()
            mock_response.json.return_value = {'stargazers_count': 100}
            mock_get.return_value = mock_response

            data = [self._make_watch_event('user1', 'user1/repo', 'https://api.github.com/repos/user1/repo', '2024-01-01 10:00:00')]
            result = bot_module.get_stars(data)
            self.assertEqual(len(result), 1)
        finally:
            bot_module.STARS = orig_stars

    @patch('github_bot.requests.get')
    def test_exception_sets_stars_to_negative_one(self, mock_get):
        mock_get.side_effect = Exception('network error')

        data = [self._make_watch_event('user1', 'user1/repo', 'https://api.github.com/repos/user1/repo', '2024-01-01 10:00:00')]
        result = bot_module.get_stars(data)
        # repo_stars == -1 means it's included (could not fetch)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['repo_stars'], -1)

    @patch('github_bot.requests.get')
    def test_sorted_by_stars_descending(self, mock_get):
        mock_response_high = MagicMock()
        mock_response_high.json.return_value = {'stargazers_count': 500}
        mock_response_low = MagicMock()
        mock_response_low.json.return_value = {'stargazers_count': 150}

        mock_get.side_effect = [mock_response_low, mock_response_high]

        data = [
            self._make_watch_event('u1', 'u1/r1', 'https://api.github.com/repos/u1/r1', '2024-01-01 10:00:00'),
            self._make_watch_event('u2', 'u2/r2', 'https://api.github.com/repos/u2/r2', '2024-01-01 11:00:00'),
        ]
        orig_stars = bot_module.STARS
        bot_module.STARS = 100
        try:
            result = bot_module.get_stars(data)
            self.assertEqual(result[0]['repo_stars'], 500)
            self.assertEqual(result[1]['repo_stars'], 150)
        finally:
            bot_module.STARS = orig_stars

    @patch('github_bot.requests.get')
    def test_empty_response_sets_stars_to_negative_one(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = None
        mock_get.return_value = mock_response

        data = [self._make_watch_event('user1', 'user1/repo', 'https://api.github.com/repos/user1/repo', '2024-01-01')]
        result = bot_module.get_stars(data)
        self.assertEqual(result[0]['repo_stars'], -1)


class TestMakeContent(unittest.TestCase):
    @patch('github_bot.get_stars')
    @patch('github_bot.analyze')
    @patch('github_bot.get_all_data')
    def test_returns_list_of_html_rows(self, mock_get_all, mock_analyze, mock_get_stars):
        mock_get_all.return_value = []
        mock_analyze.return_value = []
        mock_get_stars.return_value = [
            {
                'avatar_url': 'https://avatars.example.com/u/1',
                'user_url': 'https://github.com/user1',
                'user': 'user1',
                'repo_url': 'https://github.com/user1/repo',
                'repo_name': 'user1/repo',
                'date_time': '2024-01-01 10:00:00',
                'repo_stars': 200,
            }
        ]

        result = bot_module.make_content()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn('user1', result[0])
        self.assertIn('200', result[0])

    @patch('github_bot.get_stars')
    @patch('github_bot.analyze')
    @patch('github_bot.get_all_data')
    def test_returns_empty_list_when_no_data(self, mock_get_all, mock_analyze, mock_get_stars):
        mock_get_all.return_value = []
        mock_analyze.return_value = []
        mock_get_stars.return_value = []

        result = bot_module.make_content()
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
