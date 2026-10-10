"""Recency, dedupe, dry-run, and the Teams skip flag."""
import io
import logging
import sys
from datetime import datetime, timedelta, timezone

import pytest

from agents.pipeline_agent import _deduplicate, _filter_by_recency
from agents.search_agent import SearchClient
from main import main
from models.tool_info import ToolInfo


class RecordingClient:
    """Fake SerpApi client. Records params and never reads an API key."""

    def __init__(self, handler) -> None:
        self.calls: list[dict] = []
        self._handler = handler

    def search(self, params: dict) -> dict:
        snapshot = dict(params)
        self.calls.append(snapshot)
        return self._handler(snapshot)


def test_recency_keeps_missing_date_and_drops_stale_iso() -> None:
    fresh = (datetime.now(timezone.utc) - timedelta(days=1)).replace(microsecond=0).isoformat()
    tools = [
        ToolInfo(title="Missing", website="https://missing.example", publish_date=None),
        ToolInfo(title="Blank", website="https://blank.example", publish_date=""),
        ToolInfo(title="Fresh", website="https://fresh.example", publish_date=fresh),
        ToolInfo(title="Stale", website="https://stale.example", publish_date="2020-01-02T00:00:00Z"),
        ToolInfo(title="Old day", website="https://old.example", publish_date="2019-05-01"),
        ToolInfo(title="Unparsed", website="https://unparsed.example", publish_date="not-a-date"),
    ]

    kept = [tool.title for tool in _filter_by_recency(tools, days=7)]
    assert kept == ["Missing", "Blank", "Fresh", "Unparsed"]


def test_dedupe_by_title_and_website() -> None:
    first = ToolInfo(title="Widget", website="https://widget.example", summary="first")
    duplicate = ToolInfo(title="widget", website="https://widget.example", summary="second")
    other = ToolInfo(title="Other", website="https://widget.example", summary="third")

    assert _deduplicate([first, duplicate, other]) == [first, other]


def test_dedupe_tolerates_null_title_and_website() -> None:
    blank = ToolInfo(title=None, website=None)  # type: ignore[arg-type]
    named = ToolInfo(title="Widget", website="https://widget.example")
    assert _deduplicate([blank, blank, named]) == [blank, named]


def test_dry_run_does_not_fetch_or_call_azure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail_fetch(*_args, **_kwargs):
        raise AssertionError("fetch was called")

    def fail_azure(*_args, **_kwargs):
        raise AssertionError("Azure client was called")

    def fail_teams(*_args, **_kwargs):
        raise AssertionError("Teams was called")

    def fail_slack(*_args, **_kwargs):
        raise AssertionError("Slack was called")

    monkeypatch.setattr("agents.pipeline_agent.fetch_with_retries", fail_fetch)
    monkeypatch.setattr("agents.scraper_agent._get_client", fail_azure)
    monkeypatch.setattr("agents.scraper_agent.AsyncAzureOpenAI", fail_azure)
    monkeypatch.setattr("main.send_tool_to_teams", fail_teams)
    monkeypatch.setattr("main.send_tool_to_slack", fail_slack)
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://example.invalid/hook")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "test-token")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "C_TEST")
    monkeypatch.setenv("SEARCH_DAYS", "10")

    def handler(params: dict) -> dict:
        if params.get("engine") == "google":
            return {"organic_results": [{"link": "https://tools.example.com/nova", "title": "Nova"}]}
        return {
            "news_results": [
                {
                    "link": "https://tools.example.com/nova",
                    "title": "Nova",
                    "published_at": "2026-10-09",
                }
            ]
        }

    client = RecordingClient(handler)
    code = main(["--dry-run", "--days", "1"], client=client)
    assert code == 0

    output = capsys.readouterr().out
    assert "https://tools.example.com/nova" in output
    web_calls = [call for call in client.calls if call.get("engine") == "google"]
    news_calls = [call for call in client.calls if call.get("engine") == "google_news"]
    assert len(client.calls) == 10
    assert len(web_calls) == 6
    assert len(news_calls) == 4
    assert web_calls and all(call.get("tbs") == "qdr:d1" for call in web_calls)
    assert all("qdr:w" not in str(call.get("tbs", "")) for call in web_calls)
    assert all("after:" not in call["q"] for call in web_calls)
    assert news_calls and all("tbs" not in call and "after:" in call["q"] for call in news_calls)


def test_dry_run_prints_titles_outside_cp1252(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows consoles use cp1252. A snippet character must not abort the table."""

    def fail_fetch(*_args, **_kwargs):
        raise AssertionError("fetch was called")

    def fail_azure(*_args, **_kwargs):
        raise AssertionError("Azure client was called")

    def fail_teams(*_args, **_kwargs):
        raise AssertionError("Teams was called")

    def fail_slack(*_args, **_kwargs):
        raise AssertionError("Slack was called")

    raw_out = io.BytesIO()
    raw_err = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(raw_out, encoding="cp1252", errors="strict"))
    monkeypatch.setattr(sys, "stderr", io.TextIOWrapper(raw_err, encoding="cp1252", errors="strict"))
    monkeypatch.setattr("agents.pipeline_agent.fetch_with_retries", fail_fetch)
    monkeypatch.setattr("agents.scraper_agent._get_client", fail_azure)
    monkeypatch.setattr("agents.scraper_agent.AsyncAzureOpenAI", fail_azure)
    monkeypatch.setattr("main.send_tool_to_teams", fail_teams)
    monkeypatch.setattr("main.send_tool_to_slack", fail_slack)
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://example.invalid/hook")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "test-token")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "C_TEST")

    def handler(params: dict) -> dict:
        if params.get("engine") == "google":
            return {
                "organic_results": [
                    {
                        "link": "https://tools.example.com/nova",
                        "title": "Hawai\u02bbi",
                        "snippet": "Launch with \u02bb in the name",
                    }
                ]
            }
        return {"news_results": []}

    code = main(["--dry-run", "--days", "1"], client=RecordingClient(handler))
    assert code == 0
    sys.stdout.flush()
    text = raw_out.getvalue().decode("utf-8")
    assert "https://tools.example.com/nova" in text
    assert "Hawai\u02bbi" in text
    assert "Traceback" not in raw_err.getvalue().decode("utf-8", errors="replace")


def test_non_positive_days_and_url_caps_exit_cleanly(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Zero and negative caps are a usage error, not a traceback or a search."""

    def fail_search(*_args, **_kwargs):
        raise AssertionError("search was called")

    monkeypatch.setattr("main.run_pipeline", fail_search)

    for argv in (["--days", "0"], ["--days", "-1"]):
        with pytest.raises(SystemExit) as caught:
            main(argv)
        assert caught.value.code == 2
        err = capsys.readouterr().err
        assert "Traceback" not in err
        assert "--days must be a positive integer" in err

    with pytest.raises(SystemExit) as caught:
        main(["--max-urls", "0", "--dry-run"])
    assert caught.value.code == 2
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "--max-urls must be a positive integer" in err


def test_skip_teams_still_prints_summary(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def fake_pipeline(_settings, client: SearchClient | None = None) -> list[ToolInfo]:
        return [
            ToolInfo(
                title="Nova",
                website="https://nova.example",
                source="https://blog.example/nova",
                summary="A launch",
                ai_tool_annotation="ai_tool",
            )
        ]

    monkeypatch.setenv("SERPAPI_API_KEY", "test")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_KEY", "test")
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://example.invalid/hook")
    monkeypatch.setattr("main.run_pipeline", fake_pipeline)
    sent: list = []
    monkeypatch.setattr("main.send_tool_to_teams", lambda *args, **kwargs: sent.append(args))

    assert main(["--skip-teams"]) == 0
    assert sent == []
    assert "Nova" in capsys.readouterr().out

    assert main([]) == 0
    assert len(sent) == 1


def test_teams_failure_does_not_block_slack(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A Teams error is logged without the webhook and Slack still posts."""
    secret = "hook-secret-value"
    slack_calls: list = []

    async def fake_pipeline(_settings, client: SearchClient | None = None) -> list[ToolInfo]:
        return [
            ToolInfo(
                title="Nova",
                website="https://nova.example",
                source="https://blog.example/nova",
                summary="A launch",
                ai_tool_annotation="ai_tool",
            )
        ]

    def boom(*_args, **_kwargs):
        raise RuntimeError(f"https://example.invalid/webhook/{secret}")

    monkeypatch.setenv("SERPAPI_API_KEY", "test")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_KEY", "test")
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", f"https://example.invalid/webhook/{secret}")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "test-token")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "C_TEST")
    monkeypatch.setattr("main.run_pipeline", fake_pipeline)
    monkeypatch.setattr("main.send_tool_to_teams", boom)
    monkeypatch.setattr("main.send_tool_to_slack", lambda *args, **kwargs: slack_calls.append(args))

    with caplog.at_level(logging.ERROR):
        assert main([]) == 0
    assert len(slack_calls) == 1
    assert secret not in caplog.text
