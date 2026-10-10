"""
scraper_agent.py: Async HTML fetching and LLM-based tool info extraction using the configured Azure deployment.
- Uses ToolInfo dataclass from models.tool_info.
- All extraction, summarization, and classification is performed in a single LLM call per tool
  using prompts from prompts/ loaded via utils/prompt_loader.
- LLM input truncation limit is set in config/constants.py.
"""
import asyncio
import json
import logging
import re
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urljoin, urlparse

import aiohttp
from openai import AsyncAzureOpenAI

from agents.config_agent import AZURE_OPENAI_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT
from config.constants import LLM_INPUT_TRUNCATION_LIMIT, DEFAULT_HEADERS, NON_RETRYABLE_STATUS_CODES
from models.tool_info import ToolInfo
from utils.blacklist import PersistentBlacklist
from utils.error_handling import ScrapingError, ExtractionError
from utils.prompt_loader import load_prompt, is_allowed_by_robots

_html_fetch_cache: dict[str, str] = {}

blacklist = PersistentBlacklist()

_client: Optional[AsyncAzureOpenAI] = None
_deployment: str = ""

_system_prompt: Optional[str] = None
_user_prompt_template: Optional[str] = None


def _get_client() -> AsyncAzureOpenAI:
    """Lazy-initialize the Azure OpenAI client on first use."""
    global _client, _deployment
    if _client is None:
        if not AZURE_OPENAI_ENDPOINT:
            raise ValueError("AZURE_OPENAI_ENDPOINT is not set in environment variables.")
        _client = AsyncAzureOpenAI(
            api_key=AZURE_OPENAI_KEY,
            api_version="2025-01-01-preview",
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
        )
        _deployment = AZURE_OPENAI_DEPLOYMENT or "gpt-5.3-chat"
        if not AZURE_OPENAI_DEPLOYMENT:
            logging.warning("AZURE_OPENAI_DEPLOYMENT not set, defaulting to 'gpt-5.3-chat'")
    return _client


def _get_prompts() -> tuple[str, str]:
    """Load and cache prompt templates from disk (loaded once per process)."""
    global _system_prompt, _user_prompt_template
    if _system_prompt is None:
        _system_prompt = load_prompt("system_prompt.txt")
        _user_prompt_template = load_prompt("user_prompt.txt")
    return _system_prompt, _user_prompt_template


_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_MAX_REDIRECTS = 5


def _is_https(url: str) -> bool:
    return urlparse(url).scheme.lower() == "https"


async def fetch_with_retries(
    url: str, session: aiohttp.ClientSession, retries: int = 3, timeout: int = 30
) -> str:
    """Fetch HTML from a URL with retries and exponential backoff.

    Only https URLs are requested, and redirects that leave https are refused.
    Certificate verification stays on (`ssl=True`). Skips blacklisted domains
    and non-retryable status codes.
    """
    parsed = urlparse(url)
    if not _is_https(url):
        _html_fetch_cache[url] = ""
        raise ScrapingError(
            f"Refusing non-TLS fetch for {url}",
            context={"url": url, "step": "fetch_with_retries", "reason": "tls"},
        )

    domain = (parsed.hostname or "").lower().rstrip(".") or parsed.netloc.lower()

    if blacklist.is_blacklisted(domain):
        logging.warning(f"Domain {domain} is blacklisted. Skipping fetch for {url}.")
        _html_fetch_cache[url] = ""
        return ""

    delay = 2
    for attempt in range(retries):
        try:
            allowed = await is_allowed_by_robots(url)
            if not allowed:
                logging.warning(f"robots.txt disallows scraping {url}. Skipping fetch.")
                _html_fetch_cache[url] = ""
                return ""

            current = url
            status = 0
            html = ""
            for _hop in range(_MAX_REDIRECTS + 1):
                async with session.get(
                    current,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    ssl=True,
                    headers=DEFAULT_HEADERS,
                    allow_redirects=False,
                ) as resp:
                    if resp.status in _REDIRECT_STATUSES:
                        nxt = urljoin(current, resp.headers.get("Location") or "")
                        if not _is_https(nxt):
                            _html_fetch_cache[url] = ""
                            raise ScrapingError(
                                f"Refusing non-TLS redirect for {url}",
                                context={"url": url, "step": "fetch_with_retries", "reason": "tls"},
                            )
                        current = nxt
                        continue
                    status = resp.status
                    if resp.status == 200:
                        html = await resp.text(encoding=resp.charset or "utf-8", errors="replace")
                    break
            else:
                _html_fetch_cache[url] = ""
                raise ScrapingError(
                    f"Too many redirects for {url}",
                    context={"url": url, "step": "fetch_with_retries", "reason": "redirects"},
                )

            if status == 200:
                _html_fetch_cache[url] = html or ""
                return _html_fetch_cache[url]

            if status in NON_RETRYABLE_STATUS_CODES:
                _html_fetch_cache[url] = ""
                blacklist.record_failure(domain)
                raise ScrapingError(
                    f"HTTP {status} for {url}",
                    context={"url": url, "step": "fetch_with_retries", "status": status},
                )

            if attempt < retries - 1:
                logging.warning(f"HTTP {status} for {url}, retrying after {delay}s...")
                await asyncio.sleep(delay)
                delay *= 2
                continue

            _html_fetch_cache[url] = ""
            blacklist.record_failure(domain)
            raise ScrapingError(
                f"HTTP {status} for {url}",
                context={"url": url, "step": "fetch_with_retries", "status": status},
            )

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt < retries - 1:
                logging.warning(f"Connection error for {url}: {e}, retrying after {delay}s...")
                await asyncio.sleep(delay)
                delay *= 2
                continue
            _html_fetch_cache[url] = ""
            blacklist.record_failure(domain)
            raise ScrapingError(
                f"Connection error for {url}: {e}",
                context={"url": url, "step": "fetch_with_retries", "error": str(e)},
            )
        except ScrapingError:
            raise
        except Exception as e:
            _html_fetch_cache[url] = ""
            blacklist.record_failure(domain)
            raise ScrapingError(
                f"Unexpected error for {url}: {e}",
                context={"url": url, "step": "fetch_with_retries", "error": str(e)},
            )

    return ""


def _parse_llm_json(raw: str | None) -> dict | None:
    """Extract and parse JSON from an LLM response that may contain markdown fences."""
    if not raw:
        return None

    content = raw.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()

    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    return None


def _as_text(value: object, default: str = "") -> str:
    """Return a stripped string. Nulls and non-strings use the default."""
    if isinstance(value, str):
        return value.strip() or default
    return default


_ARTICLE_PATH_MARKERS = (
    "/blog/",
    "/blogs/",
    "/news/",
    "/article/",
    "/articles/",
    "/posts/",
    "/post/",
    "/stories/",
    "/story/",
)
_UTILITY_SEGMENTS = frozenset({
    "privacy",
    "privacy-policy",
    "terms",
    "terms-of-service",
    "legal",
    "cookie",
    "cookies",
    "careers",
    "jobs",
    "login",
    "log-in",
    "signin",
    "sign-in",
    "contact",
    "sitemap",
    "share",
})
_URL_RE = re.compile(r"https://[^\s\"'<>]+", re.IGNORECASE)
_TRAILING_URL_PUNCT = ".,);]}>\"'"


def _page_host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    if host.startswith("www."):
        return host[4:]
    return host


def page_is_article(url: str) -> bool:
    """True for blog and news URLs. A product homepage is not an article."""
    host = _page_host(url)
    if host.startswith("blog.") or host.startswith("news."):
        return True
    path = (urlparse(url).path or "").lower()
    padded = f"/{path.strip('/')}/" if path.strip("/") else "/"
    if any(marker in padded for marker in _ARTICLE_PATH_MARKERS):
        return True
    return re.search(r"/20\d{2}/\d{2}/", path) is not None


def _is_utility_path(url: str) -> bool:
    segments = [segment for segment in urlparse(url).path.lower().split("/") if segment]
    return any(segment in _UTILITY_SEGMENTS for segment in segments)


def _same_page(left: str, right: str) -> bool:
    from agents.search_agent import normalize_url

    def key(url: str) -> str:
        parsed = urlparse(normalize_url(url))
        path = parsed.path.rstrip("/") or "/"
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    try:
        return key(left) == key(right)
    except Exception:
        return left == right


class _AnchorCollector(HTMLParser):
    """Collect anchor hrefs. Malformed markup stops collection."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self._href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a" or self._href is not None:
            return
        for key, value in attrs:
            if key.lower() == "href" and value and value.strip():
                self._href = value.strip()
                return

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.links.append(self._href)
            self._href = None


def _visible_html(html: str) -> str:
    return re.sub(
        r"<(script|style)\b[^>]*>.*?</\1>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )


def _absolute_https(page_url: str, raw: str) -> str | None:
    candidate = raw.strip().rstrip(_TRAILING_URL_PUNCT)
    if not candidate or candidate.startswith(("#", "mailto:", "javascript:", "tel:")):
        return None
    absolute = urljoin(page_url, candidate)
    parsed = urlparse(absolute)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return None
    return absolute


def _product_urls_by_domain(html: str, page_url: str) -> dict[str, list[str]]:
    """Official product URLs named on the page, grouped by registrable domain.

    Aggregators, utility paths, and other articles are not product URLs.
    Several product domains means a roundup, so the caller must not pick one.
    """
    from agents.search_agent import is_aggregator, normalize_url

    visible = _visible_html(html or "")
    raw_links: list[str] = []
    collector = _AnchorCollector()
    try:
        collector.feed(visible)
        collector.close()
        raw_links.extend(collector.links)
    except Exception as exc:
        logging.warning(f"Failed to parse links for {page_url}: {exc}")

    raw_links.extend(_URL_RE.findall(visible))

    grouped: dict[str, list[str]] = {}
    seen: set[str] = set()
    for raw in raw_links:
        absolute = _absolute_https(page_url, raw)
        if absolute is None or _same_page(absolute, page_url):
            continue
        if is_aggregator(absolute) or page_is_article(absolute) or _is_utility_path(absolute):
            continue
        try:
            normalized = normalize_url(absolute)
        except Exception:
            continue
        if not normalized or normalized in seen or _same_page(normalized, page_url):
            continue
        seen.add(normalized)
        host = _page_host(normalized)
        labels = [label for label in host.split(".") if label]
        domain = ".".join(labels[-2:]) if len(labels) >= 2 else host
        if not domain:
            continue
        grouped.setdefault(domain, []).append(normalized)
    return grouped


def _best_product_url(urls: list[str]) -> str:
    def rank(url: str) -> tuple[int, int, str]:
        segments = [segment for segment in urlparse(url).path.split("/") if segment]
        return (len(segments), len(url), url)

    return min(urls, key=rank)


def apply_article_website(tool: ToolInfo, html: str, page_url: str) -> ToolInfo:
    """Prefer one official product URL over a blog or news URL.

    A homepage is unchanged. An article that names one product domain uses that
    URL as website. An article that names none, or several product domains, stays
    not_ai_tool so a roundup cannot become a single tool.
    """
    if not page_is_article(page_url):
        return tool

    grouped = _product_urls_by_domain(html, page_url)
    if len(grouped) == 1:
        urls = next(iter(grouped.values()))
        tool.website = _best_product_url(urls)
        return tool

    tool.ai_tool_annotation = "not_ai_tool"
    tool.website = page_url
    return tool


def _as_str_list(value: object) -> list[str]:
    """Return feature or tag strings. A lone string is one item. Nulls are dropped."""
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        if isinstance(item, str):
            text = item.strip()
            if text:
                items.append(text)
    return items


async def extract_tool_info_with_llm(html: str, url: str) -> ToolInfo:
    """
    Use the configured Azure deployment to extract all relevant tool info fields from raw HTML and URL in a single call.
    Returns a ToolInfo with ai_tool_annotation set to 'ai_tool' or 'not_ai_tool'.
    """
    client = _get_client()
    system_prompt, user_prompt_template = _get_prompts()

    html_trunc = html[:LLM_INPUT_TRUNCATION_LIMIT] if html else ""
    if html and len(html) > LLM_INPUT_TRUNCATION_LIMIT:
        logging.warning(f"HTML for {url} truncated to {LLM_INPUT_TRUNCATION_LIMIT} chars for LLM prompt.")

    user_prompt = user_prompt_template.format(url=url, html_trunc=html_trunc)

    try:
        response = await client.chat.completions.create(
            model=_deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            # gpt-4o-class and newer Azure chat deployments reject max_tokens.
            # Some of those deployments also accept only the default temperature.
            max_completion_tokens=800,
            temperature=1,
        )

        data = _parse_llm_json(response.choices[0].message.content)
        if data:
            website = _as_text(data.get("Website"), url)
            source = _as_text(data.get("Source URL"), url)
            title = _as_text(data.get("Title"))
            annotation = _as_text(data.get("ai_tool_annotation"), "not_ai_tool")
            logging.info(
                f"LLM result: Title='{title}', "
                f"Website='{website}', ai_tool_annotation='{annotation}'"
            )
            return apply_article_website(
                ToolInfo(
                    title=title,
                    website=website,
                    summary=_as_text(data.get("Core Functionality")) or _as_text(data.get("Summary")) or None,
                    features=_as_str_list(data.get("Key Features")),
                    pricing=_as_text(data.get("Pricing")) or None,
                    source=source,
                    target_audience=_as_text(data.get("Target Audience")) or None,
                    main_text=html_trunc,
                    ai_tool_annotation=annotation,
                    tags=_as_str_list(data.get("Tags")),
                    publish_date=_as_text(data.get("Publish Date")) or None,
                ),
                html,
                url,
            )

        logging.warning(f"LLM extraction returned non-JSON for {url}")

    except ExtractionError:
        raise
    except Exception as e:
        logging.error(f"LLM extraction failed for {url}: {e!r}", exc_info=True)
        raise ExtractionError(
            f"LLM extraction failed for {url}: {e}",
            context={"url": url, "step": "extract_tool_info_with_llm", "error": str(e)},
        )

    return apply_article_website(
        ToolInfo(
            title="",
            website=url,
            summary="",
            features=[],
            source=url,
            main_text=html_trunc,
            ai_tool_annotation="not_ai_tool",
            tags=[],
        ),
        html,
        url,
    )
