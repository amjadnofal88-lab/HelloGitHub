#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Desc    :   Generate GitHub account statements for one or more users
"""
该脚本主要用于：生成 GitHub 用户的账户报告（Account Statement）

支持为主账户和备用账户生成报告，内容包括：
- 用户基本信息（名称、头像、简介、关注者/关注数）
- 公开仓库列表（按 star 数量降序）
- 最近的 GitHub 活动事件
"""
import html as html_module
import os
import logging
import datetime
import argparse
import shutil
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.WARNING,
    filename=os.path.join(os.path.dirname(__file__), 'account_statement_log.txt'),
    filemode='a',
    format='%(name)s %(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s'
)
logger = logging.getLogger('AccountStatement')

# GitHub API base URL
GITHUB_API = 'https://api.github.com'

# Optional GitHub Personal Access Token read from the environment variable
# GITHUB_TOKEN.  Setting this increases the API rate limit from 60 to
# 5000 requests per hour.
_GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')

# Timeout (in seconds) for every outbound HTTP request
_REQUEST_TIMEOUT = 30

# Number of top repositories to include in the statement
TOP_REPOS = 10

# Number of recent events to include in the statement
RECENT_EVENTS = 20

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>GitHub Account Statement — {username}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    h1, h2 {{ color: #333; }}
    .profile {{ display: flex; align-items: center; margin-bottom: 20px; }}
    .profile img {{ border-radius: 50%; margin-right: 20px; }}
    .profile-info p {{ margin: 4px 0; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 30px; }}
    th, td {{ border: 1px solid #ccc; padding: 8px 12px; text-align: left; }}
    th {{ background-color: #f2f2f2; }}
    a {{ color: #0366d6; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .generated-at {{ color: #888; font-size: 0.9em; }}
  </style>
</head>
<body>
  <h1>GitHub Account Statement</h1>
  <p class="generated-at">Generated at: {generated_at}</p>

  <div class="profile">
    <img src="{avatar_url}" width="80" height="80" alt="{username}">
    <div class="profile-info">
      <h2><a href="{html_url}">{name}</a> ({username})</h2>
      <p>{bio}</p>
      <p>Followers: <strong>{followers}</strong> &nbsp;|&nbsp; Following: <strong>{following}</strong> &nbsp;|&nbsp; Public Repos: <strong>{public_repos}</strong></p>
      <p>Location: {location} &nbsp;|&nbsp; Company: {company}</p>
    </div>
  </div>

  <h2>Top Repositories (by Stars)</h2>
  <table>
    <tr>
      <th>Repository</th>
      <th>Description</th>
      <th>Language</th>
      <th>Stars</th>
      <th>Forks</th>
      <th>Updated</th>
    </tr>
    {repos_rows}
  </table>

  <h2>Recent Activity</h2>
  <table>
    <tr>
      <th>Date</th>
      <th>Event Type</th>
      <th>Repository</th>
    </tr>
    {events_rows}
  </table>
</body>
</html>
"""


def _auth_headers():
    """Return authentication headers if a token is configured, otherwise empty dict."""
    if _GITHUB_TOKEN:
        return {'Authorization': 'token {}'.format(_GITHUB_TOKEN)}
    return {}


def _get(url):
    """Perform a GET request with auth headers and a timeout.

    Returns the ``requests.Response`` object, or raises on connection errors.
    """
    return requests.get(url, headers=_auth_headers(), timeout=_REQUEST_TIMEOUT)


def get_user_profile(username):
    """Fetch a GitHub user's public profile."""
    url = '{}/users/{}'.format(GITHUB_API, username)
    response = _get(url)
    if response.status_code == 200:
        return response.json()
    elif response.status_code in (403, 429):
        logger.error('Rate limit exceeded while fetching profile for %s (HTTP %s)',
                     username, response.status_code)
        print('ERROR: GitHub API rate limit exceeded. Set the GITHUB_TOKEN environment '
              'variable to increase the limit from 60 to 5000 requests per hour.')
        return None
    else:
        logger.error('Failed to fetch profile for %s: %s', username, response.status_code)
        return None


def get_user_repos(username):
    """Fetch all public repositories for a user, sorted by stars descending."""
    repos = []
    page = 1
    per_page = 100
    while True:
        url = '{}/users/{}/repos?per_page={}&page={}'.format(
            GITHUB_API, username, per_page, page)
        response = _get(url)
        if response.status_code in (403, 429):
            logger.error('Rate limit exceeded while fetching repos for %s (HTTP %s)',
                         username, response.status_code)
            print('ERROR: GitHub API rate limit exceeded. Set the GITHUB_TOKEN environment '
                  'variable to increase the limit from 60 to 5000 requests per hour.')
            break
        if response.status_code != 200:
            logger.error('Failed to fetch repos for %s (page %d): %s',
                         username, page, response.status_code)
            break
        data = response.json()
        if not data:
            break
        repos.extend(data)
        # If fewer results than requested, we have reached the last page
        if len(data) < per_page:
            break
        page += 1
    repos.sort(key=lambda r: r.get('stargazers_count', 0), reverse=True)
    return repos[:TOP_REPOS]


def get_user_events(username):
    """Fetch recent public events for a user."""
    url = '{}/users/{}/events/public?per_page={}'.format(GITHUB_API, username, RECENT_EVENTS)
    response = _get(url)
    if response.status_code == 200:
        return response.json()
    elif response.status_code in (403, 429):
        logger.error('Rate limit exceeded while fetching events for %s (HTTP %s)',
                     username, response.status_code)
        return []
    else:
        logger.error('Failed to fetch events for %s: %s', username, response.status_code)
        return []


def build_repos_rows(repos):
    """Build HTML table rows for repositories."""
    rows = []
    for repo in repos:
        updated = repo.get('updated_at', '')[:10]
        row = (
            '<tr>'
            '<td><a href="{html_url}">{name}</a></td>'
            '<td>{description}</td>'
            '<td>{language}</td>'
            '<td>{stars}</td>'
            '<td>{forks}</td>'
            '<td>{updated}</td>'
            '</tr>'
        ).format(
            html_url=html_module.escape(repo.get('html_url', '')),
            name=html_module.escape(repo.get('name', '')),
            description=html_module.escape(repo.get('description') or ''),
            language=html_module.escape(repo.get('language') or ''),
            stars=repo.get('stargazers_count', 0),
            forks=repo.get('forks_count', 0),
            updated=html_module.escape(updated),
        )
        rows.append(row)
    return '\n    '.join(rows)


def build_events_rows(events):
    """Build HTML table rows for events."""
    rows = []
    for event in events:
        created_at = event.get('created_at', '')[:19].replace('T', ' ')
        event_type = event.get('type', '')
        repo_name = event.get('repo', {}).get('name', '')
        repo_url = 'https://github.com/' + repo_name if repo_name else ''
        row = (
            '<tr>'
            '<td>{created_at}</td>'
            '<td>{event_type}</td>'
            '<td><a href="{repo_url}">{repo_name}</a></td>'
            '</tr>'
        ).format(
            created_at=html_module.escape(created_at),
            event_type=html_module.escape(event_type),
            repo_url=html_module.escape(repo_url),
            repo_name=html_module.escape(repo_name),
        )
        rows.append(row)
    return '\n    '.join(rows)


def copy_to_icloud(source_path, icloud_folder='GitHub Statements'):
    """Copy a generated statement file to iCloud Drive.

    :param source_path: Path to the local file to copy (str or Path).
    :param icloud_folder: Sub-folder name inside iCloud Drive (default: 'GitHub Statements').
    :return: Destination Path on success, None if iCloud Drive is not available or copy fails.
    """
    icloud_drive = Path(os.environ.get(
        'ICLOUD_DRIVE_PATH',
        str(Path.home() / 'Library' / 'Mobile Documents' / 'com~apple~CloudDocs'),
    ))
    if not icloud_drive.exists():
        logger.warning('iCloud Drive not found at %s. Skipping iCloud export.', icloud_drive)
        print('WARNING: iCloud Drive not found at {}. Skipping iCloud export.'.format(icloud_drive))
        return None

    destination = icloud_drive / icloud_folder / Path(source_path).name
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source_path, destination)
    except OSError as exc:
        logger.error('Failed to copy %s to iCloud Drive: %s', source_path, exc)
        print('ERROR: Could not copy to iCloud Drive: {}'.format(exc))
        return None

    print('Copied to iCloud Drive: {}'.format(destination))
    return destination


def generate_statement(username, output_dir=None, icloud_folder=None):
    """
    Generate an HTML account statement for the given GitHub username.

    :param username: GitHub username
    :param output_dir: Directory to write the HTML file. Defaults to script directory.
    :param icloud_folder: If set, also copy the generated file to this iCloud Drive
        sub-folder (e.g. 'GitHub Statements'). Pass None to skip iCloud export.
    :return: Path to the generated HTML file, or None on failure.
    """
    print('Fetching data for user: {}'.format(username))

    profile = get_user_profile(username)
    if profile is None:
        print('ERROR: Could not fetch profile for "{}". Check the username and try again.'.format(username))
        return None

    repos = get_user_repos(username)
    events = get_user_events(username)

    repos_rows = build_repos_rows(repos)
    events_rows = build_events_rows(events)

    generated_at = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

    html = HTML_TEMPLATE.format(
        username=html_module.escape(username),
        generated_at=html_module.escape(generated_at),
        avatar_url=html_module.escape(profile.get('avatar_url', '')),
        html_url=html_module.escape(profile.get('html_url', '')),
        name=html_module.escape(profile.get('name') or username),
        bio=html_module.escape(profile.get('bio') or ''),
        followers=profile.get('followers', 0),
        following=profile.get('following', 0),
        public_repos=profile.get('public_repos', 0),
        location=html_module.escape(profile.get('location') or 'N/A'),
        company=html_module.escape(profile.get('company') or 'N/A'),
        repos_rows=repos_rows,
        events_rows=events_rows,
    )

    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(__file__))

    output_path = os.path.join(output_dir, 'statement_{}.html'.format(username))
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print('Statement saved to: {}'.format(output_path))

    if icloud_folder is not None:
        copy_to_icloud(output_path, icloud_folder=icloud_folder)

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Generate GitHub account statements for one or more users.'
    )
    parser.add_argument(
        'usernames',
        nargs='+',
        help='One or more GitHub usernames to generate statements for.'
    )
    parser.add_argument(
        '--output-dir',
        default=None,
        help='Directory to write the HTML statement files (default: script directory).'
    )
    parser.add_argument(
        '--icloud',
        action='store_true',
        default=False,
        help='Copy each generated statement to iCloud Drive (macOS only).'
    )
    parser.add_argument(
        '--icloud-folder',
        default='GitHub Statements',
        help='Sub-folder inside iCloud Drive to copy statements into '
             '(default: "GitHub Statements"). Only used when --icloud is set.'
    )
    args = parser.parse_args()

    icloud_folder = args.icloud_folder if args.icloud else None
    for username in args.usernames:
        generate_statement(username, output_dir=args.output_dir, icloud_folder=icloud_folder)


if __name__ == '__main__':
    main()
