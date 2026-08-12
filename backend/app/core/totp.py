"""TOTP helpers for HQ 2FA."""

from __future__ import annotations

import pyotp


def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="Studio Sunny HQ")


def verify_totp(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code.strip().replace(" ", ""), valid_window=1)
