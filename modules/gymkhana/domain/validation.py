"""Pure Python domain validations for Gymkhana."""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from decimal import Decimal

from modules.gymkhana.domain.constants import (
    ALLOWED_CLUB_CATEGORIES,
    CLUB_STATUS_CONFIRMED,
)
from modules.gymkhana.domain.exceptions import DomainValidationError


def validate_club_category(category: str) -> str:
    """Ensure category is Technical, Sports, or Cultural (BR-GYM-003)."""
    norm = category.strip().lower()
    if norm not in ALLOWED_CLUB_CATEGORIES:
        raise DomainValidationError(
            f"Invalid club category '{category}'. Must be one of {ALLOWED_CLUB_CATEGORIES}"
        )
    return norm


def validate_distinct_leaders(coordinator_id: int, co_coordinator_id: int) -> None:
    """Ensure coordinator and co-coordinator are different student accounts."""
    if coordinator_id == co_coordinator_id:
        raise DomainValidationError("Coordinator and Co-coordinator must be distinct users.")


def validate_booking_times(start_time: datetime.time, end_time: datetime.time) -> None:
    """Ensure booking start time precedes end time (BR-GYM-005)."""
    if start_time >= end_time:
        raise DomainValidationError(
            f"Start time ({start_time}) must be strictly before end time ({end_time})."
        )


def validate_venue(venue: str, configured_venues: Sequence[str]) -> str:
    """Ensure booking venue is configured (BR-GYM-020)."""
    clean = venue.strip()
    if not clean or clean not in configured_venues:
        raise DomainValidationError(f"Venue '{venue}' is not in configured venues list.")
    return clean


def validate_club_is_confirmed(status: str) -> None:
    """Ensure membership applications are only for confirmed clubs (BR-GYM-007)."""
    if status != CLUB_STATUS_CONFIRMED:
        raise DomainValidationError(
            "Membership applications can only be submitted for confirmed clubs."
        )


def validate_poll_choices(choices: Sequence[str]) -> list[str]:
    """Ensure poll has at least two non-empty distinct choices (BR-GYM-012)."""
    cleaned = [c.strip() for c in choices if c and c.strip()]
    if len(cleaned) < 2:
        raise DomainValidationError("Poll must have at least two choices.")
    if len(set(cleaned)) != len(cleaned):
        raise DomainValidationError("Poll choices must be distinct.")
    return cleaned


def validate_poll_active(
    expires_at: datetime.datetime, current_time: datetime.datetime | None = None
) -> None:
    """Ensure poll has not expired (BR-GYM-014)."""
    now = current_time or datetime.datetime.now(datetime.UTC)
    if expires_at <= now:
        raise DomainValidationError("This voting poll has expired.")


def validate_budget_amount(amount: Decimal | float | int) -> Decimal:
    """Ensure budget request amount is non-negative (BR-GYM-017)."""
    dec = Decimal(str(amount))
    if dec < Decimal("0"):
        raise DomainValidationError("Budget request amount must be non-negative.")
    return dec


def validate_file_present(has_file: bool, field_name: str) -> None:
    """Ensure mandatory file attachment is present (BR-GYM-018, BR-GYM-019)."""
    if not has_file:
        raise DomainValidationError(f"The required supporting file for {field_name} is missing.")
