"""Scheduling domain validation (BR-GYM-005, BR-GYM-006, BR-GYM-020).

Pure Python: no Django/database dependencies.
"""
from __future__ import annotations

import datetime

from modules.gymkhana.domain.exceptions import (
    InvalidTimeRangeError,
    InvalidVenueError,
)

CONFIGURED_VENUES: frozenset[str] = frozenset({
    "L-101",
    "L-102",
    "L-201",
    "Audi",
    "SAC",
    "CR-101",
    "CR-102",
})


def validate_venue(venue: str) -> None:
    """Validate that the venue is one of the configured Gymkhana booking venues (BR-GYM-020)."""
    if not venue or venue.strip() not in CONFIGURED_VENUES:
        raise InvalidVenueError(venue)


def validate_time_slot(start_time: datetime.time, end_time: datetime.time) -> None:
    """Validate that booking start_time is strictly earlier than end_time (BR-GYM-005)."""
    if start_time is None or end_time is None:
        raise InvalidTimeRangeError("Both start time and end time are required.")
    if start_time >= end_time:
        raise InvalidTimeRangeError(
            f"Booking start time ({start_time}) must be strictly earlier "
            f"than end time ({end_time})."
        )


def check_slot_overlap(
    start_a: datetime.time,
    end_a: datetime.time,
    start_b: datetime.time,
    end_b: datetime.time,
) -> bool:
    """Check if time slot [start_a, end_a) overlaps with [start_b, end_b) (BR-GYM-006)."""
    return start_a < end_b and end_a > start_b
