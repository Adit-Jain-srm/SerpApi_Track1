"""
scraper_agent.py: Async HTML fetching and LLM-based tool info extraction using GPT-4o (Azure OpenAI).
- Uses ToolInfo dataclass from models.tool_info.
- All extraction, summarization, and classification is performed in a single LLM call per tool
  using prompts from prompts/ loaded via utils/prompt_loader.
- LLM input truncation limit is set in config/constants.py.
"""
import asyncio
import json
import logging
import re
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
        _deployment = AZURE_OPENAI_DEPLOYMENT or "gpt-4o"
        if not AZURE_OPENAI_DEPLOYMENT:
            logging.warning("AZURE_OPENAI_DEPLOYMENT not set, defaulting to 'gpt-4o'")
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
    Use GPT-4o to extract all relevant tool info fields from raw HTML and URL in a single call.
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
            return ToolInfo(
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

    return ToolInfo(
        title="",
        website=url,
        summary="",
        features=[],
        source=url,
        main_text=html_trunc,
        ai_tool_annotation="not_ai_tool",
        tags=[],
    )
