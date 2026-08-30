"""Moving a request through the workflow.

Every state change goes through `apply_event`. It refuses anything the
transition table does not contain, writes the trail, and lets the caller attach
balance movements to the same transaction. A state change and the ledger
entries it causes either both happen or neither does, so a balance can never
reflect a decision that was not recorded.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.leave.domain.state_machine import (
    Actor,
    Event,
    IllegalTransition,
    State,
    is_terminal,
    resolve,
)
from modules.leave.models import EntryReason, LeaveRequest, LedgerEntry, RequestTransition
from modules.leave.services import sla


@dataclass(frozen=True)
class Movement:
    """A balance change to record alongside a state change."""

    category: str
    days: Decimal
    reason: EntryReason
    note: str = ""


@transaction.atomic
def apply_event(
    request: LeaveRequest,
    event: Event,
    actor_role: Actor,
    *,
    actor_user_id: int | None = None,
    target: State | None = None,
    remark: str = "",
    movements: list[Movement] | None = None,
    on_applied: Callable[[LeaveRequest], None] | None = None,
) -> LeaveRequest:
    """Move the request, or refuse and change nothing."""
    locked = LeaveRequest.objects.select_for_update().get(pk=request.pk)
    source = State(locked.state)

    if is_terminal(source):
        raise ConflictError(
            f"This request is {source.value.lower()} and cannot be changed.",
            code="request_closed",
        )
    try:
        move = resolve(source, event, target)
    except IllegalTransition as exc:
        raise ConflictError(str(exc), code="illegal_transition") from exc
    if move.actor is not actor_role:
        raise ConflictError(
            f"{move.event.value} is performed by {move.actor.value}, not {actor_role.value}.",
            code="wrong_actor",
        )

    locked.state = move.target.value
    if is_terminal(move.target):
        locked.decided_at = timezone.now()
    locked.save(update_fields=["state", "decided_at", "updated_at"])

    RequestTransition.objects.create(
        request=locked,
        from_state=source.value,
        to_state=move.target.value,
        event=move.event.value,
        actor_role=move.actor.value,
        actor_user_id=actor_user_id,
        remark=remark,
        workflow_ref=move.workflow,
    )
    if movements:
        _record(locked, movements)
    # The clock belongs to the state, so it moves with it rather than being
    # something each caller has to remember to wind.
    sla.on_state_change(locked, move.target)
    if on_applied is not None:
        on_applied(locked)
    return locked


def _record(request: LeaveRequest, movements: list[Movement]) -> None:
    LedgerEntry.objects.bulk_create(
        [
            LedgerEntry(
                user_id=request.user_id,
                year=request.starts_on.year,
                category=m.category,
                days=m.days,
                reason=m.reason,
                request_id=request.pk,
                policy_id=request.policy_id,
                note=m.note,
            )
            for m in movements
        ]
    )


def trail(request: LeaveRequest) -> list[RequestTransition]:
    """Everything that has happened to this request, in order."""
    return list(request.transitions.order_by("id"))
