"""Article pages become homepage fetches. No network."""

from agents.pipeline_agent import _select_tools
from agents.scraper_agent import product_leads
from models.tool_info import ToolInfo


def _tool(
    title: str,
    website: str,
    source: str,
    annotation: str,
) -> ToolInfo:
    return ToolInfo(
        title=title,
        website=website,
        source=source,
        ai_tool_annotation=annotation,
    )


def test_article_with_one_product_url_is_a_lead() -> None:
    article = _tool(
        "SynthID Detector",
        "https://deepmind.google/models/synthid/",
        "https://blog.google/innovation-and-ai/models-and-research/google-deepmind/synth-id-ai-content/",
        "not_ai_tool",
    )
    homepage = _tool(
        "Already fetched",
        "https://nova.example/",
        "https://nova.example/",
        "ai_tool",
    )

    leads = product_leads([article, homepage], {"https://nova.example/"})

    assert leads == ["https://deepmind.google/models/synthid/"]


def test_listicle_and_same_page_are_not_leads() -> None:
    same = _tool(
        "Note",
        "https://blog.example.com/posts/note",
        "https://blog.example.com/posts/note",
        "not_ai_tool",
    )
    aggregator = _tool(
        "Roundup",
        "https://www.techcrunch.com/2026/10/01/widget",
        "https://news.example/story",
        "not_ai_tool",
    )

    assert product_leads([same, aggregator], set()) == []


def test_homepage_replaces_the_article_that_named_it() -> None:
    article = _tool(
        "SynthID Detector",
        "https://deepmind.google/models/synthid/",
        "https://blog.google/innovation-and-ai/synth-id/",
        "ai_tool",
    )
    homepage = _tool(
        "SynthID Detector",
        "https://deepmind.google/models/synthid/",
        "https://deepmind.google/models/synthid/",
        "ai_tool",
    )
    direct = _tool(
        "Nova",
        "https://nova.example/",
        "https://nova.example/",
        "ai_tool",
    )

    kept = _select_tools([article, direct], [homepage])
    titles = [tool.title for tool in kept]

    assert titles == ["SynthID Detector", "Nova"]
    assert kept[0].source == "https://deepmind.google/models/synthid/"


def test_article_stays_when_its_homepage_does_not_extract() -> None:
    article = _tool(
        "SynthID Detector",
        "https://deepmind.google/models/synthid/",
        "https://blog.google/innovation-and-ai/synth-id/",
        "ai_tool",
    )

    kept = _select_tools([article], [])

    assert [tool.title for tool in kept] == ["SynthID Detector"]
    assert kept[0].source.startswith("https://blog.google/")
