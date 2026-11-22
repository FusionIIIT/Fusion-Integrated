# Pure domain validation logic for Gymkhana

from collections.abc import Sequence
from datetime import time
from decimal import Decimal

from modules.gymkhana.domain.constants import CONFIGURED_VENUES


def validate_booking_time_range(start_time: time, end_time: time) -> None:
    if start_time >= end_time:
        raise ValueError("Booking start time must be earlier than end time.")


def validate_venue(venue: str) -> None:
    if venue not in CONFIGURED_VENUES:
        raise ValueError(f"Venue {venue!r} is not a configured Gymkhana venue.")


def validate_poll_choices(choices: Sequence[str]) -> None:
    if len(choices) < 2:
        raise ValueError("A voting poll must have at least two choices.")
    cleaned = [c.strip() for c in choices if c and c.strip()]
    if len(cleaned) < 2:
        raise ValueError("A voting poll must have at least two non-empty choices.")


def validate_budget_amount(amount: Decimal | float | int) -> None:
    if Decimal(str(amount)) < Decimal("0"):
        raise ValueError("Budget request amount must be non-negative.")
