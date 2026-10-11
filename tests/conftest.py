"""Keep discovery tests off the network and independent of the developer environment."""
import pytest

_HERMETIC_ENV = (
    "SERPAPI_API_KEY",
    "SERPAPI_KEY",
    "SERPER_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_KEY",
    "AZURE_OPENAI_DEPLOYMENT",
    "TEAMS_WEBHOOK_URL",
    "SLACK_BOT_TOKEN",
    "SLACK_APP_TOKEN",
    "SLACK_CHANNEL_ID",
    "BATCH_SIZE",
    "LLM_CONCURRENCY_LIMIT",
    "SEARCH_DAYS",
    "SUPABASE_URL",
    "SUPABASE_SECRET_KEY",
    "NEXT_PUBLIC_SUPABASE_URL",
    "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
    "REQUIRE_TEAMS_DELIVERY",
    "REQUIRE_SLACK_DELIVERY",
    "REQUIRE_SUBSCRIBER_DELIVERY",
)


@pytest.fixture(autouse=True)
def hermetic_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop credentials loaded from .env so tests cannot call SerpApi, Azure, or Slack."""
    for name in _HERMETIC_ENV:
        monkeypatch.delenv(name, raising=False)
