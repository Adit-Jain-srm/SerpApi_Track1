"""Subscriber webhook delivery. No network."""

from models.tool_info import ToolInfo
from output.subscribers import notify_subscribers


def _tool() -> ToolInfo:
    return ToolInfo(
        title="Nova",
        website="https://nova.example",
        source="https://nova.example",
        summary="Writes briefs.",
        ai_tool_annotation="ai_tool",
    )


def test_http_webhooks_are_not_posted(monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "secret")

    class Response:
        status_code = 200

        def json(self):
            return [
                {"teams_webhook_url": "http://teams.example/hook", "slack_webhook_url": "https://hooks.slack.com/services/abc"},
            ]

    posted: list[str] = []

    def get(url, params, headers, timeout):
        del url, params, headers, timeout
        return Response()

    monkeypatch.setattr("output.subscribers.requests.get", get)
    monkeypatch.setattr("output.subscribers.validate_url", lambda value: value)

    def poster(url: str, payload: dict[str, str]) -> int:
        del payload
        posted.append(url)
        return 200

    notify_subscribers([_tool()], poster=poster)

    assert posted == ["https://hooks.slack.com/services/abc"]
