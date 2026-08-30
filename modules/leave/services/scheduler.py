"""Moving leave along as the calendar does, with nobody clicking anything.

Approved leave has to start on its start date, reach its end date, and open for
resumption, and none of those are decisions -- they are the passage of time.
Nothing invoked them, so an approved request stayed APPROVED_NOT_STARTED for
ever: it never became ONGOING, so it could still be cancelled after the
employee had already gone; extension, which is only reachable while the leave
runs, could never be requested at all; and resumption never opened, so nothing
ever closed and no balance was ever restored.

Every move still goes through the transition table like any other, with
SCHEDULER as the actor, so the trail shows what the clock did as plainly as
what a person did.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from django.db import transaction

from core.api.exceptions import ConflictError
from modules.leave.domain.state_machine import State
from modules.leave.models import LeaveRequest
from modules.leave.services import lifecycle

log = logging.getLogger("fusion.leave.scheduler")


@dataclass(frozen=True)
class AdvanceReport:
    started: int = 0
    ended: int = 0
    failed: int = 0

    @property
    def moved(self) -> int:
        return self.started + self.ended


def due_to_begin(on: date) -> list[LeaveRequest]:
    """Approved leave whose first day has arrived."""
    return list(
        LeaveRequest.objects.filter(
            state=State.APPROVED_NOT_STARTED.value, starts_on__lte=on
        ).order_by("starts_on", "id")
    )


def due_to_end(on: date) -> list[LeaveRequest]:
    """Running leave whose last day has passed."""
    return list(
        LeaveRequest.objects.filter(
            state=State.ONGOING.value, ends_on__lt=on
        ).order_by("ends_on", "id")
    )


def advance(on: date | None = None) -> AdvanceReport:
    """One pass over everything the calendar has caught up with.

    Each request moves in its own transaction: one that cannot move -- a policy
    withdrawn underneath it, say -- must not hold up the rest of the institute.
    """
    on = on or date.today()
    started = ended = failed = 0

    for request in due_to_begin(on):
        try:
            with transaction.atomic():
                lifecycle.begin(request=request)
            started += 1
        except ConflictError as exc:
            failed += 1
            log.warning("leave.begin_failed request=%s %s", request.pk, exc.message)

    for request in due_to_end(on):
        try:
            with transaction.atomic():
                lifecycle.await_resumption(request=request)
            ended += 1
        except ConflictError as exc:
            failed += 1
            log.warning("leave.end_failed request=%s %s", request.pk, exc.message)

    if started or ended:
        log.info("leave.advanced started=%d ended=%d failed=%d", started, ended, failed)
    return AdvanceReport(started=started, ended=ended, failed=failed)
