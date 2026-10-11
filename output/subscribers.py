"""Deliver a finished digest to signed-in subscribers."""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable
from urllib.parse import urlparse

import requests

from models.tool_info import ToolInfo
from output.slack import format_tool_for_slack
from output.teams import format_tool_for_teams
from utils.url_safety import UnsafeURL, validate_url

Poster = Callable[[str, dict[str, str]], int]


def _https(url: object) -> str | None:
    if not isinstance(url, str) or not url.strip():
        return None
    if urlparse(url.strip()).scheme.lower() != "https":
        return None
    try:
        return validate_url(url)
    except UnsafeURL:
        return None


def _post(url: str, payload: dict[str, str]) -> int:
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, timeout=15, allow_redirects=False)
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(0.5 * (2**attempt))
            continue
        if response.status_code not in {429, 500, 502, 503, 504} or attempt == 2:
            return response.status_code
        time.sleep(0.5 * (2**attempt))
    return 599


def _load_rows(base: str, secret: str) -> list[dict]:
    rows: list[dict] = []
    for start in range(0, 1_000_000, 1_000):
        try:
            response = requests.get(
                f"{base.rstrip('/')}/rest/v1/subscriptions",
                params={"active": "eq.true", "select": "teams_webhook_url,slack_webhook_url"},
                headers={
                    "apikey": secret,
                    "Authorization": f"Bearer {secret}",
                    "Range": f"{start}-{start + 999}",
                },
                timeout=15,
            )
        except requests.RequestException as exc:
            logging.error("Subscriber lookup failed: %s", type(exc).__name__)
            return []
        if response.status_code not in (200, 206):
            logging.error("Subscriber lookup failed: HTTP %s", response.status_code)
            return []
        try:
            page = response.json()
        except ValueError:
            logging.error("Subscriber lookup failed: invalid JSON")
            return []
        if not isinstance(page, list):
            logging.error("Subscriber lookup failed: expected a list")
            return []
        rows.extend(row for row in page if isinstance(row, dict))
        if len(page) < 1_000:
            return rows
    logging.error("Subscriber lookup exceeded the pagination safety limit.")
    return []


def notify_subscribers(tools: list[ToolInfo], poster: Poster = _post) -> dict[str, int]:
    """Post each kept tool to every active subscriber webhook."""
    stats = {"sent": 0, "failed": 0, "skipped": 0}
    base = (os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or "").strip()
    secret = (os.environ.get("SUPABASE_SECRET_KEY") or "").strip()
    if not base or not secret:
        logging.info("Subscriber delivery skipped. Supabase secret is unset.")
        stats["skipped"] = 1
        return stats

    kept = [tool for tool in tools if tool.ai_tool_annotation == "ai_tool"]
    if not kept:
        logging.info("Subscriber delivery skipped. No tools to send.")
        stats["skipped"] = 1
        return stats

    rows = _load_rows(base, secret)
    jobs: list[tuple[str, dict[str, str], str]] = []
    for index, tool in enumerate(kept, 1):
        for row in rows:
            teams = _https(row.get("teams_webhook_url"))
            slack = _https(row.get("slack_webhook_url"))
            for url, payload, channel in (
                (teams, {"text": format_tool_for_teams(tool, index)}, "Teams"),
                (slack, {"text": format_tool_for_slack(tool, index)}, "Slack"),
            ):
                if not url:
                    continue
                jobs.append((url, payload, channel))

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(poster, url, payload): channel
            for url, payload, channel in jobs
        }
        for future in as_completed(futures):
            channel = futures[future]
            try:
                status = future.result()
            except Exception as exc:
                logging.error("Subscriber %s post failed: %s", channel, type(exc).__name__)
                stats["failed"] += 1
            else:
                if status == 200:
                    stats["sent"] += 1
                else:
                    stats["failed"] += 1

    logging.info("Subscriber delivery finished. sent=%s failed=%s", stats["sent"], stats["failed"])
    return stats
