"""Pure timetable overlap rule for the Department module."""

from collections.abc import Iterable
from datetime import time
from typing import Protocol, TypedDict


class SlotLike(Protocol):
    day: int
    room: str
    starts_at: time
    ends_at: time


class CandidateSlot(TypedDict):
    day: int
    room: str
    starts_at: time
    ends_at: time


def has_room_overlap(
    existing_slots: Iterable[SlotLike], candidate: CandidateSlot,
) -> bool:
    """Return True when a same-room, same-day interval overlaps the candidate.

    Intervals that only touch at an endpoint are allowed. This simple
    same-room rule is the module's documented first-version interpretation.
    """
    for existing in existing_slots:
        if existing.day == candidate["day"] and existing.room == candidate["room"]:
            if (existing.starts_at < candidate["ends_at"]
                    and existing.ends_at > candidate["starts_at"]):
                return True
    return False
