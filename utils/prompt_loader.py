from __future__ import annotations

import logging
import os
from urllib.parse import urlparse

import aiohttp

from utils.url_safety import UnsafeURL, validate_url_async

_robots_cache: dict[str, str] = {}
_PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")


def load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts directory.

    Args:
        filename: Name of the prompt file (e.g. 'system_prompt.txt').

    Returns:
        Contents of the prompt file.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    path = os.path.join(_PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


async def is_allowed_by_robots(
    url: str,
    user_agent: str = "Mozilla/5.0",
    session: aiohttp.ClientSession | None = None,
) -> bool:
    """Check robots.txt to determine if fetching the URL is permitted.
    Results are cached per domain for efficiency.
    Returns True when in doubt (missing/malformed robots.txt or errors).
    """
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            logging.warning("Invalid URL for robots.txt check: %s", url)
            return True
        await validate_url_async(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    except (UnsafeURL, ValueError) as e:
        logging.warning("Unsafe URL for robots.txt check: %s | %s", url, e)
        return False
    except Exception as e:
        logging.warning("Exception parsing URL for robots.txt: %s | %s", url, e)
        return True

    if robots_url in _robots_cache:
        content = _robots_cache[robots_url]
    else:
        async def _fetch(sess: aiohttp.ClientSession) -> str:
            await validate_url_async(robots_url)
            async with sess.get(robots_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return ""
                return await resp.text()

        try:
            if session is not None and not session.closed:
                content = await _fetch(session)
            else:
                async with aiohttp.ClientSession() as ephemeral_session:
                    content = await _fetch(ephemeral_session)
            _robots_cache[robots_url] = content
        except Exception as e:
            logging.warning("Error fetching robots.txt for %s: %s", robots_url, e)
            _robots_cache[robots_url] = ""
            return True

    if not content:
        return True

    try:
        allowed = True
        current_ua = None
        for line in content.splitlines():
            line = line.strip()
            if line.lower().startswith("user-agent:"):
                current_ua = line.split(":", 1)[1].strip()
            elif line.lower().startswith("disallow:") and (
                current_ua == "*" or (current_ua is not None and user_agent in current_ua)
            ):
                path = line.split(":", 1)[1].strip()
                if path and parsed.path.startswith(path):
                    allowed = False
        return allowed
    except Exception as e:
        logging.warning("Malformed robots.txt for %s: %s", robots_url, e)
        return True
