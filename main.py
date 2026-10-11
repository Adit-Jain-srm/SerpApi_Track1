"""
main.py: Entry point for the AI Tool Discovery Agent.
Sets up logging, runs the async pipeline, prints results, and optionally posts to Microsoft Teams and Slack.
"""
import argparse
import asyncio
import logging
import os
import sys
from dataclasses import replace
from typing import Any

from agents.config_agent import (
    Settings,
    load_settings,
    require_serpapi_key,
    setup_logging,
    validate_critical_config,
)
from agents.pipeline_agent import run_pipeline
from agents.search_agent import SearchClient, SearchFailed
from output.console import print_summary
from output.slack import send_tool_to_slack
from output.subscribers import notify_subscribers
from output.teams import send_tool_to_teams


def _configure_stdio() -> None:
    """Print search text on Windows consoles that default to cp1252.

    Snippets include characters that strict cp1252 cannot encode. UTF-8 is
    preferred. If the stream cannot change encoding, unencodable characters
    are replaced so the process still exits cleanly.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            try:
                reconfigure(errors="replace")
            except (OSError, ValueError):
                continue


def build_parser() -> argparse.ArgumentParser:
    """Build the discovery CLI."""
    parser = argparse.ArgumentParser(
        description="Discover recently launched AI tools and deliver a digest.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Date window in days. Defaults to SEARCH_DAYS from the environment, or 7.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the comparison table without fetching pages, calling Azure, or posting to Teams or Slack.",
    )
    parser.add_argument(
        "--skip-teams",
        action="store_true",
        help="Print the console summary and skip the Teams webhook.",
    )
    parser.add_argument(
        "--skip-slack",
        action="store_true",
        help="Print the console summary and skip Slack, even when the bot token and channel ID are set.",
    )
    parser.add_argument(
        "--skip-subscribers",
        action="store_true",
        help="Do not post the digest to signed-in Teams or Slack webhook subscriptions.",
    )
    parser.add_argument(
        "--max-urls",
        type=int,
        default=None,
        help="Maximum candidates to keep after comparison.",
    )
    parser.add_argument(
        "--doctor",
        "--check-apis",
        action="store_true",
        help="Run comprehensive health and connectivity checks on all APIs and database.",
    )
    return parser


def _settings_from_args(args: argparse.Namespace) -> Settings:
    settings = load_settings()
    updates: dict[str, Any] = {
        "dry_run": args.dry_run,
        "skip_teams": args.skip_teams,
        "skip_slack": args.skip_slack,
        "skip_subscribers": args.skip_subscribers,
    }
    if args.days is not None:
        updates["search_days"] = args.days
    if args.max_urls is not None:
        updates["max_urls"] = args.max_urls
    return replace(settings, **updates)


def main(argv: list[str] | None = None, client: SearchClient | None = None) -> int:
    """Run the discovery pipeline. Returns a process exit code."""
    _configure_stdio()
    setup_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.doctor:
        from check_apis import print_report, run_all_checks
        return print_report(run_all_checks())

    if args.days is not None and args.days < 1:
        parser.error("--days must be a positive integer")
    if args.max_urls is not None and args.max_urls < 1:
        parser.error("--max-urls must be a positive integer")

    settings = _settings_from_args(args)
    if settings.dry_run:
        if client is None:
            require_serpapi_key()
    else:
        validate_critical_config()

    if not settings.dry_run:
        print("Running AI Tool Discovery Agent...")

    try:
        tools = asyncio.run(run_pipeline(settings, client=client))
    except SearchFailed as exc:
        logging.error("%s", exc)
        print(str(exc), file=sys.stderr)
        return 1

    if settings.dry_run:
        return 0

    print_summary(tools)
    if settings.skip_teams:
        logging.info("Skipping Teams notification.")
    else:
        webhook = (os.environ.get("TEAMS_WEBHOOK_URL") or "").strip()
        if webhook:
            for index, tool in enumerate(tools, 1):
                if tool.ai_tool_annotation == "ai_tool":
                    try:
                        send_tool_to_teams(tool, index, webhook)
                    except Exception:
                        logging.error("Teams notification failed for tool %s.", index)
    if settings.skip_slack:
        logging.info("Skipping Slack notification.")
    else:
        slack_token = (os.environ.get("SLACK_BOT_TOKEN") or "").strip()
        slack_channel = (os.environ.get("SLACK_CHANNEL_ID") or "").strip()
        if not slack_token or not slack_channel:
            logging.warning("SLACK_BOT_TOKEN or SLACK_CHANNEL_ID not set. Skipping Slack notification.")
        else:
            for index, tool in enumerate(tools, 1):
                if tool.ai_tool_annotation == "ai_tool":
                    try:
                        send_tool_to_slack(tool, index, slack_token, slack_channel)
                    except Exception:
                        logging.error("Slack notification failed for tool %s.", index)
    if settings.skip_subscribers:
        logging.info("Skipping subscriber delivery.")
    else:
        try:
            subscriber_stats = notify_subscribers(tools)
            logging.info("Subscriber delivery summary: %s", subscriber_stats)
        except Exception:
            logging.error("Subscriber delivery failed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
