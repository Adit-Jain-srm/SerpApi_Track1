"""Tests for API health checks and doctor commands."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from check_apis import (
    badge,
    check_azure_openai,
    check_serpapi,
    check_slack,
    check_supabase,
    check_teams,
    run_all_checks,
)


def test_badge_formatting() -> None:
    pass_badge = badge("PASS", "All good")
    assert "PASS" in pass_badge
    assert "All good" in pass_badge

    fail_badge = badge("FAIL", "Something broke")
    assert "FAIL" in fail_badge

    warn_badge = badge("WARN", "Caution")
    assert "WARN" in warn_badge


def test_check_serpapi_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    res = check_serpapi()
    assert res["status"] == "FAIL"
    assert "not set" in res["message"]


def test_check_serpapi_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERPAPI_API_KEY", "dummy_key")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "account_email": "tester@example.com",
        "total_searches_left": 150,
        "plan_name": "Developer",
    }
    with patch("requests.get", return_value=mock_resp):
        res = check_serpapi()
        assert res["status"] == "PASS"
        assert "tester@example.com" in res["message"]
        assert res["details"]["searches_left"] == 150


def test_check_azure_openai_missing_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    res = check_azure_openai()
    assert res["status"] == "FAIL"
    assert "AZURE_OPENAI_ENDPOINT" in res["message"]


def test_check_supabase_missing_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("NEXT_PUBLIC_SUPABASE_URL", raising=False)
    res = check_supabase()
    assert res["status"] == "WARN"
    assert "not set" in res["message"]


def test_check_supabase_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "dummy_secret")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-range": "0-0/3"}
    mock_resp.json.return_value = [{"user_id": "u1"}]
    with patch("requests.get", return_value=mock_resp):
        res = check_supabase()
        assert res["status"] == "PASS"
        assert "subscribers: 3" in res["message"]


def test_check_slack_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    res = check_slack()
    assert res["status"] == "INFO"


def test_check_slack_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "C123")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"ok": True, "user": "botty", "team": "MyTeam"}
    with patch("requests.post", return_value=mock_resp):
        res = check_slack()
        assert res["status"] == "PASS"
        assert "@botty" in res["message"]


def test_check_teams_formatting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "http://insecure.url")
    res = check_teams()
    assert res["status"] == "WARN"

    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://secure.webhook.office.com")
    res = check_teams()
    assert res["status"] == "PASS"


def test_run_all_checks() -> None:
    results = run_all_checks()
    assert "serpapi" in results
    assert "azure_openai" in results
    assert "supabase" in results
    assert "slack" in results
    assert "teams" in results
