"""Registration requests (BR-MMS-008/009/010; UC-002/003/004; BW-MMS-01/02).

One transactional choke point per state change: `select_for_update`, refuse a
terminal source state, refuse the wrong actor, write the audit trail and emit
the notification — all in one transaction.
"""

from __future__ import annotations

import contextlib

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.mms.domain import state_machine as sm
from modules.mms.domain.exceptions import ActorNotAllowed, GuardFailed, InvalidTransition
from modules.mms.models import Registration, RegistrationWindow
from modules.mms.selectors import scoping
from modules.mms.services import authz, notifications


def open_window(actor, cycle_or_period: str, opens_at, closes_at, now=None) -> RegistrationWindow:
    """BR-MMS-008: only the active Caretaker opens a registration window."""
    authz.require(actor, "mms.registration.window.manage")
    now = now or timezone.now()
    if closes_at <= opens_at:
        raise GuardFailed("window_info_complete", "The window must close after it opens.")
    return RegistrationWindow.objects.create(
        cycle_or_period=cycle_or_period,
        opens_at=opens_at,
        closes_at=closes_at,
        is_open=True,
        opened_by_user_id=actor.user_id,
    )


def submit(actor) -> Registration:
    """BR-MMS-009: a Student may submit only while the window is open."""
    authz.require(actor, "mms.registration.create")
    now = timezone.now()
    window = (
        RegistrationWindow.objects.filter(is_open=True, opens_at__lte=now, closes_at__gte=now)
        .select_for_update()
        .first()
    )
    if window is None:
        raise GuardFailed("window_open", "No registration window is open right now.")
    own = actor.user_id
    with transaction.atomic():
        if Registration.objects.filter(user_id=own, status="pending").exists():
            raise ConflictError("You already have a pending registration request.")
        reg = Registration.objects.create(user_id=own, status="pending", submitted_at=now)
        with contextlib.suppress(InvalidTransition):
            sm.resolve("window_open", "registration_pending", sm.STUDENT)
        notifications.enqueue(
            topic="registration.submitted",
            dedupe_key=f"registration.submitted:u{own}:{reg.pk}",
            subject="Mess registration request received",
            body=f"Your registration request ({reg.pk}) has been recorded "
            f"and is pending Caretaker decision.",
            recipient_user_id=own,
        )
    return reg


def decide(actor, pk: int, approve: bool, reason: str = "") -> Registration:
    """BR-MMS-010: only the active Caretaker approves or rejects; no second
    decision once decided."""
    authz.require(actor, "mms.registration.review")
    to_status = "registration_approved" if approve else "registration_rejected"
    try:
        sm.resolve("registration_pending", to_status, sm.CARETAKER)
    except (InvalidTransition, ActorNotAllowed) as exc:
        raise ConflictError(str(exc)) from exc
    with transaction.atomic():
        reg = (
            scoping.registration_requests_for(actor)
            .filter(pk=pk, status="pending")
            .select_for_update()
            .first()
        )
        if reg is None:
            raise NotFoundError("No pending registration request with that id.")
        reg.status = "approved" if approve else "rejected"
        reg.decided_at = timezone.now()
        reg.decided_by_user_id = actor.user_id
        reg.save(update_fields=["status", "decided_at", "decided_by_user_id", "updated_at"])
        topic = "registration.decided"
        notifications.enqueue(
            topic=topic,
            dedupe_key=f"registration.decided:u{reg.user_id}:{reg.pk}",
            subject=("Mess registration " + ("approved" if approve else "rejected")),
            body=(
                "Your mess registration request "
                + ("was approved" if approve else "was rejected")
                + (f". {reason}" if reason else "")
            ),
            recipient_user_id=reg.user_id,
        )
    return reg
