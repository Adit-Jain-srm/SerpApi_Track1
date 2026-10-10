"""Azure extraction request shape and prompt rules. No network."""
import asyncio

import pytest

from agents.scraper_agent import extract_tool_info_with_llm
from utils.prompt_loader import load_prompt


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


def test_extraction_coerces_null_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """Null title, features, and tags must not reach the digest as non-strings."""
    captured: dict = {}

    class _Message:
        content = (
            '{"Title": null, "Website": null, "Core Functionality": null,'
            ' "Key Features": [null, "Writes briefs"], "Tags": [1, "launch"],'
            ' "ai_tool_annotation": null}'
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

    assert captured["max_completion_tokens"] == 800
    assert captured["temperature"] == 1
    assert "max_tokens" not in captured
    assert tool.title == ""
    assert tool.website == "https://nova.example"
    assert tool.source == "https://nova.example"
    assert tool.summary is None
    assert tool.features == ["Writes briefs"]
    assert tool.tags == ["launch"]
    assert tool.ai_tool_annotation == "not_ai_tool"


def test_prompts_reject_roundups_and_third_party_articles() -> None:
    """Listicles, news roundups, and articles about someone else's tool are not_ai_tool."""
    system = load_prompt("system_prompt.txt")
    user = load_prompt("user_prompt.txt")
    combined = f"{system}\n{user}".lower()

    assert "listicle" in combined
    assert "news roundup" in combined
    assert "someone else's tool" in combined
    assert "not_ai_tool" in combined
    assert "err on the side of 'ai_tool'" not in combined
    assert "if unsure, use 'not_ai_tool'" in user.lower()
