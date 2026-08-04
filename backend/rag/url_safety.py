"""Network-level safety checks for every user-supplied fetch target.

`backend.security_utils.validate_url` runs at request-validation time and only
inspects the URL string: length, control characters, and scheme. That cannot
stop a syntactically valid URL from pointing at a loopback, private, or
link-local address, so a submitted `course_url` or `book_url` could otherwise
make the worker fetch internal services such as cloud instance metadata and
hand the response to the outline model.

This module closes that gap at fetch time, where the host can actually be
resolved. It is deliberately separate from `sources/policy.py`: policy
evaluation is a pure function over a candidate record, while these checks
perform DNS resolution and must run immediately before each request (plan step
0.6.1, extended to redirect hops in 0.6.2).
"""

from __future__ import annotations

import socket
from collections.abc import Callable
from ipaddress import IPv4Address, IPv6Address, ip_address
from urllib.parse import urlsplit

from backend.rag.errors import RagError

ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https"})
ALLOWED_PORTS: frozenset[int] = frozenset({80, 443})
DEFAULT_PORTS: dict[str, int] = {"http": 80, "https": 443}

HostResolver = Callable[[str, int], list[str]]
"""Resolve a host and port to its IP addresses, so tests stay off the network."""


class UnsafeUrlError(RagError):
    """Raised when a fetch target is not a safe, public HTTP(S) address."""


def resolve_host(host: str, port: int) -> list[str]:
    """Return every IP address a host resolves to, as plain strings."""

    try:
        addresses = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as error:
        raise UnsafeUrlError(f"Host {host!r} could not be resolved.") from error
    return [info[4][0] for info in addresses]


def validate_fetch_target(url: str, *, resolver: HostResolver = resolve_host) -> None:
    """Raise UnsafeUrlError unless the URL is a public HTTP(S) fetch target.

    Every resolved address must be public. A host that resolves to a mix of
    public and private addresses is rejected outright rather than filtered,
    because the winning address is chosen by the HTTP client after this check.
    """

    scheme, host, port = _split_target(url)
    if scheme not in ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"URL scheme {scheme!r} is not fetchable; use http or https.")
    if not host:
        raise UnsafeUrlError("URL does not contain a host.")
    if port not in ALLOWED_PORTS:
        raise UnsafeUrlError(f"Port {port} is not fetchable; use 80 or 443.")

    addresses = resolver(host, port)
    if not addresses:
        raise UnsafeUrlError(f"Host {host!r} did not resolve to any address.")
    for address in addresses:
        if not _is_public_address(address):
            # The address itself stays out of the message: this text reaches the
            # user through InputNormalizationError and would disclose internal
            # network layout.
            raise UnsafeUrlError(f"Host {host!r} resolves to a non-public address.")


def _split_target(url: str) -> tuple[str, str, int]:
    """Return the scheme, host, and effective port for a fetch target."""

    try:
        parts = urlsplit(url.strip())
        scheme = parts.scheme.casefold()
        host = (parts.hostname or "").casefold()
        port = parts.port
    except ValueError as error:
        raise UnsafeUrlError(f"URL could not be parsed as a fetch target: {error}") from error
    return scheme, host, port if port is not None else DEFAULT_PORTS.get(scheme, -1)


def _is_public_address(address: str) -> bool:
    """Report whether a resolved address is safe to send a request to."""

    try:
        parsed = ip_address(address)
    except ValueError:
        return False

    if isinstance(parsed, IPv6Address) and parsed.ipv4_mapped is not None:
        # ::ffff:127.0.0.1 is a loopback request wearing an IPv6 costume.
        parsed = parsed.ipv4_mapped

    blocked = (
        parsed.is_loopback
        or parsed.is_private
        or parsed.is_link_local
        or parsed.is_reserved
        or parsed.is_multicast
        or parsed.is_unspecified
    )
    if blocked:
        return False
    # Backstop for ranges the specific flags miss on one address family.
    return _is_global(parsed)


def _is_global(parsed: IPv4Address | IPv6Address) -> bool:
    try:
        return parsed.is_global
    except ValueError:
        return False
