"""
config_agent.py: Handles environment variable loading, API key setup, and logging configuration.
"""
import logging
import os
from dataclasses import dataclass

import dotenv

from config.constants import BATCH_SIZE, LLM_CONCURRENCY_LIMIT, SEARCH_DAYS

dotenv.load_dotenv()

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT: str | None = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY: str | None = os.environ.get("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT: str | None = os.environ.get("AZURE_OPENAI_DEPLOYMENT")

_CRITICAL_CONFIG = (
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_KEY",
    "SERPAPI_API_KEY",
)


@dataclass(frozen=True)
class Settings:
    """Runtime settings. Constants are the defaults; environment variables may override them."""

    batch_size: int
    llm_concurrency_limit: int
    search_days: int
    max_urls: int | None = 10
    dry_run: bool = False
    skip_teams: bool = False
    skip_slack: bool = False
    skip_subscribers: bool = False


def _env_int(name: str, default: int) -> int:
    """Read a positive integer from the environment, or return the constant default."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}.") from exc
    if value < 1:
        raise ValueError(f"{name} must be a positive integer, got {value}.")
    return value


def load_settings() -> Settings:
    """Load pipeline settings, letting the environment override the constants."""
    return Settings(
        batch_size=_env_int("BATCH_SIZE", BATCH_SIZE),
        llm_concurrency_limit=_env_int("LLM_CONCURRENCY_LIMIT", LLM_CONCURRENCY_LIMIT),
        search_days=_env_int("SEARCH_DAYS", SEARCH_DAYS),
        max_urls=_env_int("MAX_URLS", 10),
    )


def _missing(names: tuple[str, ...]) -> list[str]:
    return [name for name in names if not (os.environ.get(name) or "").strip()]


def require_serpapi_key() -> None:
    """Raise when a live search has no SerpApi key. A custom client does not call this."""
    missing = _missing(("SERPAPI_API_KEY",))
    if missing:
        raise ValueError(
            "Missing critical configuration: SERPAPI_API_KEY. "
            "Please check your .env file and ensure all required API keys are set."
        )


def setup_logging() -> None:
    """Configure logging with timestamp formatting and reduced noise from third-party libraries."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    for lib in ("aiohttp", "openai", "azure", "urllib3"):
        logging.getLogger(lib).setLevel(logging.WARNING)


def validate_critical_config() -> None:
    """Validate that Azure and SerpApi credentials are present.

    Raises:
        ValueError: If any critical configuration is missing.
    """
    missing = _missing(_CRITICAL_CONFIG)
    if missing:
        raise ValueError(
            f"Missing critical configuration: {', '.join(missing)}. "
            "Please check your .env file and ensure all required API keys are set."
        )
