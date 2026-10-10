"""Configuration requirements and environment overrides."""
import pytest

from agents.config_agent import load_settings, validate_critical_config
from config.constants import BATCH_SIZE, LLM_CONCURRENCY_LIMIT, SEARCH_DAYS


def _set_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_KEY", "key")
    monkeypatch.setenv("SERPAPI_API_KEY", "key")


def test_config_requires_serpapi_and_azure_not_serper() -> None:
    with pytest.raises(ValueError, match="SERPAPI_API_KEY") as caught:
        validate_critical_config()
    message = str(caught.value)
    assert "AZURE_OPENAI_ENDPOINT" in message
    assert "AZURE_OPENAI_KEY" in message
    assert "SERPER" not in message
    assert "AZURE_OPENAI_DEPLOYMENT" not in message


def test_config_accepts_keys_without_serper(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_valid(monkeypatch)
    validate_critical_config()

    monkeypatch.delenv("SERPAPI_API_KEY")
    with pytest.raises(ValueError, match="SERPAPI_API_KEY"):
        validate_critical_config()

    _set_valid(monkeypatch)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT")
    with pytest.raises(ValueError, match="AZURE_OPENAI_ENDPOINT"):
        validate_critical_config()

    _set_valid(monkeypatch)
    monkeypatch.delenv("AZURE_OPENAI_KEY")
    with pytest.raises(ValueError, match="AZURE_OPENAI_KEY"):
        validate_critical_config()

    _set_valid(monkeypatch)
    monkeypatch.setenv("SERPAPI_API_KEY", "   ")
    with pytest.raises(ValueError, match="SERPAPI_API_KEY"):
        validate_critical_config()


def test_settings_use_constants_unless_overridden(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load_settings()
    assert settings.batch_size == BATCH_SIZE == 4
    assert settings.llm_concurrency_limit == LLM_CONCURRENCY_LIMIT == 2
    assert settings.search_days == SEARCH_DAYS == 7

    monkeypatch.setenv("BATCH_SIZE", "8")
    monkeypatch.setenv("LLM_CONCURRENCY_LIMIT", "3")
    monkeypatch.setenv("SEARCH_DAYS", "10")
    overridden = load_settings()
    assert overridden.batch_size == 8
    assert overridden.llm_concurrency_limit == 3
    assert overridden.search_days == 10
    assert BATCH_SIZE == 4
    assert SEARCH_DAYS == 7


def test_settings_reject_invalid_integers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEARCH_DAYS", "week")
    with pytest.raises(ValueError, match="SEARCH_DAYS"):
        load_settings()

    monkeypatch.setenv("SEARCH_DAYS", "0")
    with pytest.raises(ValueError, match="SEARCH_DAYS"):
        load_settings()
