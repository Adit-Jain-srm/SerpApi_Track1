"""Aggregator suffix, GitHub path, and non-retryable status rules. No network."""

from agents.search_agent import compare_candidates, is_aggregator
from config.constants import (
    AGGREGATOR_DOMAINS,
    GITHUB_NON_REPO_SECTIONS,
    NON_RETRYABLE_STATUS_CODES,
    github_url_is_blocked,
)
from models.candidate import Candidate


def test_edu_suffix_matches_schools_not_the_bare_label() -> None:
    assert ".edu" in AGGREGATOR_DOMAINS
    assert ".ac.uk" in AGGREGATOR_DOMAINS
    assert ".ac.in" in AGGREGATOR_DOMAINS
    assert "edu" not in AGGREGATOR_DOMAINS
    assert "ac.uk" not in AGGREGATOR_DOMAINS

    assert is_aggregator("https://mit.edu/research")
    assert is_aggregator("https://www.stanford.edu/")
    assert is_aggregator("https://www.cam.ac.uk/")
    assert is_aggregator("https://www.iitb.ac.in/")
    # The suffix branch is endswith, so the host must not have to equal "edu".
    assert is_aggregator("http://edu/") is False
    assert is_aggregator("https://education.com/") is False
    assert is_aggregator("https://ac.uk/") is False


def test_gov_suffix_matches_us_and_country_governments() -> None:
    assert ".gov" in AGGREGATOR_DOMAINS
    for suffix in (".gov.uk", ".gov.in", ".gov.au", ".gov.ca", ".gov.sg"):
        assert suffix in AGGREGATOR_DOMAINS
    assert "gov.us" not in AGGREGATOR_DOMAINS
    assert "gov.uk" not in AGGREGATOR_DOMAINS

    assert is_aggregator("https://nasa.gov/news")
    assert is_aggregator("https://www.whitehouse.gov/")
    assert is_aggregator("http://gov/") is False
    assert is_aggregator("https://www.gov.uk/")
    assert is_aggregator("https://www.service.gov.uk/start")
    assert is_aggregator("https://www.india.gov.in/")
    assert is_aggregator("https://nasa.com/") is False


def test_apple_subdomain_stays_blocked_without_itunes_entry() -> None:
    assert "apple.com" in AGGREGATOR_DOMAINS
    assert "itunes.apple.com" not in AGGREGATOR_DOMAINS
    assert is_aggregator("https://itunes.apple.com/us/app/example/id1")
    assert is_aggregator("https://apps.apple.com/us/app/example/id1")
    assert is_aggregator("https://www.apple.com/shop")


def test_github_repository_root_is_kept_and_other_paths_are_blocked() -> None:
    repo = "https://github.com/openai/whisper"
    repo_slash = "https://github.com/openai/whisper/"
    topics = "https://github.com/topics"
    topics_page = "https://github.com/topics/machine-learning"

    assert "github.com" not in AGGREGATOR_DOMAINS
    assert "gist.github.com" in AGGREGATOR_DOMAINS
    assert "github.io" in AGGREGATOR_DOMAINS
    assert GITHUB_NON_REPO_SECTIONS >= {
        "topics",
        "features",
        "marketplace",
        "collections",
        "settings",
        "pull",
        "issues",
        "actions",
    }

    assert github_url_is_blocked(repo) is False
    assert is_aggregator(repo) is False
    assert is_aggregator(repo_slash) is False
    assert is_aggregator("https://www.github.com/openai/whisper") is False
    assert is_aggregator("https://github.com/openai/whisper?utm_source=news") is False

    assert github_url_is_blocked(topics) is True
    assert is_aggregator(topics) is True
    assert is_aggregator(topics_page) is True
    assert is_aggregator("https://github.com/features") is True
    assert is_aggregator("https://github.com/marketplace/actions") is True
    assert is_aggregator("https://github.com/openai/whisper/issues") is True
    assert is_aggregator("https://github.com/openai/whisper/pull/12") is True
    assert is_aggregator("https://github.com/openai/whisper/actions") is True
    assert is_aggregator("https://gist.github.com/openai/abc") is True
    assert is_aggregator("https://openai.github.io/whisper/") is True

    kept = compare_candidates(
        [
            Candidate(url=repo, title="Whisper", engines={"google"}),
            Candidate(url=topics, title="Topics", engines={"google"}),
            Candidate(url="https://gist.github.com/openai/abc", title="Gist", engines={"google"}),
        ]
    )
    assert [item.url for item in kept] == [repo]


def test_directory_hosts_and_no_parent_already_covers_a_host() -> None:
    for host in (
        "producthunt.com",
        "theresanaiforthat.com",
        "futurepedia.io",
        "topai.tools",
        "futuretools.io",
    ):
        assert host in AGGREGATOR_DOMAINS
        assert is_aggregator(f"https://{host}/tool")

    hosts = [domain for domain in AGGREGATOR_DOMAINS if not domain.startswith(".")]
    for host in hosts:
        for parent in hosts:
            if host != parent and (host == parent or host.endswith("." + parent)):
                raise AssertionError(f"{host} is already covered by {parent}")


def test_roundup_hosts_from_the_digest_are_dropped() -> None:
    for host in ("worldlybrief.com", "readsforyou.com"):
        assert host in AGGREGATOR_DOMAINS
        assert is_aggregator(f"https://{host}/new-ai-tools-launched-this-week/")
        assert is_aggregator(f"https://www.{host}/8-new-ai-tools/")

    assert "cbsnews.com" not in AGGREGATOR_DOMAINS
    assert "medium.com" in AGGREGATOR_DOMAINS
    assert "substack.com" in AGGREGATOR_DOMAINS


def test_401_410_and_451_are_not_retried() -> None:
    for status in (401, 403, 404, 410, 451):
        assert status in NON_RETRYABLE_STATUS_CODES
    for status in (200, 429, 500, 502, 503):
        assert status not in NON_RETRYABLE_STATUS_CODES
