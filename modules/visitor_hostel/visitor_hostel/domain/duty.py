"""The VH duty roster (BR-VH-045..050).

The IAM decides who *may* act as Caretaker or VH In-Charge. The roster decides
which one of them is on duty, so a reassignment takes effect at once
(BR-VH-048) and open records follow the new holder (BR-VH-049/050).
"""
from __future__ import annotations

from datetime import datetime

CARETAKER = "caretaker"
INCHARGE = "incharge"
ROLES = (CARETAKER, INCHARGE)
LABELS = {CARETAKER: "Caretaker", INCHARGE: "VH In-Charge"}


class InvalidDutyWindow(Exception):
    pass


def validate_window(valid_from: datetime, valid_until: datetime) -> None:
    """BR-VH-047: every assignment ends, and ends after it starts."""
    if valid_until is None:
        raise InvalidDutyWindow("A duty assignment must have an end (BR-VH-047).")
    if valid_until <= valid_from:
        raise InvalidDutyWindow("A duty assignment must end after it starts.")


def is_current(valid_from: datetime, valid_until: datetime,
               ended_at: datetime | None, now: datetime) -> bool:
    return ended_at is None and valid_from <= now < valid_until
