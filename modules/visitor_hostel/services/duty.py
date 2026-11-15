"""Duty reassignment and record transfer (UC-VH-019, BR-VH-045..050).

Who may *perform* a reassignment is unresolved by the spec, so it is gated on
`visitor_hostel.duty.manage`, which no designation holds yet; operators use
`manage.py vh_assign_duty` until the institute names the authority.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError
from modules.visitor_hostel.domain import duty
from modules.visitor_hostel.domain import state_machine as sm
from modules.visitor_hostel.models import Booking, DutyAssignment

log = logging.getLogger("fusion.visitor_hostel.duty")


@dataclass(frozen=True)
class Reassignment:
    assignment: DutyAssignment
    previous_user_id: int | None
    pending_transferred: int
    ongoing_transferred: int


def _transfer(role: str, user_id: int) -> tuple[int, int]:
    """BR-VH-049 pending and BR-VH-050 ongoing records move to the new holder."""
    if role == duty.CARETAKER:
        field, pending, ongoing = ("caretaker_user_id", sm.CARETAKER_PENDING,
                                   sm.CARETAKER_ONGOING)
    else:
        field, pending, ongoing = ("incharge_user_id", sm.INCHARGE_PENDING,
                                   sm.INCHARGE_ONGOING)
    moved_pending = Booking.objects.filter(status__in=pending).update(**{field: user_id})
    moved_ongoing = Booking.objects.filter(status__in=ongoing).update(**{field: user_id})
    return moved_pending, moved_ongoing


@transaction.atomic
def assign(*, role: str, user_id: int, valid_until, valid_from=None,
           assigned_by_user_id: int | None = None, note: str = "") -> Reassignment:
    if role not in duty.ROLES:
        raise BadRequestError("Role must be caretaker or incharge.", code="invalid_role")
    now = timezone.now()
    valid_from = valid_from or now
    try:
        duty.validate_window(valid_from, valid_until)
    except duty.InvalidDutyWindow as exc:
        raise BadRequestError(str(exc), code="invalid_duty_window") from exc

    # The lock serialises two concurrent reassignments of the same role.
    open_rows = list(DutyAssignment.objects.select_for_update()
                     .filter(role=role, ended_at__isnull=True))
    previous = open_rows[0].user_id if open_rows else None
    for row in open_rows:
        row.ended_at = now
        row.save(update_fields=["ended_at"])

    assignment = DutyAssignment.objects.create(
        role=role, user_id=user_id, valid_from=valid_from, valid_until=valid_until,
        assigned_by_user_id=assigned_by_user_id, note=note)
    pending, ongoing = _transfer(role, user_id)
    log.info("visitor_hostel.duty.assigned role=%s from=%s to=%s pending=%d ongoing=%d",
             role, previous, user_id, pending, ongoing)
    return Reassignment(assignment, previous, pending, ongoing)


def close_lapsed(now=None) -> int:
    """Close assignments past their end, so the roster says what is true."""
    now = now or timezone.now()
    lapsed = DutyAssignment.objects.filter(ended_at__isnull=True, valid_until__lte=now)
    closed = 0
    for row in lapsed:
        row.ended_at = row.valid_until
        row.save(update_fields=["ended_at"])
        closed += 1
    if closed:
        log.warning("visitor_hostel.duty.lapsed count=%d — nobody is on duty for "
                    "the affected role until a new assignment is recorded", closed)
    return closed
