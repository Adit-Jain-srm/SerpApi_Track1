from dataclasses import dataclass, field


@dataclass
class Candidate:
    """A URL kept after web and news hits are compared, before any page is fetched."""

    url: str
    title: str = ""
    snippet: str = ""
    published_at: str = ""
    engines: set[str] = field(default_factory=set)
