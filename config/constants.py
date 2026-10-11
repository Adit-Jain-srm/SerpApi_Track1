# Global constants for the AI Tool Discovery Agent

from urllib.parse import urlparse

LLM_INPUT_TRUNCATION_LIMIT = 15_000  # Max HTML chars sent to LLM

AGGREGATOR_DOMAINS = frozenset([
    # Social media & video
    "youtube.com", "youtu.be", "reddit.com", "linkedin.com", "facebook.com",
    "twitter.com", "x.com", "tiktok.com", "instagram.com", "pinterest.com",
    "discord.com", "slack.com", "telegram.org",
    # News & media
    "msn.com", "yahoo.com", "cnn.com", "bbc.com", "reuters.com", "bloomberg.com",
    "forbes.com", "techcrunch.com", "venturebeat.com", "theverge.com", "wired.com",
    "cnbc.com", "marketwatch.com",
    # AI tool aggregators
    "forum.freecodecamp.org", "futuretools.io", "aitools.fyi", "toolify.ai", "toolsai.io",
    "producthunt.com", "theresanaiforthat.com", "futurepedia.io", "topai.tools",
    "worldlybrief.com", "readsforyou.com",
    # Review & comparison sites
    "g2.com", "capterra.com", "getapp.com", "alternativeto.net", "slant.co", "trustpilot.com",
    # Freelance & job boards
    "fiverr.com", "upwork.com", "freelancer.com", "indeed.com", "glassdoor.com", "monster.com",
    # E-commerce
    "amazon.com", "aliexpress.com", "ebay.com", "apple.com",
    # Public suffixes (leading dot: domain.endswith, not an exact host)
    ".gov", ".gov.uk", ".gov.in", ".gov.au", ".gov.ca", ".gov.sg",
    ".edu", ".ac.uk", ".ac.in",
    # Search engines
    "google.com", "bing.com", "duckduckgo.com", "serper.dev", "serpapi.com",
    # Crowdfunding
    "patreon.com", "kickstarter.com", "indiegogo.com", "gofundme.com",
    # Petitions
    "change.org", "avaaz.org",
    # Events
    "eventbrite.com", "meetup.com", "eventful.com", "ticketmaster.com",
    # Audio streaming
    "soundcloud.com", "spotify.com",
    # Archives & reference
    "archive.org", "waybackmachine.org", "wikipedia.org", "wikidata.org", "wikimedia.org",
    # Q&A & developer platforms
    # github.com repository roots are launches; github_url_is_blocked classifies that host.
    "quora.com", "stackexchange.com", "stackoverflow.com",
    "gist.github.com", "github.io", "gitlab.com", "bitbucket.org",
    # Productivity platforms
    "notion.so", "airtable.com", "asana.com", "trello.com",
    # Email marketing
    "mailchi.mp", "mailchimp.com", "sendgrid.com", "constantcontact.com",
    # Design platforms
    "dribbble.com", "behance.net",
    # Classifieds
    "craigslist.org",
    # Blogging & forums
    "medium.com", "substack.com", "news.ycombinator.com", "hackernews.com", "hacker-news.com",
])

# github.com itself is not an aggregator: open-source launches live at /<owner>/<repo>.
GITHUB_HOST = "github.com"
GITHUB_NON_REPO_SECTIONS = frozenset({
    "topics",
    "features",
    "marketplace",
    "collections",
    "settings",
    "pull",
    "issues",
    "actions",
})


def github_url_is_blocked(url: str) -> bool:
    """Return True when a github.com URL is not a repository root.

    Allows https://github.com/<owner>/<repo> and that same path with a trailing
    slash. Site sections and any deeper path are blocked. Other hosts, including
    gist.github.com and *.github.io, return False so the domain list decides.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    if host != GITHUB_HOST:
        return False
    segments = [segment for segment in parsed.path.split("/") if segment]
    if len(segments) != 2:
        return True
    if segments[0].lower() in GITHUB_NON_REPO_SECTIONS:
        return True
    return False


BATCH_SIZE = 4
LLM_CONCURRENCY_LIMIT = 2
SEARCH_DAYS = 7

# Launch announcements. News and web both run these, then the pipeline
# follows a single product URL named on an article.
BASE_QUERIES = [
    '"just launched" ("AI tool" OR "AI app" OR "AI agent")',
    '"now available" ("AI assistant" OR "AI copilot") (pricing OR "sign up")',
    '"public beta" AI (platform OR app OR agent)',
    '"open-source" ("AI tool" OR "AI agent") launched',
]

# Homepage-intent queries. Web only, inside the same date window.
# 6 web searches + 4 news searches = 10. Not a crawl.
HOMEPAGE_QUERIES = [
    '"we launched" AI (pricing OR "sign up" OR "get started")',
    'intitle:introducing ("AI tool" OR "AI app" OR "AI agent")',
]

# Articles name a product URL. This caps the extra homepage fetches.
FOLLOW_HOP_LIMIT = 12

# Hosts that show up beside a product link and are never the product.
# Matched on the registrable domain (fonts.gstatic.com matches gstatic.com).
NON_PRODUCT_DOMAINS = frozenset({
    "gstatic.com",
    "googleapis.com",
    "google-analytics.com",
    "googletagmanager.com",
    "googleusercontent.com",
    "cloudflare.com",
    "cloudflareinsights.com",
    "jsdelivr.net",
    "unpkg.com",
    "schema.org",
    "w3.org",
    "gravatar.com",
    "wp.com",
    "doubleclick.net",
    "onetrust.com",
    "cookiebot.com",
})

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
    "Pragma": "no-cache",
    "Referer": "https://www.google.com/",
}

NON_RETRYABLE_STATUS_CODES = frozenset({401, 403, 404, 410, 451})
