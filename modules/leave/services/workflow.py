"""Every state change in this module goes through `move()`.

One function, because the alternative — a check in each view — is how a rule
ends up enforced on four endpoints and missing on the fifth. `move()` does five
things in one transaction:

    resolve   the edge in the state machine, for THIS permission and lane
    authorise does the caller hold it, and may they act on THIS row
    record    an append-only LeaveApproval row
    hand over supersede the finished task, open the next one, clock the SLA
    stage     which lane acted, so the audit trail says who did what

The caller then applies whatever the decision MEANS — a deduction, a restored
balance, an extended end date — as an effect on top, in the same transaction.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.leave.domain import guards as guard_table
from modules.leave.domain import state_machine as sm
from modules.leave.domain.guards import Facts
from modules.leave.models import LeaveApproval, LeaveRequest, LeaveTask
from modules.leave.services import notifications

log = logging.getLogger("fusion.leave.workflow")

#: Permissions whose exercise is a DECISION about somebody else's leave.
#: Holding one of these on your own request is exactly the self-approval the
#: Director-specific path exists to permit, and nothing else does.
DECISION_PERMISSIONS = frozenset({
    "leave.request.review",
    "leave.request.route",
    "leave.request.approve",
    "leave.resumption.review",
})

#: permission -> the lane of the state machine that exercises it.
LANES = {
    "leave.application.create": sm.EMPLOYEE,
    "leave.application.withdraw": sm.EMPLOYEE,
    "leave.application.cancel": sm.EMPLOYEE,
    "leave.application.extend": sm.EMPLOYEE,
    "leave.substitute.nominate": sm.EMPLOYEE,
    "leave.resumption.submit": sm.EMPLOYEE,
    "leave.substitute.respond": sm.SUBSTITUTE,
    "leave.request.review": sm.UNIT_HEAD,
    "leave.request.route": sm.ESTABLISHMENT,
    "leave.request.approve": sm.AUTHORITY,
    "leave.resumption.review": sm.AUTHORITY,
}

#: Resulting state -> the task it needs, and whose it is.
STAGE_FOR_STATE = {
    sm.AWAITING_SUBSTITUTE: ("substitute", "substitute_user_id"),
    sm.AWAITING_UNIT_HEAD: ("unit_head", "unit_head_user_id"),
    sm.AWAITING_ESTABLISHMENT: ("establishment", None),
    sm.AWAITING_FINAL: ("final", None),
    sm.AWAITING_SELF_SANCTION: ("self_sanction", "user_id"),
    sm.RESUMPTION_PENDING: ("final", "unit_head_user_id"),
}

STAGE_FOR_LANE = {
    sm.EMPLOYEE: "employee",
    sm.SUBSTITUTE: "substitute",
    sm.UNIT_HEAD: "unit_head",
    sm.ESTABLISHMENT: "establishment",
}


def lane_for(permission: str) -> str:
    try:
        return LANES[permission]
    except KeyError as exc:
        raise LookupError(
            f"No actor lane is declared for permission {permission!r}.") from exc


def stage_for(lane: str, request: LeaveRequest) -> str:
    """The audit trail's name for the lane that acted."""
    if lane == sm.AUTHORITY:
        return "self_sanction" if request.self_sanction else "final"
    return STAGE_FOR_LANE[lane]


def require(principal, permission: str, request: LeaveRequest | None = None,
            *, allow_self: bool = False) -> None:
    """The fine gate. Scope is the selector's job, done before we get here."""
    if not principal.has_permission(permission):
        raise PermissionDeniedError(
            "You do not have permission to perform this action.",
            code="permission_denied")
    if (request is not None and permission in DECISION_PERMISSIONS
            and not allow_self and request.user_id == principal.user_id):
        raise PermissionDeniedError(
            "You cannot take a decision on your own leave request.",
            code="self_approval")


def _resolve(*, request: LeaveRequest, permission: str, facts: Facts):
    """The table, with its errors translated into ones the API can render."""
    lane = lane_for(permission)
    try:
        return guard_table.select(frm=request.status, permission=permission,
                                  facts=facts, actor_kind=lane)
    except guard_table.GuardFailed as exc:
        raise ConflictError(
            _message_for(exc.guard), code="guard_failed",
            details=[{"guard": exc.guard, "state": request.status,
                      "allowed": sm.allowed_targets(request.status, lane)}]) from exc
    except sm.InvalidTransition as exc:
        raise ConflictError(
            f"This request is {exc.frm.replace('_', ' ')} and can no longer "
            f"take that action.", code="invalid_transition",
            details=[{"state": exc.frm,
                      "allowed": sm.allowed_targets(exc.frm, lane)}]) from exc
    except sm.ActorNotAllowed as exc:
        raise PermissionDeniedError("Your role cannot make that change.",
                                    code="actor_not_allowed") from exc


def _message_for(guard: str) -> str:
    """Guard names are for the table; the person holding the request needs a
    sentence."""
    return {
        "substitute_required": "This request is still waiting for the substitute's consent.",
        "no_substitute_required": "No substitute is nominated for this request.",
        "consent_accepted": "The substitute has not accepted yet.",
        "consent_declined": "The substitute has not declined this request.",
        "replacement_eligible": "Nominate an eligible replacement substitute.",
        "applicant_is_director": "This request is not a Director self-sanction.",
        "applicant_not_director": "A Director's own leave follows the self-sanction path.",
        "unit_head_final": "That decision belongs to the final sanctioning authority.",
        "higher_sanction": "This leave needs the full sanctioning path, not a Unit Head decision.",
        "establishment_configured": "No Establishment step is configured, so "
                                     "this goes straight to the final authority.",
        "decision_approve": "Record an approval to complete this action.",
        "decision_reject": "Record a rejection to complete this action.",
        "pre_start": "This leave has already begun, so it can no longer be cancelled.",
        "leave_ongoing": "Only leave currently in effect can be extended.",
        "extension_eligible": "This leave category cannot be extended.",
        "leave_started": "The leave has not begun yet.",
        "resumption_eligible": "Resumption review applies to EL, COL and VL.",
        "not_final": "This request has already been decided.",
    }.get(guard, f"The request does not satisfy {guard.replace('_', ' ')}.")


def _open_task(request: LeaveRequest, stage: str, assignee_id, policy) -> None:
    """Hand the work over, and start the SLA clock (BR-EL-035/038)."""
    task = LeaveTask.objects.create(
        request=request, stage=stage, assignee_user_id=assignee_id)
    if policy is not None:
        now = timezone.now()
        task.reminder_due_at = now + timedelta(hours=policy.reminder_hours)
        task.escalation_due_at = now + timedelta(hours=policy.escalation_hours)
        task.save(update_fields=["reminder_due_at", "escalation_due_at"])
    notifications.tell_the_assignee(
        task, "A leave request needs your attention",
        f"{request.get_category_display()} {request.from_date} to {request.to_date}.")


def _supersede(request: LeaveRequest, *, stage: str | None = None) -> None:
    """A stage that has been passed can no longer be acted on — which is what
    makes "no reminder for a task that is no longer pending" a fact rather
    than a promise (BR-EL-032/033)."""
    qs = LeaveTask.objects.filter(request=request, status="pending")
    if stage:
        qs = qs.filter(stage=stage)
    qs.update(status="superseded", actioned_at=timezone.now())


def _hand_over(request: LeaveRequest, to_state: str, policy) -> None:
    _supersede(request)
    spec = STAGE_FOR_STATE.get(to_state)
    if spec is None:
        return
    stage, attr = spec
    assignee = getattr(request, attr) if attr else None
    _open_task(request, stage, assignee, policy)


@transaction.atomic
def move(*, request: LeaveRequest, principal, permission: str, facts: Facts,
         decision: str = "", remarks: str = "", policy=None) -> LeaveRequest:
    """Take the one transition this caller, this permission and these facts
    allow, and record everything that follows from it."""
    lane = lane_for(permission)
    require(principal, permission, request, allow_self=bool(request.self_sanction))
    transition = _resolve(request=request, permission=permission, facts=facts)

    frm = request.status
    request.status = transition.to
    if decision:
        request.decision = decision
        request.decision_remarks = remarks
        request.decided_by_user_id = principal.user_id
        request.decided_at = timezone.now()
    request.save(update_fields=["status", "decision", "decision_remarks",
                                "decided_by_user_id", "decided_at", "updated_at"])

    LeaveApproval.objects.create(
        request=request, stage=stage_for(lane, request),
        decision=decision or transition.to,
        actor_user_id=principal.user_id, remarks=remarks)
    _hand_over(request, transition.to, policy)

    log.info("leave.%s %s -> %s by %s (%s)", request.pk, frm, transition.to,
             principal.user_id, permission)
    return request
