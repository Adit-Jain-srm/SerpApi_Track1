from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolInfo:
    """Structured information about a discovered AI tool."""

    title: str
    website: str
    summary: str | None = None
    features: list[str] = field(default_factory=list)
    pricing: str | None = None
    source: str = ""
    target_audience: str | None = None
    main_text: str = ""
    ai_tool_annotation: str | None = None
    tags: list[str] = field(default_factory=list)
    publish_date: str | None = None
    is_recent: bool | None = None
