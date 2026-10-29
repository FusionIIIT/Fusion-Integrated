"""Write authority for leave, stated once. Every service write path calls it.

A permission code proves the caller holds a capability; it never proves the row
in hand is one they may act on. Ownership and task assignment are checked here
so an endpoint cannot grant a decision to whoever holds the code.
"""
from __future__ import annotations

from core.api.exceptions import NotFoundError, PermissionDeniedError
from modules.leave.models.requests import TASK_PENDING

P_VIEW_SELF = "leave.request.view_self"
P_CREATE = "leave.request.create"
P_DELETE = "leave.request.delete"
P_VIEW = "leave.request.view"
P_APPROVE = "leave.request.approve"
P_BALANCE_UPDATE = "leave.balance.update"
P_TYPE_MANAGE = "leave.type.manage"
P_SUBSTITUTE_RESPOND = "leave.substitute.respond"
P_RECORD_MAINTAIN = "leave.record.maintain"


def require(actor, *codes: str) -> None:
    if actor is None:
        raise PermissionDeniedError("Authentication required.",
                                    code="not_authenticated")
    check = getattr(actor, "has_permission", None)
    if check is None or not any(check(c) for c in codes):
        raise PermissionDeniedError(
            f"This action needs {' or '.join(codes)}.", code="permission_denied")


def own_id(actor) -> int | None:
    return getattr(actor, "user_id", None)


def is_owner(actor, obj) -> bool:
    own = own_id(actor)
    return own is not None and getattr(obj, "user_id", None) == own


def require_owner(actor, obj, *, message: str = "") -> None:
    if not is_owner(actor, obj):
        raise NotFoundError(message or "Not found.")


def require_assignee(actor, task) -> None:
    """A decision belongs to the person the task names, not to anyone holding
    `leave.request.approve` (BR-EL-036)."""
    if task.assignee_user_id != own_id(actor):
        raise NotFoundError("Not found.")


def require_pending(task) -> None:
    if task.status != TASK_PENDING:
        raise PermissionDeniedError(
            "This task has already been dealt with.", code="task_not_pending")


def require_draft(request_obj) -> None:
    """Only a draft may be edited or deleted (BR-EL-034)."""
    from modules.leave.domain import state_machine as sm

    if request_obj.status != sm.DRAFT:
        raise PermissionDeniedError(
            "Only a draft can be changed or deleted.", code="not_draft")