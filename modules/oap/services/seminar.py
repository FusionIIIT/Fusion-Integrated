from __future__ import annotations

from datetime import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError
from modules.oap.domain import roles
from modules.oap.domain import state_machines as sm
from modules.oap.models import SeminarRequest, SeminarSchedule
from modules.oap.selectors import scoping
from modules.oap.services import notifications
from modules.oap.services.common import domain_guard, locked, need, need_role, record


def request(principal) -> SeminarRequest:
    need(principal, "oap.seminar_request.create")
    with transaction.atomic():
        req = SeminarRequest.objects.create(user_id=principal.user_id)
        record("seminar", req.pk, "", sm.SEMINAR_AWAITING, principal.user_id)
        notifications.notify(
            [principal.user_id],
            "Seminar scheduling requested",
            f"Your seminar scheduling request #{req.pk} is with the Department Administrator.",
        )
    return req


def schedule(principal, pk: int, *, scheduled_for: datetime, venue: str) -> SeminarSchedule:
    need(principal, "oap.seminar_schedule.update")
    need_role(principal, roles.DEPARTMENT_ADMIN)
    venue = (venue or "").strip()
    if not venue:
        raise BadRequestError("Enter the venue for the seminar.", code="venue_required")
    with transaction.atomic(), domain_guard():
        req = locked(scoping.seminar_requests_for(principal), pk, "Seminar request not found.")
        previous = req.status
        new_state = sm.next_state("seminar", previous, "schedule", "dept_admin")
        req.status = new_state
        req.save(update_fields=["status", "updated_at"])
        entry = SeminarSchedule.objects.create(
            request=req,
            scheduled_for=scheduled_for,
            venue=venue,
            scheduled_by_user_id=principal.user_id,
            scheduled_at=timezone.now(),
        )
        record("seminar", req.pk, previous, new_state, principal.user_id)
        notifications.notify(
            [req.user_id],
            "Graduate seminar scheduled",
            f"Your seminar is scheduled for {scheduled_for:%d %b %Y %H:%M} at {venue}.",
        )
    return entry
