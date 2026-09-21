"""In-code Destination Guard for ECDAT network probes.

Enforces air-gap compliance: live network probes (TLS, SSH, etc.) are strictly
restricted to localhost and approved local docker test containers.
Attempts to probe external domains, public IPs, or arbitrary hosts are
immediately rejected before any network traffic is initiated.
"""

from __future__ import annotations

import os

# Approved destination hosts: localhost and standard test harness containers.
DEFAULT_ALLOWED_HOSTS: frozenset[str] = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "::1",
        "test-target-legacy-tls",
        "test-target-modern-tls",
        "test-target-legacy-ssh",
        "localstack",
    }
)


class SecurityException(Exception):
    """Raised when an unauthorized destination is targeted for probing."""

    pass


def get_allowed_hosts() -> set[str]:
    """Return the set of allowed probe hosts, combining defaults with any
    explicit environment overrides (ECDAT_ALLOWED_PROBE_HOSTS)."""
    allowed = set(DEFAULT_ALLOWED_HOSTS)
    env_hosts = os.getenv("ECDAT_ALLOWED_PROBE_HOSTS", "").strip()
    if env_hosts:
        for host in env_hosts.split(","):
            cleaned = host.strip().lower()
            if cleaned:
                allowed.add(cleaned)
    return allowed


def is_allowed_host(host: str) -> bool:
    """Check if a host is permitted by the air-gap guardrail."""
    normalized = host.strip().lower()
    return normalized in get_allowed_hosts()


def validate_probe_destination(host: str) -> None:
    """Validate that the destination host is strictly within the allowed set.

    Raises:
        SecurityException: If host is not permitted by air-gap guardrail policy.
    """
    if not is_allowed_host(host):
        raise SecurityException(
            f"Probe destination '{host}' is rejected: air-gap policy strictly restricts "
            f"probing to localhost and approved test containers."
        )
