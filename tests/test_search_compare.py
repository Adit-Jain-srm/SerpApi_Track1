"""Planner, fake-client search, and candidate comparison."""
import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

import pytest

from agents.config_agent import Settings
from agents.search_agent import (
    SearchFailed,
    candidates_from_payload,
    compare_candidates,
    run_search,
)
from config.constants import BASE_QUERIES, HOMEPAGE_QUERIES
from main import main
from models.candidate import Candidate

NOW = datetime(2026, 10, 10, 18, 30, tzinfo=timezone.utc)
SHARED = "https://tools.example.com/nova"
BARE = "https://tools.example.com/bare"
DATED = "https://news.example.com/dated"
AGGREGATOR = "https://www.youtube.com/watch?v=abc"


class RecordingClient:
    """Fake SerpApi client. Records params and never reads an API key."""

    def __init__(self, handler) -> None:
        self.calls: list[dict[str, Any]] = []
        self._handler = handler

    def search(self, params: dict[str, Any]) -> dict[str, Any]:
        snapshot = dict(params)
        self.calls.append(snapshot)
        return self._handler(snapshot)


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "batch_size": 4,
        "llm_concurrency_limit": 2,
        "search_days": 7,
    }
    values.update(overrides)
    return Settings(**values)


def _empty(_params: dict[str, Any]) -> dict[str, Any]:
    return {"search_metadata": {"status": "Success"}}


def _mixed(params: dict[str, Any]) -> dict[str, Any]:
    if str(params.get("q", "")).startswith("open-source"):
        return {"search_metadata": {"status": "Success"}}
    if params.get("engine") == "google":
        return {
            "organic_results": [
                {
                    "link": f"{SHARED}?utm_source=google&utm_medium=organic",
                    "title": "Nova web",
                    "snippet": "Web snippet",
                    "published_at": "2020-01-01",
                },
                {"link": AGGREGATOR, "title": "A video", "snippet": "watch"},
                {"link": BARE},
            ]
        }
    return {
        "news_results": [
            {
                "link": f"{SHARED}?utm_source=news",
                "title": "Nova news",
                "snippet": "News snippet",
                "published_at": "2026-10-09",
                "source": "Example Wire",
            },
            {
                "link": DATED,
                "title": "Dated",
                "source": "Wire",
                "date": "2026-10-08",
            },
        ]
    }


@pytest.mark.parametrize(
    ("days", "tbs", "after_date"),
    [
        (7, "qdr:d7", "2026-10-03"),
        (1, "qdr:d1", "2026-10-09"),
    ],
)
def test_planner_date_window(days: int, tbs: str, after_date: str) -> None:
    assert os.environ.get("SERPAPI_API_KEY") is None
    assert os.environ.get("SERPAPI_KEY") is None
    assert len(BASE_QUERIES) == 4
    assert len(HOMEPAGE_QUERIES) == 2
    joined = " ".join(BASE_QUERIES).lower()
    assert "just launched" in joined
    assert "ai tool" in joined
    assert "now available" in joined
    assert "open-source" in joined
    assert "public beta" in joined
    homepage = " ".join(HOMEPAGE_QUERIES).lower()
    assert "pricing" in homepage
    assert "sign up" in homepage
    assert "introducing" in homepage
    assert all("after:" not in query and "site:" not in query for query in BASE_QUERIES)
    assert all("after:" not in query and "site:" not in query for query in HOMEPAGE_QUERIES)

    client = RecordingClient(_empty)
    candidates = asyncio.run(run_search(_settings(search_days=days), client=client, now=NOW))

    assert candidates == []
    web_calls = [call for call in client.calls if call.get("engine") == "google"]
    news_calls = [call for call in client.calls if call.get("engine") == "google_news"]
    assert len(web_calls) == 6
    assert len(news_calls) == 4
    assert [call.get("q") for call in web_calls] == [*BASE_QUERIES, *HOMEPAGE_QUERIES]
    assert all(
        not any(str(call.get("q", "")).startswith(query) for query in HOMEPAGE_QUERIES)
        for call in news_calls
    )
    assert {call.get("tbs") for call in web_calls} == {tbs}
    assert all("after:" not in call["q"] for call in web_calls)
    assert all("tbs" not in call for call in news_calls)
    assert all(f"after:{after_date}" in call["q"] for call in news_calls)
    assert all(call.get("hl") == "en" and call.get("gl") == "us" for call in client.calls)
    assert all("api_key" not in call and "output" not in call for call in client.calls)
    assert all("qdr:w" not in str(call.get("tbs", "")) for call in web_calls)
    if days == 1:
        assert all("qdr:d7" not in str(call.get("tbs", "")) for call in web_calls)
        assert all("qdr:w" not in str(call) for call in client.calls)
        assert all("after:2026-10-03" not in call["q"] for call in news_calls)


def test_runner_compares_fixtures_without_a_key() -> None:
    assert os.environ.get("SERPAPI_API_KEY") is None
    assert os.environ.get("SERPAPI_KEY") is None
    client = RecordingClient(_mixed)
    candidates = asyncio.run(run_search(_settings(), client=client, now=NOW))

    by_url = {candidate.url: candidate for candidate in candidates}
    assert set(by_url) == {SHARED, BARE, DATED}
    assert "utm_" not in "".join(by_url)
    assert all("youtube.com" not in candidate.url for candidate in candidates)

    nova = by_url[SHARED]
    assert nova.published_at == "2026-10-09"
    assert nova.engines == {"google", "google_news"}
    assert by_url[BARE].title == ""
    assert by_url[BARE].snippet == ""
    assert by_url[BARE].published_at == ""
    assert by_url[DATED].published_at == "2026-10-08"
    assert by_url[DATED].snippet == ""
    assert len(client.calls) == 10


def test_no_results_payload_is_empty() -> None:
    assert candidates_from_payload({"no_results": True}, "google") == []
    assert candidates_from_payload({"organic_results": []}, "google") == []
    assert candidates_from_payload({"organic_results": [{"title": "missing link"}]}, "google") == []
    assert candidates_from_payload({"news_results": [{"title": "no link"}]}, "google_news") == []


def test_compare_drops_userinfo_and_merges_host_case_and_default_port() -> None:
    """A password in the URL is not kept, and :443 does not split the same page."""
    records = [
        Candidate(
            url="https://User:pw@Tools.Example.com:443/Nova?utm=1",
            title="A",
            engines={"google"},
        ),
        Candidate(url="HTTPS://tools.example.com/Nova", title="B", engines={"google_news"}),
    ]
    merged = compare_candidates(records)
    assert len(merged) == 1
    assert merged[0].url == "https://tools.example.com/Nova"
    assert "pw" not in merged[0].url
    assert "User" not in merged[0].url
    assert merged[0].engines == {"google", "google_news"}


def test_compare_merges_news_date_and_caps() -> None:
    records = [
        Candidate(
            url=f"{SHARED}?utm_source=google",
            title="Web",
            snippet="w",
            published_at="2020-01-01",
            engines={"google"},
        ),
        Candidate(url=AGGREGATOR, title="Vid", engines={"google"}),
        Candidate(
            url=f"{SHARED}?utm_source=news",
            title="News",
            snippet="n",
            published_at="2026-10-09",
            engines={"google_news"},
        ),
        Candidate(url="https://other.example.com/b", title="B", engines={"google"}),
    ]

    merged = compare_candidates(records)
    assert [candidate.url for candidate in merged] == [SHARED, "https://other.example.com/b"]
    assert merged[0].published_at == "2026-10-09"
    assert merged[0].engines == {"google", "google_news"}

    capped = compare_candidates(records, max_urls=1)
    assert [candidate.url for candidate in capped] == [SHARED]
    assert capped[0].published_at == "2026-10-09"


def test_web_failure_keeps_news(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.ERROR)

    class WebDown:
        def search(self, params: dict[str, Any]) -> dict[str, Any]:
            if params.get("engine") == "google":
                raise RuntimeError("web down")
            return {
                "news_results": [
                    {
                        "link": "https://tools.example.com/only",
                        "title": "Only",
                        "snippet": "from news",
                        "published_at": "2026-10-09",
                    }
                ]
            }

    candidates = asyncio.run(run_search(_settings(), client=WebDown(), now=NOW))
    assert len(candidates) == 1
    assert candidates[0].url == "https://tools.example.com/only"
    assert candidates[0].engines == {"google_news"}
    assert any("SerpApiSearchError" in record.message for record in caplog.records)


def test_both_engines_fail(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    class Boom:
        def search(self, params: dict[str, Any]) -> dict[str, Any]:
            raise RuntimeError("down")

    with pytest.raises(SearchFailed) as caught:
        asyncio.run(run_search(_settings(), client=Boom(), now=NOW))
    assert caught.value.errors

    monkeypatch.setenv("SERPAPI_API_KEY", "test")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_KEY", "test")
    code = main(["--days", "7"], client=Boom())
    assert code == 1
    assert "Both web and news search failed" in capsys.readouterr().err

