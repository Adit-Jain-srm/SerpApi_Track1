import logging
import re

import requests

from models.tool_info import ToolInfo
from utils.url_safety import UnsafeURL, validate_url

_GENERIC_FEATURES = frozenset({
    "BPO Services", "Consultation", "Talent Outsourcing",
    "International Logistics BPO", "E-Recovery", "Process Automation", "Services",
})


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


def format_tool_for_teams(tool: ToolInfo, idx: int) -> str:
    """Format a ToolInfo as a Markdown message suitable for Microsoft Teams."""
    features = _feature_lines(tool.features)
    features_str = "\n".join(f"- {f}" for f in features) if features else "N/A"

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

    website_line = f"**\U0001f310 Website:** [{tool.website}]({tool.website})\n\n" if tool.website != tool.source else ""

    return (
        f"### \U0001f680 AI Tool {idx}: {tool.title or 'N/A'}\n\n"
        f"{website_line}"
        f"**\U0001f517 Source:** [{tool.source}]({tool.source})\n\n"
        f"**\U0001f3af Target Audience / Use Case:** {target}\n\n"
        f"**\U0001f4dd Overview:**\n{overview}\n\n"
        f"**\U0001f4a1 Key Features:**\n{features_str}\n\n"
        f"**\U0001f4b2 Pricing:** {pricing}\n\n"
    )


def send_tool_to_teams(tool: ToolInfo, idx: int, webhook_url: str) -> bool:
    """Post a formatted tool message to Microsoft Teams via webhook.

    The webhook URL is the secret. Failures log a status or exception type only.
    """
    webhook = (webhook_url or "").strip()
    if not webhook:
        logging.warning("TEAMS_WEBHOOK_URL not set. Skipping Teams notification.")
        return False
    try:
        webhook = validate_url(webhook)
    except UnsafeURL:
        logging.error("Teams webhook rejected by outbound URL policy.")
        return False

    try:
        payload = {"text": format_tool_for_teams(tool, idx)}
        response = requests.post(webhook, json=payload, timeout=15, allow_redirects=False)
    except requests.RequestException as exc:
        logging.error("Teams webhook request failed for tool %s: %s", idx, type(exc).__name__)
        return False
    except Exception:
        logging.error("Teams notification failed for tool %s.", idx)
        return False

    if response.status_code == 200:
        logging.info("Tool %s sent to Microsoft Teams successfully.", idx)
        return True
    logging.error("Failed to send tool %s to Teams: HTTP %s", idx, response.status_code)
    return False
