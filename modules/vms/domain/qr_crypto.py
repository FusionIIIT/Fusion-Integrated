"""Pure python deterministic QR token generator and verifier.

ZERO framework imports allowed here.
"""

from __future__ import annotations

import hashlib
import hmac

_VMS_SALT = "fusion-vms-salt-2026"


def generate_qr_token(pass_number: str, secret_key: str | None = None) -> str:
    """Generate tamper-proof HMAC SHA-256 token for digital pass QR code."""
    key = (secret_key or _VMS_SALT).encode("utf-8")
    token = hmac.new(
        key,
        pass_number.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"VMS-{pass_number}-{token[:16]}"


def verify_qr_token(token: str, secret_key: str | None = None) -> tuple[bool, str]:
    """Verify QR code token authenticity and extract pass number."""
    if not token or not token.startswith("VMS-"):
        return False, ""

    rem = token[4:]
    if "-" not in rem:
        return False, ""

    pass_number, _ = rem.rsplit("-", 1)
    expected_token = generate_qr_token(pass_number, secret_key)
    if hmac.compare_digest(token, expected_token):
        return True, pass_number
    return False, ""
