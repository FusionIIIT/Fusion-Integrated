"""Pure Python domain validations for Gymkhana."""

from __future__ import annotations

import datetime
import re
from collections.abc import Sequence
from decimal import Decimal

from modules.gymkhana.domain.constants import (
    ALL_GROUPS,
    ALLOWED_CLUB_CATEGORIES,
    CLUB_STATUS_CONFIRMED,
    MAX_UPLOAD_BYTES,
)
from modules.gymkhana.domain.exceptions import DomainValidationError

MAX_BRANCH_LENGTH = 50
_BATCH = re.compile(r"^\d{4}$")

# Content a browser or shell would execute, whatever the file is called.
_ACTIVE_CONTENT = (
    b"<!doctype html",
    b"<html",
    b"<script",
    b"<svg",
    b"<?xml",
    b"#!",
    b"mz\x90",
    b"\x7felf",
)


def validate_club_category(category: str) -> str:
    """Technical, Sports or Cultural only (BR-GYM-003, AFR-GYM-004)."""
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
    """The start precedes the end (BR-GYM-005, AFR-GYM-011)."""
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
    """At least two distinct choices (BR-GYM-012, AFR-GYM-024)."""
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
    """The amount is zero or more (BR-GYM-017, AFR-GYM-030)."""
    dec = Decimal(str(amount))
    if dec < Decimal("0"):
        raise DomainValidationError("Budget request amount must be non-negative.")
    return dec


def validate_file_present(has_file: bool, field_name: str) -> None:
    """The required file is there (BR-GYM-018, BR-GYM-019, AFR-GYM-030, AFR-GYM-033)."""
    if not has_file:
        raise DomainValidationError(f"The required supporting file for {field_name} is missing.")


def validate_target_groups(groups: Sequence[tuple[str, str]]) -> list[tuple[str, str]]:
    """Normalise the selected batch and branch groups, refusing unusable ones (BR-GYM-013)."""
    if not groups:
        raise DomainValidationError("Select at least one batch and branch group for this poll.")
    clean: list[tuple[str, str]] = []
    for raw_batch, raw_branch in groups:
        batch, branch = raw_batch.strip(), raw_branch.strip()
        batch = ALL_GROUPS if batch.lower() == ALL_GROUPS else batch
        branch = ALL_GROUPS if branch.lower() == ALL_GROUPS else branch
        if batch != ALL_GROUPS and not _BATCH.match(batch):
            raise DomainValidationError(f"Batch '{batch}' must be a four digit year or 'all'.")
        if not branch or len(branch) > MAX_BRANCH_LENGTH:
            raise DomainValidationError("Select a branch, or 'all' branches, for every group.")
        if (batch, branch) not in clean:
            clean.append((batch, branch))
    return clean


def validate_event_has_occurred(
    event_date: datetime.datetime, current_time: datetime.datetime
) -> None:
    """A report documents an event that has already taken place (UC-GYM-010)."""
    if event_date > current_time:
        raise DomainValidationError("A report can only be submitted after the event has occurred.")


def validate_not_own_application(applicant_id: int, approver_id: int) -> None:
    """Nobody decides their own membership application (BR-GYM-010)."""
    if applicant_id == approver_id:
        raise DomainValidationError(
            "You cannot approve your own application. Ask the other Club Head to review it."
        )


def validate_upload(*, name: str, size: int, head: bytes, extensions: Sequence[str]) -> None:
    """Accept only an allowed, non-empty, bounded file with no active content."""
    extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if extension not in extensions:
        raise DomainValidationError(f"Upload one of these file types: {', '.join(extensions)}.")
    if size <= 0:
        raise DomainValidationError("The uploaded file is empty.")
    if size > MAX_UPLOAD_BYTES:
        raise DomainValidationError("The uploaded file must be 5 MB or smaller.")
    if head.lstrip(b"\xef\xbb\xbf \t\r\n").lower().startswith(_ACTIVE_CONTENT):
        raise DomainValidationError("The uploaded file contains content that is not allowed.")
