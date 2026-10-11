"""Classify a URL as an article or a product page. No network and no model."""

import re
from urllib.parse import urlparse

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
_DIRECTORY_MARKERS = (
    "/topics/",
    "/topic/",
    "/category/",
    "/categories/",
    "/tag/",
    "/tags/",
    "/hub/",
)
_DATED_PATH = re.compile(r"/20[0-9]{2}/[0-9]{2}/")
_LANG = re.compile(r"^[a-z]{2}$")


def _host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    if host.startswith("www."):
        return host[4:]
    return host


def _padded_path(url: str) -> str:
    path = (urlparse(url).path or "").lower()
    return f"/{path.strip('/')}/" if path.strip("/") else "/"


def page_is_directory(url: str) -> bool:
    """True for a topic or category index. That page is not one product."""
    padded = _padded_path(url)
    return any(marker in padded for marker in _DIRECTORY_MARKERS)


def page_is_article(url: str) -> bool:
    """True for blog and news URLs. A product homepage is not an article."""
    host = _host(url)
    if host.startswith("blog.") or host.startswith("news."):
        return True
    path = (urlparse(url).path or "").lower()
    padded = _padded_path(url)
    if any(marker in padded for marker in _ARTICLE_PATH_MARKERS):
        return True
    if _DATED_PATH.search(path):
        return True
    segments = [segment for segment in path.split("/") if segment]
    # /en/a-long-news-slug is a story. /en/pricing is not.
    return (
        len(segments) >= 2
        and _LANG.fullmatch(segments[0]) is not None
        and len(segments[-1]) >= 24
    )
