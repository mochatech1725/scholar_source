"""Fetch-target safety checks for plan step 0.6.1."""

import socket

import pytest

from backend.rag.url_safety import UnsafeUrlError, resolve_host, validate_fetch_target

PUBLIC_ADDRESS = "93.184.216.34"


def _resolver_returning(*addresses: str):
    """Build a resolver that always yields the given addresses."""

    def resolver(host: str, port: int) -> list[str]:
        return list(addresses)

    return resolver


_PUBLIC = _resolver_returning(PUBLIC_ADDRESS)


def test_accepts_a_public_https_url():
    validate_fetch_target("https://ocw.mit.edu/statics", resolver=_PUBLIC)


def test_accepts_an_explicit_allowed_port():
    validate_fetch_target("http://ocw.mit.edu:80/statics", resolver=_PUBLIC)


@pytest.mark.parametrize(
    ("label", "address"),
    [
        ("loopback", "127.0.0.1"),
        ("private_class_a", "10.0.0.7"),
        ("private_class_b", "172.16.4.9"),
        ("private_class_c", "192.168.1.10"),
        ("link_local_metadata", "169.254.169.254"),
        ("unspecified", "0.0.0.0"),
        ("multicast", "224.0.0.1"),
        ("carrier_grade_nat", "100.64.0.1"),
        ("ipv6_loopback", "::1"),
        ("ipv6_unique_local", "fd00::1"),
        ("ipv6_link_local", "fe80::1"),
        ("ipv4_mapped_loopback", "::ffff:127.0.0.1"),
    ],
)
def test_rejects_non_public_resolved_addresses(label: str, address: str):
    with pytest.raises(UnsafeUrlError, match="non-public address"):
        validate_fetch_target("https://internal.example.com/", resolver=_resolver_returning(address))


def test_rejects_a_host_resolving_to_both_public_and_private_addresses():
    """A mixed answer is rejected: the client, not this check, picks the address."""
    resolver = _resolver_returning(PUBLIC_ADDRESS, "127.0.0.1")
    with pytest.raises(UnsafeUrlError, match="non-public address"):
        validate_fetch_target("https://rebind.example.com/", resolver=resolver)


def test_rejects_a_literal_private_ip_host():
    with pytest.raises(UnsafeUrlError, match="non-public address"):
        validate_fetch_target(
            "http://169.254.169.254/latest/meta-data/", resolver=_resolver_returning("169.254.169.254")
        )


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/book.pdf", "gopher://example.com/"])
def test_rejects_non_http_schemes(url: str):
    with pytest.raises(UnsafeUrlError, match="not fetchable; use http or https"):
        validate_fetch_target(url, resolver=_PUBLIC)


@pytest.mark.parametrize("url", ["http://example.com:22/", "https://example.com:8080/", "https://example.com:6379/"])
def test_rejects_ports_outside_the_allowlist(url: str):
    with pytest.raises(UnsafeUrlError, match="is not fetchable; use 80 or 443"):
        validate_fetch_target(url, resolver=_PUBLIC)


def test_rejects_a_url_without_a_host():
    with pytest.raises(UnsafeUrlError, match="does not contain a host"):
        validate_fetch_target("https:///statics", resolver=_PUBLIC)


def test_rejects_an_unparsable_port():
    with pytest.raises(UnsafeUrlError, match="could not be parsed"):
        validate_fetch_target("https://example.com:notaport/", resolver=_PUBLIC)


def test_rejects_an_empty_resolution():
    with pytest.raises(UnsafeUrlError, match="did not resolve"):
        validate_fetch_target("https://example.com/", resolver=_resolver_returning())


def test_resolver_failure_becomes_an_unsafe_url_error(monkeypatch: pytest.MonkeyPatch):
    def fail(*args, **kwargs):
        raise socket.gaierror("no such host")

    monkeypatch.setattr("backend.rag.url_safety.socket.getaddrinfo", fail)
    with pytest.raises(UnsafeUrlError, match="could not be resolved"):
        resolve_host("nonexistent.invalid", 443)


def test_rejection_message_does_not_disclose_the_resolved_address():
    """The message reaches users through InputNormalizationError."""
    with pytest.raises(UnsafeUrlError) as error:
        validate_fetch_target("https://internal.example.com/", resolver=_resolver_returning("10.1.2.3"))
    assert "10.1.2.3" not in str(error.value)
