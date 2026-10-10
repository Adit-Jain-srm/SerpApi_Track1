"""Slack formatting and delivery. Dry-run never posts."""
import logging

import pytest
import requests

from main import main
from models.tool_info import ToolInfo
from output.slack import format_tool_for_slack, send_tool_to_slack


def _tool(*, website: str, source: str, annotation: str = "ai_tool") -> ToolInfo:
    return ToolInfo(
        title="Nova",
        website=website,
        source=source,
        summary="Nova drafts launch notes.",
        features=["BPO Services", "Consultation", "Summarizes product launches"],
        pricing="Free for founders",
        target_audience="Founders",
        ai_tool_annotation=annotation,
    )


def test_formatter_omits_duplicate_website_line() -> None:
    same_url = "https://nova.example"
    message = format_tool_for_slack(_tool(website=same_url, source=same_url), 1)
    assert "Website:" not in message
    assert same_url in message
    assert "BPO Services" not in message
    assert "Consultation" not in message
    assert "Summarizes product launches" in message
    assert "Founders" in message
    assert "Free for founders" in message
    assert "Nova drafts launch notes." in message

    distinct = format_tool_for_slack(
        _tool(website="https://nova.example", source="https://blog.example/nova"),
        2,
    )
    assert "Website:" in distinct
    assert "https://nova.example" in distinct
    assert "https://blog.example/nova" in distinct

    messy = _tool(website="https://nova.example", source="https://nova.example")
    messy.features = [None, "Summarizes product launches", "Summarizes product launches"]  # type: ignore[list-item]
    again = format_tool_for_slack(messy, 3)
    assert again.count("Summarizes product launches") == 1
    assert "None" not in again


def test_dry_run_does_not_call_slack(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_slack(*_args, **_kwargs):
        raise AssertionError("Slack was called")

    def fail_teams(*_args, **_kwargs):
        raise AssertionError("Teams was called")

    async def fake_pipeline(settings, client=None):
        assert settings.dry_run is True
        return [_tool(website="https://nova.example", source="https://nova.example")]

    monkeypatch.setattr("main.send_tool_to_slack", fail_slack)
    monkeypatch.setattr("main.send_tool_to_teams", fail_teams)
    monkeypatch.setattr("main.run_pipeline", fake_pipeline)
    monkeypatch.setenv("SERPAPI_API_KEY", "test")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "test-token")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "C_TEST")
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://example.invalid/hook")

    assert main(["--dry-run"]) == 0


def test_skip_flags_and_slack_errors_leave_the_run_going(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    slack_calls: list = []
    teams_calls: list = []

    async def fake_pipeline(_settings, client=None):
        return [
            _tool(website="https://nova.example", source="https://blog.example/nova"),
            _tool(
                website="https://other.example",
                source="https://other.example",
                annotation="not_ai_tool",
            ),
        ]

    monkeypatch.setattr("main.run_pipeline", fake_pipeline)
    monkeypatch.setattr("main.send_tool_to_slack", lambda *args, **kwargs: slack_calls.append(args))
    monkeypatch.setattr("main.send_tool_to_teams", lambda *args, **kwargs: teams_calls.append(args))
    monkeypatch.setenv("SERPAPI_API_KEY", "test")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_KEY", "test")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "test-token")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "C_TEST")
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://example.invalid/hook")

    assert main(["--skip-slack"]) == 0
    assert slack_calls == []
    assert len(teams_calls) == 1
    assert "Nova" in capsys.readouterr().out

    slack_calls.clear()
    teams_calls.clear()
    assert main(["--skip-teams"]) == 0
    assert teams_calls == []
    assert len(slack_calls) == 1
    assert "Nova" in capsys.readouterr().out

    def boom(*_args, **_kwargs):
        raise RuntimeError("slack down")

    monkeypatch.setattr("main.send_tool_to_slack", boom)
    teams_calls.clear()
    assert main([]) == 0
    assert len(teams_calls) == 1


def test_send_logs_slack_error_without_the_token(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    token = "test-token"
    captured: dict = {}

    class Response:
        status_code = 200

        def json(self) -> dict:
            return {"ok": False, "error": "channel_not_found"}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["timeout"] = timeout
        captured["channel"] = None if json is None else json.get("channel")
        captured["text"] = "" if json is None else json.get("text", "")
        authorization = "" if headers is None else str(headers.get("Authorization", ""))
        captured["bearer"] = authorization.startswith("Bearer ") and token in authorization
        return Response()

    monkeypatch.setattr("output.slack.requests.post", fake_post)
    tool = _tool(website="https://nova.example", source="https://nova.example")
    with caplog.at_level(logging.ERROR):
        send_tool_to_slack(tool, 3, token, "C_TEST")

    assert captured["url"] == "https://slack.com/api/chat.postMessage"
    assert captured["timeout"] == 15
    assert captured["channel"] == "C_TEST"
    assert captured["bearer"] is True
    assert "Website:" not in captured["text"]
    assert "channel_not_found" in caplog.text
    assert token not in caplog.text


def test_send_swallows_request_errors(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    token = "test-token"

    def fake_post(*_args, **_kwargs):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr("output.slack.requests.post", fake_post)
    tool = _tool(website="https://nova.example", source="https://blog.example/nova")
    with caplog.at_level(logging.ERROR):
        send_tool_to_slack(tool, 1, token, "C_TEST")

    assert "Slack post failed" in caplog.text
    assert token not in caplog.text
