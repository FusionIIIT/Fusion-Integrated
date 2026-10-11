"""Write authority, stated once (BR-EL-036).

A selector proves a row is *readable* — never that the caller may change it.
Every service write path calls `require`, and `actor_kind` says which lane of
the state machine the caller is in: the lane comes from the step the task
belongs to, not from the caller's title, because the configured route is what
decided whose queue this request is in (BR-EL-019).
"""
from __future__ import annotations

from core.api.exceptions import PermissionDeniedError
from modules.leave.domain import state_machine as sm


def require(actor, *codes: str) -> None:
    """Admit the actor, or raise PermissionDeniedError."""
    if actor is None:
        raise PermissionDeniedError("Authentication required.",
                                    code="not_authenticated")
    check = getattr(actor, "has_permission", None)
    if check is None or not any(check(c) for c in codes):
        raise PermissionDeniedError(
            f"This action needs {' or '.join(codes)}.", code="permission_denied")


def require_owner(actor, request) -> None:
    """The applicant-only actions: apply, withdraw, extension, resumption."""
    if getattr(actor, "user_id", None) != request.user_id:
        raise PermissionDeniedError(
            "Only the applicant may do this.", code="not_the_applicant")


def step_actor_kind(step_kind: str) -> str:
    """Which actor kind a routed step belongs to."""
    return {
        sm.UNIT_HEAD: sm.UNIT_HEAD,
        sm.ESTABLISHMENT: sm.ESTABLISHMENT,
        sm.SANCTION: sm.SANCTION,
    }.get(step_kind, sm.SANCTION)


def task_actor_kind(task) -> str:
    if task.step_kind == sm.SANCTION and task.authority == "director":
        return sm.DIRECTOR
    return step_actor_kind(task.step_kind)


def may_act(actor, task) -> bool:
    """Is this caller the assignee, or the holder of the routed office?

    A substitute task is assigned to one person; a routed office is held by
    whoever carries that designation, which is what the IAM reports in
    `principal.roles`.
    """
    own = getattr(actor, "user_id", None)
    if task.assignee_user_id is not None:
        return own == task.assignee_user_id
    return task.assignee_role in tuple(getattr(actor, "roles", ()) or ())
