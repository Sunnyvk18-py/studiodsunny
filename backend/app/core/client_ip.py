"""Resolve the real client IP behind trusted reverse proxies."""

from __future__ import annotations

import ipaddress

from fastapi import Request

from app.core.config import settings


def _trusted_set() -> set[str]:
    raw = (settings.trusted_proxy_ips or "").strip()
    if not raw:
        return set()
    return {p.strip() for p in raw.split(",") if p.strip()}


def _is_trusted_peer(host: str | None, trusted: set[str]) -> bool:
    if not host or not trusted:
        return False
    if host in trusted:
        return True
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    for entry in trusted:
        try:
            if "/" in entry:
                if addr in ipaddress.ip_network(entry, strict=False):
                    return True
            elif addr == ipaddress.ip_address(entry):
                return True
        except ValueError:
            continue
    return False


def client_ip(request: Request | None) -> str:
    """Return client IP, honoring X-Forwarded-For only from trusted proxies.

    Without a trusted peer, XFF is ignored — otherwise any client could spoof
    the rate-limit bucket. When trusted, use the left-most (original client) hop.
    """
    if request is None:
        return "unknown"
    peer = request.client.host if request.client else None
    trusted = _trusted_set()
    if peer and _is_trusted_peer(peer, trusted):
        xff = request.headers.get("x-forwarded-for") or ""
        if xff.strip():
            # First hop is the original client when proxies append.
            return xff.split(",")[0].strip() or peer or "unknown"
    return peer or "unknown"
