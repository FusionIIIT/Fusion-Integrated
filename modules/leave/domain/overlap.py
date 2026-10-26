"""Whether two leave intervals collide (BR-EL-012, BR-EL-014)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from modules.leave.domain.counting import FULL


@dataclass(frozen=True)
class Interval:
    start: date
    end: date
    half: str = FULL
    request_id: int | None = None


def collides(a: Interval, b: Interval) -> bool:
    """First-half and second-half of the same single date share it without colliding."""
    if a.end < b.start or b.end < a.start:
        return False
    same_day = a.start == a.end == b.start == b.end
    return not (same_day and a.half and b.half and a.half != b.half)


def first_collision(candidate: Interval, existing: list[Interval]) -> Interval | None:
    return next((e for e in existing if collides(candidate, e)), None)
