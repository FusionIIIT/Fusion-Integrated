"""Deregistration requests (BR-MMS-012/013; UC-005/006/027; BW-MMS-03/04)."""

from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.mms.domain import state_machine as sm
from modules.mms.domain.exceptions import ActorNotAllowed, InvalidTransition
from modules.mms.models import Deregistration
from modules.mms.selectors import scoping
from modules.mms.services import authz, notifications


def submit(actor) -> Deregistration:
    """BR-MMS-012: a registered Student may deregister at any time."""
    authz.require(actor, "mms.deregistration.create")
    own = actor.user_id
    now = timezone.now()
    with transaction.atomic():
        if Deregistration.objects.filter(user_id=own, status="pending").exists():
            raise ConflictError("You already have a pending deregistration request.")
        dereg = Deregistration.objects.create(user_id=own, status="pending", submitted_at=now)
        notifications.enqueue(
            topic="deregistration.submitted",
            dedupe_key=f"deregistration.submitted:u{own}:{dereg.pk}",
            subject="Mess deregistration request received",
            body=f"Your deregistration request ({dereg.pk}) has been "
            f"recorded and is pending Caretaker decision.",
            recipient_user_id=own,
        )
    return dereg


def decide(actor, pk: int, approve: bool, reason: str = "") -> Deregistration:
    """BR-MMS-010: only the active Caretaker approves or rejects; an approved
    deregistration becomes effective the next calendar day (BR-MMS-013,
    UC-027)."""
    authz.require(actor, "mms.deregistration.review")
    to_status = "deregistration_approved_awaiting_date" if approve else "deregistration_rejected"
    try:
        sm.resolve("deregistration_pending", to_status, sm.CARETAKER)
    except (InvalidTransition, ActorNotAllowed) as exc:
        raise ConflictError(str(exc)) from exc
    with transaction.atomic():
        dereg = (
            scoping.deregistration_requests_for(actor)
            .filter(pk=pk, status="pending")
            .select_for_update()
            .first()
        )
        if dereg is None:
            raise NotFoundError("No pending deregistration request with that id.")
        dereg.status = "approved_awaiting_effective_date" if approve else "rejected"
        dereg.decided_at = timezone.now()
        dereg.decided_by_user_id = actor.user_id
        if approve:
            dereg.effective_date = timezone.localdate() + timedelta(days=1)
        dereg.save(
            update_fields=[
                "status",
                "decided_at",
                "decided_by_user_id",
                "effective_date",
                "updated_at",
            ]
        )
        notifications.enqueue(
            topic="deregistration.decided",
            dedupe_key=f"deregistration.decided:u{dereg.user_id}:{dereg.pk}",
            subject=("Mess deregistration " + ("approved" if approve else "rejected")),
            body=(
                "Your mess deregistration request "
                + ("was approved" if approve else "was rejected")
                + (f". {reason}" if reason else "")
            ),
            recipient_user_id=dereg.user_id,
        )
    return dereg


def activate_approved() -> int:
    """UC-027 / BR-MMS-013: make approved deregistrations effective from the
    next calendar day. Idempotent."""
    today = timezone.localdate()
    due = Deregistration.objects.filter(
        status="approved_awaiting_effective_date", effective_date__lte=today
    )
    count = 0
    for dereg in due:
        dereg.status = "student_deregistered"
        dereg.save(update_fields=["status", "updated_at"])
        count += 1
    return count
