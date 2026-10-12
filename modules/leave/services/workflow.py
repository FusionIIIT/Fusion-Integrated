"""Shared workflow machinery: one place that moves a request, records the
event, and points the open task at whoever holds the next step (BR-EL-035).

Every status change in the module goes through `move`, so the audit trail
and the task/SLA state can never drift from the status itself.
"""
from __future__ import annotations

from django.utils import timezone

from modules.leave.domain import states as st
from modules.leave.models import LeaveRequest, LeaveRequestEvent, SlaThreshold
from modules.leave.services import authz, notifications
from modules.leave.services.errors import resolve_or_raise

#: status -> (SLA task class, the field holding whoever owns that step).
#: An applicant's own action (APPLICANT_ACTION) is deliberately absent:
#: there is no desk to remind, the notification already points at them.
TASK_FOR_STATUS: dict[str, tuple[str, str]] = {
    st.AWAITING_SUBSTITUTE: (SlaThreshold.SUBSTITUTE_RESPONSE,
                             "substitute_user_id"),
    st.AWAITING_UH_REVIEW: (SlaThreshold.UNIT_HEAD_REVIEW,
                            "unit_head_user_id"),
    st.AWAITING_ESTABLISHMENT: (SlaThreshold.ESTABLISHMENT_ROUTING,
                                "establishment_user_id"),
    st.AWAITING_FINAL: (SlaThreshold.FINAL_SANCTION, "authority_user_id"),
    st.AWAITING_DIRECTOR: (SlaThreshold.DIRECTOR_SANCTION, "user_id"),
}


def record_event(request: LeaveRequest, kind: str, *, frm: str = "",
                 to: str = "", actor=None, note: str = "") -> None:
    LeaveRequestEvent.objects.create(
        request=request, from_status=frm, to_status=to, kind=kind,
        actor_user_id=getattr(actor, "user_id", None),
        actor_label=str(getattr(actor, "display_name", "")
                        or getattr(actor, "username", "") or ""),
        note=note)


def close_task(request: LeaveRequest) -> None:
    """Nothing to remind about once a file has no open step."""
    request.task_class = ""
    request.task_user_id = None
    request.task_assigned_at = None
    request.reminder_sent_at = None
    request.escalated_at = None
    request.save(update_fields=["task_class", "task_user_id",
                                "task_assigned_at", "reminder_sent_at",
                                "escalated_at", "updated_at"])


def assign_task(request: LeaveRequest, *, actor=None, note: str = "") -> int | None:
    """(Re)point the open task at whoever holds this file's next step.

    Called after every status change; the old holder's reminder clock resets
    with the new assignment, which is what makes the SLA per-step rather than
    per-request.
    """
    spec = TASK_FOR_STATUS.get(request.status)
    if spec is None:
        close_task(request)
        return None
    task_class, field = spec
    holder = getattr(request, field, None)
    request.task_class = task_class
    request.task_user_id = holder
    request.task_assigned_at = timezone.now()
    request.reminder_sent_at = None
    request.escalated_at = None
    request.save(update_fields=["task_class", "task_user_id",
                                "task_assigned_at", "reminder_sent_at",
                                "escalated_at", "updated_at"])
    if holder is not None:
        notifications.notify(
            holder, "assigned",
            f"A leave request ({request.category.upper()} "
            f"{request.start_date.isoformat()}…{request.end_date.isoformat()}) "
            f"needs your action: {task_class.replace('_', ' ')}.",
            request)
    record_event(request, LeaveRequestEvent.ASSIGNMENT, actor=actor,
                 note=note or f"task → {task_class}")
    return holder


def move(request: LeaveRequest, to_status: str, *, actor, actor_kind: str,
         permission: str, guards: tuple[str, ...] = (),
         note: str = "") -> LeaveRequest:
    """The one legal way to change a request's status.

    `guards` are the conditions the caller has already evaluated; the state
    machine re-checks that the edge exists *with those guards*, so a service
    cannot, for example, approve a Unit-Head-final file through the
    establishment edge by mislabelling its outcome.
    """
    transition = resolve_or_raise(request.status, to_status, actor_kind)
    missing = set(transition.guards) - set(guards)
    if missing:
        from core.api.exceptions import ConflictError
        raise ConflictError(
            f"This request cannot move to '{to_status}' yet.",
            code="guard_not_satisfied",
            details=[{"from": request.status, "to": to_status,
                      "unsatisfied": sorted(missing)}])
    authz.require(actor, permission)
    frm = request.status
    request.status = to_status
    request.save(update_fields=["status", "updated_at"])
    record_event(request, LeaveRequestEvent.STATUS_CHANGE, frm=frm,
                 to=to_status, actor=actor, note=note)
    assign_task(request, actor=actor)
    return request
