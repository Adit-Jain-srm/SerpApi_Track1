"""Teams message formatting."""
import logging

import pytest
import requests

from models.tool_info import ToolInfo
from output.teams import format_tool_for_teams, send_tool_to_teams


def test_formatter_omits_duplicate_website_and_generic_features() -> None:
    same_url = ToolInfo(
        title="Nova",
        website="https://nova.example",
        source="https://nova.example",
        summary="Nova drafts launch notes.",
        features=["BPO Services", "Consultation", "Summarizes product launches"],
    )
    message = format_tool_for_teams(same_url, 1)
    assert "Website:" not in message
    assert "https://nova.example" in message
    assert "BPO Services" not in message
    assert "Consultation" not in message
    assert "Summarizes product launches" in message

    distinct = ToolInfo(
        title="Nova",
        website="https://nova.example",
        source="https://blog.example/nova",
        summary="Nova drafts launch notes.",
        features=["Summarizes product launches"],
    )
    assert "Website:" in format_tool_for_teams(distinct, 2)


def test_formatter_skips_null_features_and_non_string_tags() -> None:
    tool = ToolInfo(
        title="Nova",
        website="https://nova.example",
        source="https://nova.example",
        summary="Nova drafts launch notes.",
        features=[None, "Summarizes product launches", "Summarizes product launches"],  # type: ignore[list-item]
        tags=[1, 2],  # type: ignore[list-item]
    )
    message = format_tool_for_teams(tool, 1)
    assert message.count("Summarizes product launches") == 1
    assert "None" not in message


def test_blank_webhook_does_not_post(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args, **_kwargs):
        raise AssertionError("Teams was called")

    monkeypatch.setattr("output.teams.requests.post", boom)
    tool = ToolInfo(title="Nova", website="https://nova.example", source="https://nova.example")
    send_tool_to_teams(tool, 1, "   ")
    send_tool_to_teams(tool, 1, "")


def test_send_logs_failure_without_the_webhook(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    secret = "hook-secret-value"
    webhook = f"https://example.invalid/webhook/{secret}"
    tool = ToolInfo(title="Nova", website="https://nova.example", source="https://nova.example")

    def connection_error(*_args, **_kwargs):
        raise requests.ConnectionError(f"url: /webhook/{secret}")

    monkeypatch.setattr("output.teams.requests.post", connection_error)
    with caplog.at_level(logging.ERROR):
        send_tool_to_teams(tool, 1, webhook)
    assert "ConnectionError" in caplog.text
    assert secret not in caplog.text

    class Response:
        status_code = 500
        text = f"refused {webhook}"

    monkeypatch.setattr("output.teams.requests.post", lambda *_args, **_kwargs: Response())
    caplog.clear()
    with caplog.at_level(logging.ERROR):
        send_tool_to_teams(tool, 2, webhook)
    assert "HTTP 500" in caplog.text
    assert secret not in caplog.text
