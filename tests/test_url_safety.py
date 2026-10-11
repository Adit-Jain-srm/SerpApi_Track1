import pytest

from utils.url_safety import UnsafeURL, validate_url


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1/admin",
        "https://10.0.0.1/",
        "https://169.254.169.254/latest/meta-data",
        "https://[::1]/",
        "https://localhost/",
    ],
)
def test_private_and_metadata_destinations_are_rejected(url: str) -> None:
    with pytest.raises(UnsafeURL):
        validate_url(url)


def test_https_public_literal_is_allowed() -> None:
    assert validate_url("https://8.8.8.8/health") == "https://8.8.8.8/health"
