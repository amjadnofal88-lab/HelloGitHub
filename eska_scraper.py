#!/usr/bin/env python3
"""Simple authenticated scraper with secure password handling."""

from __future__ import annotations

import argparse
import getpass
import os
import re
from html import unescape
from html.parser import HTMLParser

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch a page and print a compact text preview.")
    parser.add_argument("url", help="Target page URL to scrape")
    parser.add_argument("--username", default=os.getenv("ESKA_USER"), help="Username (or set ESKA_USER)")
    parser.add_argument(
        "--password",
        default=None,
        help="Password (or set ESKA_PASS to avoid exposing it in shell history)",
    )
    parser.add_argument("--timeout", type=float, default=20.0, help="Request timeout in seconds")
    return parser.parse_args()


def resolve_password(cli_password: str | None, username: str | None) -> str | None:
    if not username:
        return None
    if cli_password:
        return cli_password
    env_password = os.getenv("ESKA_PASS")
    if env_password:
        return env_password
    return getpass.getpass("ESKA password: ")


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._ignored_depth = 0
        self.chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in {"script", "style"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"} and self._ignored_depth > 0:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.chunks.append(data)


class _TitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._inside_title = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "title":
            self._inside_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._inside_title = False

    def handle_data(self, data: str) -> None:
        if self._inside_title:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _TextParser()
    parser.feed(html)
    text = unescape(" ".join(parser.chunks))
    return re.sub(r"\s+", " ", text).strip()


def extract_title(html: str) -> str:
    parser = _TitleParser()
    parser.feed(html)
    if not parser.parts:
        return "(no title found)"
    return re.sub(r"\s+", " ", unescape(" ".join(parser.parts))).strip()


def main() -> None:
    args = parse_args()
    password = resolve_password(args.password, args.username)

    auth = None
    if args.username:
        auth = (args.username, password or "")

    try:
        response = requests.get(args.url, auth=auth, timeout=args.timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SystemExit(f"Request failed: {exc}") from exc

    html = response.text
    print(f"URL: {args.url}")
    print(f"Title: {extract_title(html)}")

    text = html_to_text(html)
    preview = text[:500] + ("..." if len(text) > 500 else "")
    print("Preview:")
    print(preview)


if __name__ == "__main__":
    main()
