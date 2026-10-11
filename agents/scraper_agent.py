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
from openai import AsyncAzureOpenAI, RateLimitError

from agents.config_agent import AZURE_OPENAI_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT
from agents.page_kind import page_is_article, page_is_directory
from config.constants import (
    DEFAULT_HEADERS,
    LLM_INPUT_TRUNCATION_LIMIT,
    NON_PRODUCT_DOMAINS,
    NON_RETRYABLE_STATUS_CODES,
)
from models.tool_info import ToolInfo
from utils.blacklist import PersistentBlacklist
from utils.error_handling import ScrapingError, ExtractionError
from utils.prompt_loader import load_prompt, is_allowed_by_robots
from utils.url_safety import UnsafeURL, validate_url_async

_MAX_CACHE_SIZE = 1000
_html_fetch_cache: dict[str, str] = {}


def _cache_set(url: str, html: str) -> None:
    """Store in bounded fetch cache, evicting oldest if full."""
    if len(_html_fetch_cache) >= _MAX_CACHE_SIZE:
        first_key = next(iter(_html_fetch_cache), None)
        if first_key is not None:
            _html_fetch_cache.pop(first_key, None)
    _html_fetch_cache[url] = html

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
    if url in _html_fetch_cache and _html_fetch_cache[url]:
        return _html_fetch_cache[url]

    if not _is_https(url):
        _cache_set(url, "")
        raise ScrapingError(
            f"Refusing non-TLS fetch for {url}",
            context={"url": url, "step": "fetch_with_retries", "reason": "tls"},
        )
    try:
        await validate_url_async(url)
    except UnsafeURL as exc:
        _cache_set(url, "")
        raise ScrapingError(
            f"Refusing unsafe fetch for {url}",
            context={"url": url, "step": "fetch_with_retries", "reason": str(exc)},
        ) from exc

    parsed = urlparse(url)

    domain = (parsed.hostname or "").lower().rstrip(".") or parsed.netloc.lower()

    if blacklist.is_blacklisted(domain):
        logging.warning("Domain %s is blacklisted. Skipping fetch for %s.", domain, url)
        _cache_set(url, "")
        return ""

    delay = 2
    for attempt in range(retries):
        try:
            try:
                allowed = await is_allowed_by_robots(url, session=session)
            except TypeError:
                allowed = await is_allowed_by_robots(url)
            if not allowed:
                logging.warning("robots.txt disallows scraping %s. Skipping fetch.", url)
                _cache_set(url, "")
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
                        try:
                            await validate_url_async(nxt)
                        except UnsafeURL as exc:
                            _cache_set(url, "")
                            raise ScrapingError(
                                f"Refusing unsafe redirect for {url}",
                                context={
                                    "url": url,
                                    "step": "fetch_with_retries",
                                    "reason": str(exc),
                                },
                            ) from exc
                        current = nxt
                        continue
                    status = resp.status
                    if resp.status == 200:
                        content = getattr(resp, "content", None)
                        if content is not None and hasattr(content, "iter_chunked"):
                            chunks: list[bytes] = []
                            size = 0
                            async for chunk in content.iter_chunked(64 * 1024):
                                size += len(chunk)
                                if size > 500_000:
                                    raise ScrapingError(
                                        f"Response exceeded 500000 bytes for {url}",
                                        context={"url": url, "step": "fetch_with_retries", "reason": "size"},
                                    )
                                chunks.append(chunk)
                            html = b"".join(chunks).decode(resp.charset or "utf-8", errors="replace")
                        else:
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
    """Collect anchor hrefs, including anchors that HTML truncation left unclosed."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value and value.strip():
                self.links.append(value.strip())
                return


def _visible_html(html: str) -> str:
    return re.sub(
        r"<(script|style|noscript)\b[^>]*>.*?</\1>",
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


# Last two labels are the suffix, not the site. alpha.co.uk and beta.co.uk stay distinct.
_MULTI_LABEL_SUFFIXES = frozenset({
    "co.uk",
    "org.uk",
    "ac.uk",
    "gov.uk",
    "com.au",
    "net.au",
    "org.au",
    "co.in",
    "co.jp",
    "co.nz",
    "co.za",
    "com.br",
    "com.sg",
})


def _registrable_domain(host: str) -> str:
    labels = [label for label in host.split(".") if label]
    if len(labels) >= 3 and ".".join(labels[-2:]) in _MULTI_LABEL_SUFFIXES:
        return ".".join(labels[-3:])
    if len(labels) >= 2:
        return ".".join(labels[-2:])
    return host


def _is_non_product_host(host: str) -> bool:
    """True for CDNs, font hosts, and consent widgets. Never the shipped product."""
    domain = _registrable_domain(host)
    return domain in NON_PRODUCT_DOMAINS or host in NON_PRODUCT_DOMAINS


def _named_links(html: str) -> list[str]:
    """Anchor targets, plus URLs written in the text. Tag attributes are not URLs.

    A font stylesheet or an image CDN is not a second product. A URL typed in a
    paragraph is.
    """
    visible = _visible_html(html or "")
    anchors: list[str] = []
    collector = _AnchorCollector()
    try:
        collector.feed(visible)
        collector.close()
        anchors.extend(collector.links)
    except Exception as exc:
        logging.warning(f"Failed to parse links: {exc}")
    text = re.sub(r"<[^>]+>", " ", visible)
    return anchors + _URL_RE.findall(text)


def _product_urls_by_domain(html: str, page_url: str) -> dict[str, list[str]]:
    """Official product URLs named on the page, grouped by registrable domain.

    Aggregators, utility paths, articles, and infrastructure hosts are not
    product URLs. Several product domains means a roundup, so the caller must
    not pick one.
    """
    from agents.search_agent import is_aggregator, normalize_url

    raw_links = _named_links(html)

    grouped: dict[str, list[str]] = {}
    seen: set[str] = set()
    for raw in raw_links:
        absolute = _absolute_https(page_url, raw)
        if absolute is None or _same_page(absolute, page_url):
            continue
        if is_aggregator(absolute) or page_is_article(absolute) or page_is_directory(absolute) or _is_utility_path(absolute):
            continue
        try:
            normalized = normalize_url(absolute)
        except Exception:
            continue
        if not normalized or normalized in seen or _same_page(normalized, page_url):
            continue
        seen.add(normalized)
        host = _page_host(normalized)
        if _is_non_product_host(host):
            continue
        domain = _registrable_domain(host)
        if not domain:
            continue
        grouped.setdefault(domain, []).append(normalized)
    return grouped


def _chosen_product_urls(grouped: dict[str, list[str]], page_url: str) -> list[str] | None:
    """The product URLs an article named, or None when it named several.

    The publisher's own domain is not a second product: a magazine homepage
    next to one tool link is still that tool. When nothing off-site is named,
    the publisher's own links are the homepage of a same-site launch post.
    """
    page_domain = _registrable_domain(_page_host(page_url))
    foreign = [urls for domain, urls in grouped.items() if domain != page_domain]
    if len(foreign) == 1:
        return foreign[0]
    if len(foreign) > 1:
        return None
    own = grouped.get(page_domain)
    if own:
        return own
    return None


def _best_product_url(urls: list[str]) -> str:
    def rank(url: str) -> tuple[int, int, str]:
        segments = [segment for segment in urlparse(url).path.split("/") if segment]
        return (len(segments), len(url), url)

    return min(urls, key=rank)


def product_leads(tools: list[ToolInfo], already_fetched: set[str]) -> list[str]:
    """Product homepages named by a fetched page, skipping pages already fetched.

    An article that names one product domain is a lead even when the article
    itself is not_ai_tool. Listicles do not produce a lead, because they do not
    leave a single product website. The list is capped.
    """
    from agents.search_agent import is_aggregator, normalize_url

    from config.constants import FOLLOW_HOP_LIMIT

    seen = {normalize_url(url) for url in already_fetched if url}
    leads: list[str] = []
    for tool in tools:
        site = (tool.website or "").strip()
        source = (tool.source or "").strip()
        if not site or not source or _same_page(site, source):
            continue
        if page_is_article(site) or is_aggregator(site):
            continue
        try:
            url = normalize_url(site)
        except Exception:
            continue
        if not url.startswith("https://") or url in seen:
            continue
        seen.add(url)
        leads.append(url)
        if len(leads) >= FOLLOW_HOP_LIMIT:
            break
    return leads


def apply_article_website(tool: ToolInfo, html: str, page_url: str) -> ToolInfo:
    """Prefer one official product URL over a blog or news URL.

    A homepage is unchanged. An article that names one other product domain uses
    that URL as website. The publisher's own domain does not count as another
    product. An article that names none, or several other product domains, stays
    not_ai_tool so a roundup cannot become a single tool.
    """
    if not page_is_article(page_url):
        return tool

    chosen = _chosen_product_urls(_product_urls_by_domain(html, page_url), page_url)
    if chosen:
        tool.website = _best_product_url(chosen)
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

    except RateLimitError:
        raise
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
