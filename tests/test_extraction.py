"""Azure extraction request shape. No network."""
import asyncio

import pytest

from agents.scraper_agent import extract_tool_info_with_llm


def test_extraction_sends_max_completion_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    """Newer Azure chat deployments reject max_tokens. The call must use max_completion_tokens."""
    captured: dict = {}

    class _Message:
        content = (
            '{"Title":"Nova","Core Functionality":"Writes briefs",'
            '"ai_tool_annotation":"ai_tool"}'
        )

    class _Choice:
        message = _Message()

    class _Response:
        choices = [_Choice()]

    class _Completions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return _Response()

    class _Chat:
        completions = _Completions()

    class _Client:
        chat = _Chat()

    monkeypatch.setattr("agents.scraper_agent._get_client", lambda: _Client())
    monkeypatch.setattr("agents.scraper_agent._deployment", "gpt-4o")
    monkeypatch.setattr(
        "agents.scraper_agent._get_prompts",
        lambda: ("system", "URL: {url}\nHTML: {html_trunc}"),
    )

    tool = asyncio.run(extract_tool_info_with_llm("<p>Nova</p>", "https://nova.example"))

    assert "max_tokens" not in captured
    assert captured["max_completion_tokens"] == 800
    assert captured["temperature"] == 1
    assert captured["model"] == "gpt-4o"
    assert tool.title == "Nova"
    assert tool.ai_tool_annotation == "ai_tool"
