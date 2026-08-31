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
from modules.leave.models import (
    EntryReason,
    LeaveRequest,
    LedgerEntry,
    RequestTransition,
    YearEndClosure,
)
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
    _refuse_self_decision(locked, source, move, actor_role, actor_user_id)

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
    sla.on_state_change(locked, move.target, source)
    if on_applied is not None:
        on_applied(locked)
    return locked


def _refuse_self_decision(
    request: LeaveRequest,
    source: State,
    move,
    actor_role: Actor,
    actor_user_id: int | None,
) -> None:
    """Nobody decides their own leave.

    A unit head is an employee too, and their own request lands in the queue
    they work from. Without this a head could approve their own leave, and an
    establishment officer could route and sanction theirs, with the trail
    showing an approval that looks exactly like any other.

    The one exception is written into the workflow rather than assumed: the
    self-sanction route (BR-EL-020) exists so that the Director's own leave has
    somewhere to go. It is reached only from a state the authority
    configuration put the request in.
    """
    if actor_user_id is None or actor_user_id != request.user_id:
        return
    if actor_role in (Actor.EMPLOYEE, Actor.SCHEDULER):
        return                              # their own request, their own action
    if source is State.AWAITING_SELF_SANCTION:
        return                              # BR-EL-020, deliberately

    raise ConflictError(
        "You cannot decide your own leave request. It has to be actioned by "
        "somebody else in the approval path.",
        code="self_decision",
    )


def _record(request: LeaveRequest, movements: list[Movement]) -> None:
    year = request.starts_on.year
    if YearEndClosure.objects.filter(user_id=request.user_id, year=year).exists():
        # The year has been lapsed, converted and carried forward. Booking into
        # it now changes a balance the next year's opening was computed from,
        # and nothing recomputes that opening -- the correction has to be a
        # deliberate one, not a side effect of approving a December request in
        # January.
        raise ConflictError(
            f"{year} has been closed for this employee, so nothing further can "
            "be charged to it. The leave administrator has to settle this "
            "against the closed year explicitly.",
            code="year_already_closed",
        )
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
