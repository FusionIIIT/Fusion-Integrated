"""All reads. Ownership filtering lives HERE — once per module, not once per
view — which is why a foreign id naturally yields 404 instead of 403.

Nothing in here authorises; a selector decides what you can SEE. Whether you
may act on it is `services/workflow.py`, and which lane you act in is
`domain/routing.py`.
"""
from __future__ import annotations

from modules.leave.models import LeaveRequest, LeaveTask

#: Stale substitute requests: a nominee who has not answered yet.
OPEN_RESPONSES = ("", "declined")


def my_requests(principal, *, kind: str | None = None):
    qs = LeaveRequest.objects.filter(user_id=principal.user_id)
    if kind:
        qs = qs.filter(kind=kind)
    return qs.select_related("parent")


def visible_requests(principal):
    """Every leave request, for a designation that holds `.application.view`.

    There is no department scope to narrow here: a Unit Head sees their own
    unit's work through their task inbox, which is the narrower and more
    honest question. A holder of `.view` is a leave administrator or an
    authority, and the institute's leave record is theirs to see.
    """
    qs = LeaveRequest.objects.all()
    if principal.has_permission("leave.application.view"):
        return qs
    return qs.filter(user_id=principal.user_id)


def visible_children(principal, parent: LeaveRequest):
    """The amendments on a leave — extensions, cancellations, resumptions."""
    return visible_requests(principal).filter(parent=parent)


def task_inbox(principal):
    """Actionable work assigned to this person.

    Role-addressed stages (Establishment, final sanction) have no single
    assignee, so they are not in anyone's inbox: the permission gate is the
    authority there, and the sweep still clocks them for SLA.
    """
    return (LeaveTask.objects
            .filter(assignee_user_id=principal.user_id, status="pending")
            .select_related("request")
            .order_by("reminder_due_at", "created_at"))


def substitution_requests(principal):
    """What this person has been nominated for and has not settled."""
    return (LeaveRequest.objects
            .filter(substitute_user_id=principal.user_id,
                    substitute_response__in=OPEN_RESPONSES,
                    status="awaiting_substitute")
            .order_by("from_date"))


def substitute_request_by_id(principal, pk: int):
    """The one request this person is the nominee on.

    A substitute is not granted `.application.view`, so their row is reached by
    nomination rather than by ownership — which is also why answering it is a
    permission of its own (`leave.substitute.respond`).
    """
    return (LeaveRequest.objects
            .filter(pk=pk, substitute_user_id=principal.user_id)
            .select_related("parent")
            .first())


def request_by_id(principal, pk: int):
    """Scope first, then fetch: a foreign request is absent, hence a 404."""
    return visible_requests(principal).filter(pk=pk).first()


def my_request_by_id(principal, pk: int):
    return my_requests(principal).filter(pk=pk).first()


def open_tasks_for_request(request: LeaveRequest, *, stage: str | None = None):
    qs = LeaveTask.objects.filter(request=request, status="pending")
    if stage:
        qs = qs.filter(stage=stage)
    return qs
