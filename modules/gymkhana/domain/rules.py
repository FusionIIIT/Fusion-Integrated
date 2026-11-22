"""Gymkhana business rules as pure functions; services translate RuleViolation."""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal

TECHNICAL = "technical"
SPORTS = "sports"
CULTURAL = "cultural"
# BR-GYM-003
CATEGORIES = (TECHNICAL, SPORTS, CULTURAL)

MIN_CHOICES = 2
MAX_CHOICES = 10
MAX_TARGETS = 20
MAX_BOOKING_DAYS_AHEAD = 365
MIN_BATCH_YEAR = 2000
MAX_BATCH_YEAR = 2100
MAX_DISCIPLINE_LENGTH = 40


class RuleViolation(Exception):
    """A rule refused the input; `conflict` marks a clash with stored state, not bad input."""

    def __init__(self, code: str, message: str, *, conflict: bool = False,
                 field: str = ""):
        super().__init__(message)
        self.code = code
        self.message = message
        self.conflict = conflict
        self.field = field


def check_category(category: str) -> str:
    """BR-GYM-003: only Technical, Sports or Cultural."""
    value = (category or "").strip().lower()
    if value not in CATEGORIES:
        raise RuleViolation(
            "invalid_category",
            "Choose a category of Technical, Sports or Cultural.",
            field="category")
    return value


def check_distinct_leaders(coordinator: int, co_coordinator: int) -> None:
    """The coordinator and co-coordinator must be two different students."""
    if coordinator == co_coordinator:
        raise RuleViolation(
            "same_leader_twice",
            "The coordinator and the co-coordinator must be different students.",
            field="co_coordinator_user_id")


def check_time_range(start: time, end: time) -> None:
    """BR-GYM-005: a booking starts before it ends."""
    if not start < end:
        raise RuleViolation(
            "invalid_time_range",
            "The start time must be earlier than the end time.",
            field="end_time")


def check_booking_date(day: date, today: date) -> None:
    """A booking is for today or a later day, at most a year ahead."""
    if day < today:
        raise RuleViolation(
            "booking_in_past",
            "That date has already passed. Choose today or a later date.",
            conflict=True, field="date")
    if day > today + timedelta(days=MAX_BOOKING_DAYS_AHEAD):
        raise RuleViolation(
            "booking_too_far_ahead",
            f"Bookings can be made at most {MAX_BOOKING_DAYS_AHEAD} days ahead.",
            conflict=True, field="date")


def overlaps(a_start: time, a_end: time, b_start: time, b_end: time) -> bool:
    """Half-open intervals, so a slot ending at 11:00 does not clash with one starting at 11:00."""
    return a_start < b_end and b_start < a_end


@dataclass(frozen=True)
class Slot:
    booking_id: int
    start: time
    end: time


def find_conflict(start: time, end: time, existing: Iterable[Slot]) -> Slot | None:
    """BR-GYM-006: the first stored session or event the requested slot overlaps."""
    for slot in existing:
        if overlaps(start, end, slot.start, slot.end):
            return slot
    return None


def check_amount(amount: Decimal) -> None:
    """BR-GYM-017: a budget amount is zero or more."""
    if amount < 0:
        raise RuleViolation(
            "negative_amount",
            "The budget amount cannot be negative. Enter zero or more.",
            field="amount")


def check_choices(labels: Sequence[str]) -> list[str]:
    """BR-GYM-012: at least two distinct, non-empty choices."""
    cleaned = [(label or "").strip() for label in labels]
    if any(not label for label in cleaned):
        raise RuleViolation("empty_choice", "Every choice needs some text.",
                            field="choices")
    if len({label.casefold() for label in cleaned}) != len(cleaned):
        raise RuleViolation("duplicate_choice",
                            "Each choice must be different from the others.",
                            field="choices")
    if len(cleaned) < MIN_CHOICES:
        raise RuleViolation("too_few_choices",
                            "A poll needs at least two choices.", field="choices")
    if len(cleaned) > MAX_CHOICES:
        raise RuleViolation("too_many_choices",
                            f"A poll can have at most {MAX_CHOICES} choices.",
                            field="choices")
    return cleaned


@dataclass(frozen=True)
class Target:
    batch_year: int
    # Empty means every branch of the batch (BR-GYM-013 exception).
    discipline: str = ""


def check_targets(targets: Sequence[Target]) -> list[Target]:
    """BR-GYM-013: one or more batch/branch groups, each well formed and listed once."""
    if not targets:
        raise RuleViolation("no_targets",
                            "Choose at least one batch to address the poll to.",
                            field="targets")
    if len(targets) > MAX_TARGETS:
        raise RuleViolation("too_many_targets",
                            f"A poll can address at most {MAX_TARGETS} groups.",
                            field="targets")
    cleaned: list[Target] = []
    seen: set[tuple[int, str]] = set()
    for t in targets:
        discipline = (t.discipline or "").strip()
        if not MIN_BATCH_YEAR <= t.batch_year <= MAX_BATCH_YEAR:
            raise RuleViolation("invalid_target",
                                f"{t.batch_year} is not a batch year. Enter a year from "
                                f"{MIN_BATCH_YEAR} to {MAX_BATCH_YEAR}, such as 2023.",
                                field="targets")
        if len(discipline) > MAX_DISCIPLINE_LENGTH:
            raise RuleViolation("invalid_target",
                                "That branch name is too long.", field="targets")
        key = (t.batch_year, discipline.casefold())
        if key in seen:
            raise RuleViolation("duplicate_target",
                                "The same batch and branch is listed twice.",
                                field="targets")
        seen.add(key)
        cleaned.append(Target(t.batch_year, discipline))
    return cleaned


def check_expiry(expires_on: date, today: date) -> None:
    """A poll cannot be created already expired."""
    if expires_on < today:
        raise RuleViolation("expiry_in_past",
                            "The expiration date has already passed. Choose "
                            "today or a later date.", field="expires_on")


def poll_is_active(expires_on: date, today: date) -> bool:
    """BR-GYM-014: open through the whole of its expiration day."""
    return today <= expires_on


def in_audience(targets: Iterable[Target], batch_year: int | None,
                discipline: str) -> bool:
    """BR-GYM-013: whether a student's batch and branch fall in any target group."""
    if batch_year is None:
        return False
    branch = (discipline or "").strip().casefold()
    for t in targets:
        if t.batch_year != batch_year:
            continue
        if not t.discipline or (branch and t.discipline.casefold() == branch):
            return True
    return False


def check_event_held(event_at: datetime, now: datetime) -> None:
    """UC-GYM-010 precondition: a report is for an event that has taken place."""
    if event_at > now:
        raise RuleViolation("event_not_yet_held",
                            "A report can only be submitted for an event that "
                            "has already taken place.", conflict=True,
                            field="event_at")
