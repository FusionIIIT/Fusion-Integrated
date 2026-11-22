"""Pure Python retention policy evaluation and expiry logic for BADMS.

Evaluates retention durations and expiration dates based on authoritative classifications.
"""
from __future__ import annotations

from datetime import datetime, timedelta


class RetentionPolicyError(Exception):
    def __init__(self, message: str):
        super().__init__(
            f"{message} Review configured classification retention rules before retrying."
        )


DEFAULT_RETENTION_DAYS: dict[str, int] = {
    "Routine": 30,
    "Sensitive": 365,
    "Critical": 2555,  # 7 years
    "Archival": 3650,  # 10 years
}


def resolve_retention_duration(classification: str, policy_override_days: int | None = None) -> int:
    if policy_override_days is not None and policy_override_days > 0:
        return policy_override_days
    duration = DEFAULT_RETENTION_DAYS.get(classification)
    if duration is None:
        raise RetentionPolicyError(f"Unknown data classification {classification!r}.")
    return duration


def calculate_retention_expiry(
    created_at: datetime,
    classification: str,
    policy_override_days: int | None = None,
) -> datetime:
    duration_days = resolve_retention_duration(classification, policy_override_days)
    return created_at + timedelta(days=duration_days)


def is_retention_expired(
    created_at: datetime,
    classification: str,
    now: datetime,
    policy_override_days: int | None = None,
) -> bool:
    expiry = calculate_retention_expiry(created_at, classification, policy_override_days)
    return now >= expiry
