"""
search_agent.py: Plans a date window, searches SerpApi web and news, and compares candidates.
"""
import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from urllib.parse import urlparse, urlunparse

from serpapi_search_tools import SearchResultFormat, SerpApiSearchError, news_search, web_search

from agents.config_agent import Settings
from agents.page_kind import page_is_article, page_is_directory
from config.constants import (
    AGGREGATOR_DOMAINS,
    BASE_QUERIES,
    HOMEPAGE_QUERIES,
    github_url_is_blocked,
)
from models.candidate import Candidate

WEB_ENGINE = "google"
NEWS_ENGINE = "google_news"

# List titles. A count below 3, a version like GPT-4, and a list quoted only in
# the snippet are not matches: those still get fetched and the model can reject them.
_LIST_COUNT = re.compile(
    r"(?<![-.\w])([0-9]{1,4})\s+(?:new\s+|best\s+|ai\s+)*(?:tools|apps|agents)\b",
    re.IGNORECASE,
)
_TOP_COUNT = re.compile(r"\btop\s+([0-9]{1,4})\b", re.IGNORECASE)
_LIST_PHRASE = re.compile(r"\b(?:roundup|best ai tools)\b", re.IGNORECASE)
_MIN_LIST_COUNT = 3
_PRODUCT_HINTS = (
    "pricing",
    "sign up",
    "signup",
    "get started",
    "launched",
    "introducing",
    "public beta",
)


class SearchClient(Protocol):
    """Sync SerpApi client. A custom client skips the network and does not read a key."""

    def search(self, params: dict[str, Any]) -> Any: ...


class SearchFailed(Exception):
    """Raised when web and news both fail. An empty result set is not a failure."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = list(errors)
        detail = "; ".join(self.errors) if self.errors else "unknown error"
        super().__init__(f"Both web and news search failed: {detail}")


def _hostname(url: str) -> str:
    """Return the lowercased host, without a port, userinfo, or trailing dot."""
    return (urlparse(url).hostname or "").lower().rstrip(".")


def normalize_url(url: str) -> str:
    """Normalize URL by removing query parameters and fragments for deduplication.

    The host is lowercased and userinfo is dropped so a password in the URL is
    not kept on the candidate. Default ports 80 and 443 are dropped so the same
    page merges across those spellings.
    """
    try:
        parsed = urlparse(url.strip())
        scheme = (parsed.scheme or "").lower()
        host = _hostname(url)
        if not scheme or not host:
            return url
        netloc = host
        try:
            port = parsed.port
        except ValueError:
            port = None
        if port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
            netloc = f"{host}:{port}"
        return urlunparse((scheme, netloc, parsed.path or "", "", "", ""))
    except Exception as e:
        logging.warning(f"Failed to normalize URL {url}: {e}")
        return url


def is_aggregator(url: str) -> bool:
    """Check if a URL belongs to an aggregator, news, or social media domain.

    The host is the URL hostname, so a port or userinfo cannot bypass the list.
    A single-label suffix such as '.edu' matches mit.edu and does not match the
    bare host edu. A multi-label suffix such as '.gov.uk' also matches the apex
    host gov.uk. github.com repository roots are kept; other github.com paths
    are blocked by github_url_is_blocked.
    """
    try:
        if github_url_is_blocked(url):
            return True
        domain = _hostname(url)
        if not domain:
            return True
        for agg in AGGREGATOR_DOMAINS:
            if agg.startswith("."):
                suffix = agg[1:]
                if not suffix:
                    continue
                if "." in suffix:
                    if domain == suffix or domain.endswith("." + suffix):
                        return True
                elif domain.endswith("." + suffix):
                    return True
            elif domain == agg or domain.endswith("." + agg):
                return True
        return False
    except Exception as e:
        logging.warning(f"Failed to check if URL {url} is aggregator: {e}")
        return True


def news_cutoff(days: int, now: datetime | None = None) -> str:
    """UTC calendar date `days` before `now`, used as the Google News `after:` filter."""
    if days < 1:
        raise ValueError("days must be at least 1")
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    else:
        moment = moment.astimezone(timezone.utc)
    return (moment - timedelta(days=days)).date().isoformat()


def _as_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _published_at(item: dict[str, Any]) -> str:
    """Read a result date. Google News puts the article time in `date`."""
    published = _as_text(item.get("published_at"))
    if published:
        return published
    return _as_text(item.get("date"))


def candidates_from_payload(payload: dict[str, Any], engine: str) -> list[Candidate]:
    """Turn one JSON search payload into candidates. `no_results` is an empty list."""
    if payload.get("no_results") is True:
        return []

    key = "news_results" if engine == NEWS_ENGINE else "organic_results"
    raw_items = payload.get(key) or []
    if not isinstance(raw_items, list):
        return []

    records: list[Candidate] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        link = _as_text(item.get("link"))
        if not link:
            continue
        records.append(
            Candidate(
                url=link,
                title=_as_text(item.get("title")),
                snippet=_as_text(item.get("snippet")),
                published_at=_published_at(item),
                engines={engine},
            )
        )
    return records


def is_roundup_text(title: str, snippet: str = "") -> bool:
    """True when the title is a list of tools, not one product.

    A list that appears only in the snippet stays. Google often quotes one
    under a product name. When the title is empty, the snippet is the only
    label, so it is checked instead. A count below 3, and a version such as
    GPT-4, stay.
    """
    text = title.strip() or snippet
    if _LIST_PHRASE.search(text):
        return True
    for pattern in (_LIST_COUNT, _TOP_COUNT):
        for match in pattern.finditer(text):
            if int(match.group(1)) >= _MIN_LIST_COUNT:
                return True
    return False


def candidate_score(candidate: Candidate) -> int:
    """Prefer a product-shaped page over an article, before any fetch.

    Every homepage scores above every article, so `--max-urls` cannot fill
    itself with posts. Words like pricing or launched, two engines agreeing,
    and a date only order pages of the same kind.
    """
    text = f"{candidate.title} {candidate.snippet}".lower()
    hints = sum(1 for hint in _PRODUCT_HINTS if hint in text)
    extras = hints + (1 if len(candidate.engines) > 1 else 0) + (1 if candidate.published_at else 0)
    # Larger than every hint, plus both engines, plus a date.
    if page_is_article(candidate.url):
        return extras
    return extras + len(_PRODUCT_HINTS) + 3


def compare_candidates(records: list[Candidate], max_urls: int | None = None) -> list[Candidate]:
    """Drop aggregators and roundups, then rank what is left.

    When web and news disagree about the date, the news date is kept.
    `--max-urls` applies after that rank, so the cap keeps product-shaped
    pages rather than whichever row arrived first.
    """
    if max_urls is not None and max_urls < 1:
        raise ValueError("max_urls must be a positive integer")

    merged: dict[str, Candidate] = {}
    order: list[str] = []
    for record in records:
        if not record.url or is_aggregator(record.url):
            continue
        url = normalize_url(record.url)
        if not url or is_aggregator(url):
            continue

        current = merged.get(url)
        if current is None:
            merged[url] = Candidate(
                url=url,
                title=record.title,
                snippet=record.snippet,
                published_at=record.published_at,
                engines=set(record.engines),
            )
            order.append(url)
            continue

        from_news = NEWS_ENGINE in record.engines
        current.engines.update(record.engines)
        if from_news and record.published_at:
            current.published_at = record.published_at
        elif not current.published_at and record.published_at:
            current.published_at = record.published_at
        if not current.title and record.title:
            current.title = record.title
        if not current.snippet and record.snippet:
            current.snippet = record.snippet

    ranked: list[tuple[int, Candidate]] = []
    for index, url in enumerate(order):
        candidate = merged[url]
        if page_is_directory(candidate.url):
            logging.info("Skipping directory before fetch: %s", candidate.url)
            continue
        if is_roundup_text(candidate.title, candidate.snippet):
            logging.info("Skipping roundup before fetch: %s", candidate.title or url)
            continue
        ranked.append((index, candidate))
    ranked.sort(key=lambda item: (-candidate_score(item[1]), item[0]))
    chosen = [candidate for _, candidate in ranked]
    if max_urls is not None:
        return chosen[:max_urls]
    return chosen


def format_comparison_table(candidates: list[Candidate]) -> str:
    """Render the dry-run comparison as a plain-text table."""
    lines = ["URL | Title | Published | Engines | Snippet"]
    if not candidates:
        lines.append("No candidates.")
        return "\n".join(lines)

    for candidate in candidates:
        engines = ", ".join(sorted(candidate.engines))
        cells = [
            " ".join(candidate.url.split()),
            " ".join(candidate.title.split()),
            " ".join(candidate.published_at.split()),
            engines,
            " ".join(candidate.snippet.split()),
        ]
        lines.append(" | ".join(cells))
    lines.append(f"Candidates: {len(candidates)}")
    return "\n".join(lines)


def _build_tools(days: int, client: SearchClient | None):
    """Build the web and news callables for one date window.

    Web is pinned to Google so `tbs` is valid. News does not receive `tbs`.
    """
    locale = {"hl": "en", "gl": "us"}
    shared = {
        "provider": "function",
        "response_format": SearchResultFormat.JSON,
        "client": client,
    }
    web = web_search(
        allowed_engines=[WEB_ENGINE],
        default_engine=WEB_ENGINE,
        default_params={**locale, "tbs": f"qdr:d{days}"},
        **shared,
    )
    news = news_search(default_params=dict(locale), **shared)
    return web, news


async def _run_tool(
    tool: Any, queries: list[str], engine: str
) -> tuple[list[dict[str, Any]], list[str], bool]:
    """Call one engine for every query. One failure does not cancel the rest."""
    payloads: list[dict[str, Any]] = []
    errors: list[str] = []
    for query in queries:
        try:
            raw = await asyncio.to_thread(tool, query=query)
        except SerpApiSearchError as exc:
            message = f"SerpApiSearchError for {engine} query {query!r}: {exc}"
            logging.error(message)
            errors.append(message)
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            message = f"Invalid JSON for {engine} query {query!r}: {exc}"
            logging.error(message)
            errors.append(message)
            continue
        if not isinstance(payload, dict):
            message = f"Invalid JSON for {engine} query {query!r}: expected an object"
            logging.error(message)
            errors.append(message)
            continue
        payloads.append(payload)
    return payloads, errors, bool(payloads)


async def run_search(
    settings: Settings,
    client: SearchClient | None = None,
    now: datetime | None = None,
) -> list[Candidate]:
    """Search web and news, then compare the hits.

    `client` is injected by tests. A custom client skips the network and does not
    read an API key. `now` fixes the UTC clock for the news `after:` date.
    """
    days = settings.search_days
    if days < 1:
        raise ValueError("days must be at least 1")

    cutoff = news_cutoff(days, now)
    # Homepage queries stay on web. News would turn them back into articles.
    web_queries = [*BASE_QUERIES, *HOMEPAGE_QUERIES]
    news_queries = [f"{query} after:{cutoff}" for query in BASE_QUERIES]
    logging.info(
        f"Searching {len(web_queries)} web and {len(news_queries)} news queries over {days} days "
        f"(web tbs=qdr:d{days}, news after:{cutoff})"
    )

    web_tool, news_tool = _build_tools(days, client)
    (web_payloads, web_errors, web_ok), (news_payloads, news_errors, news_ok) = await asyncio.gather(
        _run_tool(web_tool, web_queries, WEB_ENGINE),
        _run_tool(news_tool, news_queries, NEWS_ENGINE),
    )

    if not web_ok and news_ok:
        logging.error("Web search failed; continuing with news results.")
    elif not news_ok and web_ok:
        logging.error("News search failed; continuing with web results.")
    elif not web_ok and not news_ok:
        raise SearchFailed(web_errors + news_errors)

    records: list[Candidate] = []
    for payload in web_payloads:
        records.extend(candidates_from_payload(payload, WEB_ENGINE))
    for payload in news_payloads:
        records.extend(candidates_from_payload(payload, NEWS_ENGINE))

    candidates = compare_candidates(records, max_urls=settings.max_urls)
    logging.info(f"Compared search results to {len(candidates)} candidates")
    return candidates
