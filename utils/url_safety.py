"""Outbound URL validation for server-side HTTP requests."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeURL(ValueError):
    """Raised when a URL resolves to a private or otherwise unsafe destination."""


_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata",
        "instance-data.ec2.internal",
    }
)
_MAX_HOSTNAME_LENGTH = 253


def _blocked_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def _resolve(hostname: str) -> set[str]:
    try:
        records = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeURL(f"Could not resolve outbound host {hostname!r}") from exc

    addresses = {record[4][0] for record in records}
    if not addresses:
        raise UnsafeURL(f"Outbound host {hostname!r} has no addresses")
    return addresses


def validate_url(url: str, *, resolve: bool = True) -> str:
    """Validate an HTTPS URL and reject private, local, or metadata destinations."""
    if not isinstance(url, str):
        raise UnsafeURL("Outbound URL must be a string")

    parsed = urlparse(url.strip())
    hostname = (parsed.hostname or "").rstrip(".").lower()
    if parsed.scheme.lower() != "https" or not hostname:
        raise UnsafeURL("Outbound URL must use HTTPS and include a hostname")
    if len(hostname) > _MAX_HOSTNAME_LENGTH or hostname in _BLOCKED_HOSTNAMES:
        raise UnsafeURL(f"Outbound host {hostname!r} is not allowed")

    try:
        literal = ipaddress.ip_address(hostname)
        addresses = {str(literal)}
    except ValueError:
        addresses = _resolve(hostname) if resolve else set()

    for value in addresses:
        if _blocked_ip(ipaddress.ip_address(value)):
            raise UnsafeURL(f"Outbound host {hostname!r} resolves to a blocked address")
    return parsed.geturl()


async def validate_url_async(url: str) -> str:
    """Resolve and validate a URL without blocking the event loop."""
    return await asyncio.to_thread(validate_url, url)
