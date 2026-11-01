"""Super Admin shared business rules (pure Python: no Django, no DRF, no database).

Covers BR-SA-026, 028, 029, 030 and 032. Rules raise RuleViolation(code, message);
a service translates it to an HTTP error.
"""
from __future__ import annotations

from collections.abc import Iterable


class RuleViolation(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


ALLOWED_CHANNELS = frozenset({"email", "in_app", "sms"})
BULK_HARD_MAX = 1000

# Keys that would indicate operational content the Super Admin must never see.
FORBIDDEN_CONTENT_KEYS = frozenset({
    "marks", "grades", "fees", "salary", "prescription",
    "complaint", "document", "submission", "request",
})


def check_not_self_modification(actor_user_id: int, target_user_id: int) -> None:
    """BR-SA-028: a Super Admin cannot change their own Super Admin status."""
    if actor_user_id == target_user_id:
        raise RuleViolation("self_modification",
                            "A Super Admin cannot modify their own status.")


def require_reauth(confirmed: bool) -> None:
    """BR-SA-029: critical operations need authenticated confirmation."""
    if not confirmed:
        raise RuleViolation("reauth_required",
                            "Authenticated confirmation is required for this operation.")


def check_bulk_limit(count: int, limit: int, hard_max: int = BULK_HARD_MAX) -> None:
    """BR-SA-030: a bulk operation may not exceed the configured limit (max 1000)."""
    effective = min(limit, hard_max)
    if count > effective:
        raise RuleViolation("bulk_limit_exceeded",
                            f"A bulk operation is limited to {effective} records.")


def check_channel(channel: str, critical: bool = False) -> None:
    """BR-SA-032: email and in-system always; SMS only for critical security alerts."""
    if channel not in ALLOWED_CHANNELS:
        raise RuleViolation("bad_channel", f"Unsupported channel {channel!r}.")
    if channel == "sms" and not critical:
        raise RuleViolation("bad_channel",
                            "SMS is allowed only for critical security alerts.")


def check_no_operational_content(keys: Iterable[str]) -> None:
    """BR-SA-026: archive/export payloads may carry metadata only."""
    hits = sorted({k for k in keys if k.lower() in FORBIDDEN_CONTENT_KEYS})
    if hits:
        raise RuleViolation("data_isolation",
                            f"Operational content is not permitted: {', '.join(hits)}.")
