"""Azure extraction request shape and prompt rules. No network."""
import asyncio
from pathlib import Path

import pytest

from agents.scraper_agent import apply_article_website, extract_tool_info_with_llm
from models.tool_info import ToolInfo
from utils.prompt_loader import load_prompt

FIXTURE_DIR = Path(__file__).parent / "fixtures"
ARTICLE_URL = (
    "https://blog.google/innovation-and-ai/models-and-research/"
    "google-deepmind/synth-id-ai-content/"
)
PRODUCT_URL = "https://deepmind.google/models/synthid/"


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
    assert "different official product url" in combined
    assert "only an article" in combined
    assert "several different product sites" in combined
    assert "do not copy the article url" in combined
    assert "err on the side of 'ai_tool'" not in combined
    assert "if unsure, use 'not_ai_tool'" in user.lower()


def _fake_client(content: str):
    class _Message:
        def __init__(self) -> None:
            self.content = content

    class _Choice:
        message = _Message()

    class _Response:
        choices = [_Choice()]

    class _Completions:
        async def create(self, **kwargs):
            return _Response()

    class _Chat:
        completions = _Completions()

    class _Client:
        chat = _Chat()

    return _Client()


def _patch_llm(monkeypatch: pytest.MonkeyPatch, content: str) -> None:
    monkeypatch.setattr("agents.scraper_agent._get_client", lambda: _fake_client(content))
    monkeypatch.setattr("agents.scraper_agent._deployment", "gpt-4o")
    monkeypatch.setattr(
        "agents.scraper_agent._get_prompts",
        lambda: ("system", "URL: {url}\nHTML: {html_trunc}"),
    )


def test_article_fixture_uses_named_product_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """A blog post that names one product URL must not keep the article as Website."""
    html = (FIXTURE_DIR / "article_names_product.html").read_text(encoding="utf-8")
    _patch_llm(
        monkeypatch,
        (
            '{"Title":"SynthID Detector","Website":"' + ARTICLE_URL + '",'
            '"Core Functionality":"Detects SynthID watermarks.",'
            '"Source URL":"' + ARTICLE_URL + '","ai_tool_annotation":"ai_tool"}'
        ),
    )

    tool = asyncio.run(extract_tool_info_with_llm(html, ARTICLE_URL))

    assert tool.website == PRODUCT_URL
    assert tool.source == ARTICLE_URL
    assert tool.ai_tool_annotation == "ai_tool"
    assert tool.website != tool.source


def test_article_product_url_does_not_accept_third_party_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Finding a product URL fills Website. It does not turn an article into ai_tool."""
    html = (FIXTURE_DIR / "article_names_product.html").read_text(encoding="utf-8")
    _patch_llm(
        monkeypatch,
        (
            '{"Title":"SynthID Detector","Website":"' + ARTICLE_URL + '",'
            '"Source URL":"' + ARTICLE_URL + '","ai_tool_annotation":"not_ai_tool"}'
        ),
    )

    tool = asyncio.run(extract_tool_info_with_llm(html, ARTICLE_URL))

    assert tool.website == PRODUCT_URL
    assert tool.ai_tool_annotation == "not_ai_tool"


def test_article_without_product_url_stays_not_ai_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """An article that names no other URL stays not_ai_tool and may use its own URL."""
    page = "https://blog.example.com/posts/weekly-note"
    _patch_llm(
        monkeypatch,
        (
            '{"Title":"Weekly note","Website":"https://hallucinated.example/",'
            '"Source URL":"' + page + '","ai_tool_annotation":"ai_tool"}'
        ),
    )

    tool = asyncio.run(
        extract_tool_info_with_llm("<article><h1>Weekly note</h1><p>No product page.</p></article>", page)
    )

    assert tool.website == page
    assert tool.ai_tool_annotation == "not_ai_tool"


def test_listicle_fixture_is_not_one_product(monkeypatch: pytest.MonkeyPatch) -> None:
    """Several product sites on an article stay not_ai_tool. One of them is not Website."""
    page = "https://magazine.example/blog/10-new-ai-tools"
    html = (FIXTURE_DIR / "listicle_names_many_products.html").read_text(encoding="utf-8")
    _patch_llm(
        monkeypatch,
        (
            '{"Title":"10 new AI tools","Website":"https://alpha.example/",'
            '"Source URL":"' + page + '","ai_tool_annotation":"ai_tool"}'
        ),
    )

    tool = asyncio.run(extract_tool_info_with_llm(html, page))

    assert tool.ai_tool_annotation == "not_ai_tool"
    assert tool.website == page
    assert "alpha.example" not in tool.website
    assert "beta.example" not in tool.website
    assert "gamma.example" not in tool.website


def test_asset_and_infrastructure_links_do_not_hide_the_product(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A font, an image, and a Cloudflare footer are not a second product."""
    page = "https://blog.example.com/posts/nova-launch"
    html = (
        "<article>"
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Inter">'
        '<img src="https://cdn.example/hero.png" alt="">'
        '<a href="https://nova.example/">Nova</a>'
        '<a href="https://www.cloudflare.com/">Protected</a>'
        "<p>Docs live at https://nova.example/docs.</p>"
        "</article>"
    )
    _patch_llm(
        monkeypatch,
        (
            '{"Title":"Nova","Website":"' + page + '",'
            '"Source URL":"' + page + '","ai_tool_annotation":"not_ai_tool"}'
        ),
    )

    tool = asyncio.run(extract_tool_info_with_llm(html, page))

    assert tool.website == "https://nova.example/"
    assert tool.ai_tool_annotation == "not_ai_tool"


def test_publisher_homepage_is_not_a_second_product() -> None:
    """The magazine's own homepage does not cancel the one tool the article names."""
    page = "https://magazine.example/blog/nova-launch"
    html = (
        "<article>"
        '<a href="https://magazine.example/">Magazine</a>'
        "<noscript><img src=\"https://pixel.example/t\"></noscript>"
        '<a href="https://nova.example/">Nova'
        "</article>"
    )
    tool = apply_article_website(
        ToolInfo(title="Nova", website=page, source=page, ai_tool_annotation="ai_tool"),
        html,
        page,
    )

    assert tool.website == "https://nova.example/"
    assert tool.ai_tool_annotation == "ai_tool"


def test_same_site_launch_post_uses_the_homepage() -> None:
    """A blog on the product's own site, with no other company linked, points at that site."""
    page = "https://nova.example/blog/we-launched"
    html = (
        "<article>"
        '<a href="https://nova.example/">Home</a>'
        '<a href="https://nova.example/pricing">Pricing</a>'
        "</article>"
    )
    tool = apply_article_website(
        ToolInfo(title="Nova", website=page, source=page, ai_tool_annotation="ai_tool"),
        html,
        page,
    )

    assert tool.website == "https://nova.example/"


def test_two_country_code_sites_are_not_one_product() -> None:
    """alpha.co.uk and beta.co.uk are different sites, not one domain named co.uk."""
    page = "https://magazine.example/blog/uk-tools"
    html = (
        "<article>"
        '<a href="https://alpha.co.uk/">Alpha</a>'
        '<a href="https://beta.co.uk/">Beta</a>'
        "</article>"
    )
    tool = apply_article_website(
        ToolInfo(title="UK tools", website="https://alpha.co.uk/", source=page, ai_tool_annotation="ai_tool"),
        html,
        page,
    )

    assert tool.website == page
    assert tool.ai_tool_annotation == "not_ai_tool"


def test_product_homepage_is_not_rewritten(monkeypatch: pytest.MonkeyPatch) -> None:
    """A product homepage is not an article, even when the page links elsewhere."""
    page = "https://nova.example/"
    html = (
        "<main><h1>Nova</h1>"
        '<a href="https://alpha.example/">Alpha</a>'
        '<a href="https://beta.example/pricing">Beta</a>'
        "</main>"
    )
    _patch_llm(
        monkeypatch,
        (
            '{"Title":"Nova","Website":"' + page + '",'
            '"Source URL":"' + page + '","ai_tool_annotation":"ai_tool"}'
        ),
    )

    tool = asyncio.run(extract_tool_info_with_llm(html, page))

    assert tool.website == page
    assert tool.ai_tool_annotation == "ai_tool"
