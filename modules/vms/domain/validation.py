from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta

SUPPORTED_ID_TYPES = frozenset(
    {"passport", "national_id", "driving_license", "voter_id", "other_government_id"}
)


class RuleViolation(ValueError):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


def validate_visit_window(
    *,
    starts_at: datetime,
    ends_at: datetime,
    now: datetime,
    maximum: timedelta,
    advance_window: timedelta,
) -> None:
    if starts_at <= now:
        raise RuleViolation("Choose a future visit start time.", "visit_start_past")
    if ends_at <= starts_at:
        raise RuleViolation("The visit end must be after its start.", "invalid_visit_window")
    if ends_at - starts_at > maximum:
        raise RuleViolation(
            "The visit exceeds the published maximum duration.", "visit_duration_exceeded"
        )
    if starts_at - now < advance_window:
        raise RuleViolation(
            "This visit needs the same-day urgent approval path.", "urgent_approval_required"
        )


def validate_walk_in_window(*, starts_at: datetime, ends_at: datetime, maximum: timedelta) -> None:
    if ends_at <= starts_at or ends_at - starts_at > maximum:
        raise RuleViolation(
            "The walk-in pass duration is outside the published limit.", "walk_in_duration_invalid"
        )


def blacklist_match(*, name: str, fingerprint: str, entries: Iterable[tuple[str, str]]) -> bool:
    normalized_name = " ".join(name.casefold().split())
    return any(
        (candidate_hash and candidate_hash == fingerprint)
        or (candidate_name and " ".join(candidate_name.casefold().split()) == normalized_name)
        for candidate_name, candidate_hash in entries
    )


def zones_allowed(requested: Iterable[str], permitted: Iterable[str]) -> bool:
    return set(requested).issubset(set(permitted))
