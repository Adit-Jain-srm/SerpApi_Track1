"""Page fetch stays on TLS. No network."""
import asyncio

import pytest

from agents.scraper_agent import fetch_with_retries
from utils.error_handling import ScrapingError


class _Response:
    def __init__(self, status: int, headers: dict | None = None, body: str = "") -> None:
        self.status = status
        self.headers = headers or {}
        self.charset = "utf-8"
        self._body = body
        self.content = None

    async def text(self, encoding: str | None = None, errors: str | None = None) -> str:
        return self._body

    async def __aenter__(self) -> "_Response":
        return self

    async def __aexit__(self, *_args: object) -> bool:
        return False


class _StreamingContent:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    async def iter_chunked(self, _size: int):
        for chunk in self._chunks:
            yield chunk


class _Session:
    def __init__(self, responses: list[_Response]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, object, object]] = []

    def get(self, url: str, **kwargs: object) -> _Response:
        self.calls.append((url, kwargs.get("ssl"), kwargs.get("allow_redirects")))
        return self._responses.pop(0)


def _stub_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    async def allow(_url: str) -> bool:
        return True

    monkeypatch.setattr("agents.scraper_agent.is_allowed_by_robots", allow)
    async def safe(_url: str) -> str:
        return _url
    monkeypatch.setattr("agents.scraper_agent.validate_url_async", safe)
    monkeypatch.setattr("agents.scraper_agent.blacklist.is_blacklisted", lambda _domain: False)
    monkeypatch.setattr("agents.scraper_agent.blacklist.record_failure", lambda _domain: None)


def test_fetch_refuses_plaintext(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_gates(monkeypatch)
    session = _Session([])
    with pytest.raises(ScrapingError, match="non-TLS"):
        asyncio.run(fetch_with_retries("http://tools.example/page", session))  # type: ignore[arg-type]
    assert session.calls == []


def test_fetch_refuses_http_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_gates(monkeypatch)
    session = _Session([_Response(302, {"Location": "http://tools.example/page"})])
    with pytest.raises(ScrapingError, match="non-TLS"):
        asyncio.run(fetch_with_retries("https://tools.example/start", session))  # type: ignore[arg-type]
    assert session.calls == [("https://tools.example/start", True, False)]


def test_fetch_follows_https_with_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_gates(monkeypatch)
    session = _Session(
        [
            _Response(302, {"Location": "/final"}),
            _Response(200, body="<p>ok</p>"),
        ]
    )
    html = asyncio.run(fetch_with_retries("https://tools.example/start", session))  # type: ignore[arg-type]
    assert html == "<p>ok</p>"
    assert [call[0] for call in session.calls] == [
        "https://tools.example/start",
        "https://tools.example/final",
    ]
    assert all(ssl is True and allow_redirects is False for _url, ssl, allow_redirects in session.calls)


def test_fetch_truncates_oversized_body_instead_of_failing(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_gates(monkeypatch)
    response = _Response(200)
    response.content = _StreamingContent([b"a" * 400_000, b"b" * 200_000])
    session = _Session([response])

    html = asyncio.run(fetch_with_retries("https://tools.example/large", session))  # type: ignore[arg-type]

    assert len(html.encode("utf-8")) == 500_000
    assert html.endswith("b" * 100_000)
