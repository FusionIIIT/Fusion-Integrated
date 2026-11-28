"""Transactional state movement choke point."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.leave.domain.errors import InvalidLeaveTransitionError
from modules.leave.domain.state_machine import LeaveState, transition
from modules.leave.models import LeaveRequest, LeaveTransition, LedgerEntry, SlaClock


def advance_request_state(
    request_id: int,
    event: str,
    actor_user_id: int,
    actor_role: str,
    remark: str = "",
    workflow_ref: str = "",
) -> LeaveRequest:
    """Single transactional choke point for all workflow movement."""
    with transaction.atomic():
        try:
            req = LeaveRequest.objects.select_for_update().get(pk=request_id)
        except LeaveRequest.DoesNotExist:
            raise NotFoundError(f"Leave request #{request_id} does not exist.") from None

        from_state = req.state
        try:
            to_state = transition(from_state, event)
        except InvalidLeaveTransitionError as e:
            raise ConflictError(str(e)) from e

        req.state = to_state
        if to_state in (LeaveState.APPROVED, LeaveState.REJECTED):
            req.decided_at = timezone.now()
        req.save(update_fields=["state", "decided_at", "updated_at"])

        LeaveTransition.objects.create(
            request=req,
            from_state=from_state,
            to_state=to_state,
            event=event,
            actor_role=actor_role,
            actor_user_id=actor_user_id,
            remark=remark,
            workflow_ref=workflow_ref,
        )

        # Ledger effect on final approval (deduct) or cancellation (restore)
        if to_state == LeaveState.APPROVED and from_state != LeaveState.APPROVED:
            LedgerEntry.objects.create(
                user_id=req.user_id,
                year=req.starts_on.year,
                category=req.category,
                days=-abs(req.requested_days),
                reason="consumption",
                request_id=req.pk,
                note=f"Approved leave {req.pk}",
            )
        elif to_state == LeaveState.CANCELLED:
            LedgerEntry.objects.create(
                user_id=req.user_id,
                year=req.starts_on.year,
                category=req.category,
                days=abs(req.requested_days),
                reason="cancellation_reversal",
                request_id=req.pk,
                note=f"Cancelled leave {req.pk}",
            )

        # SLA clock update
        SlaClock.objects.update_or_create(
            request=req,
            defaults={"state": to_state, "entered_at": timezone.now()},
        )

        return req
