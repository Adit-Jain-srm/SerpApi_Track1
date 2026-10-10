"""Post digest messages to Slack with chat.postMessage.

Content rules match Microsoft Teams (features, pricing, overview, audience).
The text is Slack mrkdwn. SLACK_APP_TOKEN is not read here; it is reserved
for a future socket-mode listener and is not used to post.
"""
import logging
import re

import requests

from models.tool_info import ToolInfo

_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"
_TOKEN_MARKERS = ("xoxb-", "xapp-", "xoxp-", "xoxa-")

_GENERIC_FEATURES = frozenset({
    "BPO Services", "Consultation", "Talent Outsourcing",
    "International Logistics BPO", "E-Recovery", "Process Automation", "Services",
})


def _escape(value: str) -> str:
    """Escape the three characters Slack mrkdwn treats as markup."""
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _public_detail(value: object) -> str:
    """Return a log-safe error string. Tokens are never written to the log."""
    text = str(value)
    if any(marker in text for marker in _TOKEN_MARKERS):
        return "slack error"
    return text


def _mrkdwn_link(url: str) -> str:
    if not url:
        return "N/A"
    if any(char in url for char in "<|>"):
        return _escape(url)
    return f"<{url}|{_escape(url)}>"


def _feature_lines(features: object) -> list[str]:
    """Keep unique feature strings. Nulls and non-strings are skipped."""
    if isinstance(features, str):
        raw: list[object] = [features]
    elif isinstance(features, list):
        raw = list(features)
    else:
        raw = []
    kept: list[str] = []
    seen: set[str] = set()
    for feature in raw:
        if not isinstance(feature, str):
            continue
        text = feature.strip()
        if not text or text in seen or text in _GENERIC_FEATURES or len(text) <= 5:
            continue
        seen.add(text)
        kept.append(text)
    return kept


def format_tool_for_slack(tool: ToolInfo, idx: int) -> str:
    """Format a ToolInfo as Slack mrkdwn. Omit Website when it duplicates Source."""
    features = _feature_lines(tool.features)
    features_str = "\n".join(f"- {_escape(f)}" for f in features) if features else "N/A"

    pricing = tool.pricing
    if not pricing or len(str(pricing).split()) > 20 or (isinstance(pricing, str) and "revolution" in pricing.lower()):
        pricing = "No pricing information available."

    overview = tool.summary or (tool.main_text[:300] if tool.main_text else "")
    if overview:
        sentences = re.split(r"(?<=[.!?]) +", overview)
        if len(sentences) > 5:
            overview = " ".join(sentences[:5])
        elif len(overview.split()) > 80:
            overview = " ".join(overview.split()[:80]) + "..."
    overview = overview or "N/A"

    audience = tool.target_audience if isinstance(tool.target_audience, str) else ""
    target = audience if len(audience) >= 3 else "N/A"

    website_line = ""
    if tool.website != tool.source:
        website_line = f"*\U0001f310 Website:* {_mrkdwn_link(tool.website)}\n\n"

    return (
        f"*\U0001f680 AI Tool {idx}: {_escape(tool.title or 'N/A')}*\n\n"
        f"{website_line}"
        f"*\U0001f517 Source:* {_mrkdwn_link(tool.source)}\n\n"
        f"*\U0001f3af Target Audience / Use Case:* {_escape(target)}\n\n"
        f"*\U0001f4dd Overview:*\n{_escape(overview)}\n\n"
        f"*\U0001f4a1 Key Features:*\n{features_str}\n\n"
        f"*\U0001f4b2 Pricing:* {_escape(str(pricing))}\n\n"
    )


def send_tool_to_slack(tool: ToolInfo, idx: int, bot_token: str, channel: str) -> None:
    """Post one tool digest. Missing credentials or an API error is logged, not raised."""
    token = (bot_token or "").strip()
    channel_id = (channel or "").strip()
    if not token or not channel_id:
        logging.warning("SLACK_BOT_TOKEN or SLACK_CHANNEL_ID not set. Skipping Slack notification.")
        return

    try:
        response = requests.post(
            _POST_MESSAGE_URL,
            headers={"Authorization": f"Bearer {token}"},
            json={"channel": channel_id, "text": format_tool_for_slack(tool, idx)},
            timeout=15,
        )
    except requests.RequestException as exc:
        logging.error("Slack post failed for tool %s: %s", idx, _public_detail(exc))
        return
    except Exception as exc:
        logging.error("Slack notification failed for tool %s: %s", idx, type(exc).__name__)
        return

    error = ""
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        error = _public_detail(body.get("error") or "")

    if response.status_code == 200 and isinstance(body, dict) and body.get("ok") is True:
        logging.info("Tool %s sent to Slack successfully.", idx)
        return

    logging.error(
        "Failed to send tool %s to Slack: %s",
        idx,
        error or f"HTTP {response.status_code}",
    )
