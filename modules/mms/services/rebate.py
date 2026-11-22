"""Rebate requests (BR-MMS-021..025; UC-014/015; BW-MMS-05/06/07)."""

from __future__ import annotations

import contextlib

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.mms.domain import rules
from modules.mms.domain import state_machine as sm
from modules.mms.domain.exceptions import ActorNotAllowed, GuardFailed, InvalidTransition
from modules.mms.models import RebateRequest
from modules.mms.selectors import scoping
from modules.mms.services import authz, notifications


def submit(actor, reason: str, explanation: str, start_date, end_date) -> RebateRequest:
    """BR-MMS-021..024: validate then record a Pending rebate request."""
    authz.require(actor, "mms.rebate.create")
    own = actor.user_id
    submitted_on = timezone.localdate()
    existing = list(
        RebateRequest.objects.filter(user_id=own, status__in=("pending", "approved")).values_list(
            "start_date", "end_date"
        )
    )
    try:
        rules.rebate_valid(reason, explanation, start_date, end_date, submitted_on, existing)
    except GuardFailed as exc:
        raise ConflictError(exc.message) from exc
    with transaction.atomic():
        rebate = RebateRequest.objects.create(
            user_id=own,
            reason=reason,
            explanation=explanation,
            start_date=start_date,
            end_date=end_date,
            status="pending",
            submitted_at=timezone.now(),
        )
        with contextlib.suppress(InvalidTransition):
            sm.resolve("no_rebate", "rebate_pending", sm.STUDENT)
        notifications.enqueue(
            topic="rebate.submitted",
            dedupe_key=f"rebate.submitted:u{own}:{rebate.pk}",
            subject="Mess rebate request received",
            body=f"Your rebate request ({rebate.pk}) has been recorded and "
            f"is pending Caretaker decision.",
            recipient_user_id=own,
        )
    return rebate


def decide(
    actor,
    pk: int,
    approve: bool,
    approved_start_date=None,
    approved_end_date=None,
    reason: str = "",
) -> RebateRequest:
    """BR-MMS-025: Caretaker approves/rejects; may modify dates before
    approval only where external policy permits (no range invented here)."""
    authz.require(actor, "mms.rebate.review")
    to_status = "rebate_approved" if approve else "rebate_rejected"
    if approve:
        perm = "mms.rebate.review"
        if approved_start_date or approved_end_date:
            perm = "mms.rebate.update"
    authz.require(actor, perm)
    try:
        sm.resolve("rebate_pending", to_status, sm.CARETAKER)
    except (InvalidTransition, ActorNotAllowed) as exc:
        raise ConflictError(str(exc)) from exc
    with transaction.atomic():
        rebate = (
            scoping.rebate_requests_for(actor)
            .filter(pk=pk, status="pending")
            .select_for_update()
            .first()
        )
        if rebate is None:
            raise NotFoundError("No pending rebate request with that id.")
        rebate.status = "approved" if approve else "rejected"
        rebate.decided_at = timezone.now()
        rebate.decided_by_user_id = actor.user_id
        if approve:
            rebate.approved_start_date = approved_start_date or rebate.start_date
            rebate.approved_end_date = approved_end_date or rebate.end_date
        rebate.save(
            update_fields=[
                "status",
                "decided_at",
                "decided_by_user_id",
                "approved_start_date",
                "approved_end_date",
                "updated_at",
            ]
        )
        notifications.enqueue(
            topic="rebate.decided",
            dedupe_key=f"rebate.decided:u{rebate.user_id}:{rebate.pk}",
            subject=("Mess rebate " + ("approved" if approve else "rejected")),
            body=(
                "Your mess rebate request "
                + ("was approved" if approve else "was rejected")
                + (f". {reason}" if reason else "")
            ),
            recipient_user_id=rebate.user_id,
        )
    return rebate
