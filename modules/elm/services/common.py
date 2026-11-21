"""Shared plumbing: error translation, audit events and notifications."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import (
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.elm.domain.errors import RuleViolation
from modules.elm.domain.workflow import TASK_OWNER, check_move
from modules.elm.models import LeaveApplication, LeaveEvent, LeaveNotification
from modules.elm.selectors import applications as sel

PERMISSION_FOR_OWNER = {
    "unit_head": "elm.leave.review",
    "establishment": "elm.leave.route",
    "sanction": "elm.leave.sanction",
    "director": "elm.leave.self_sanction",
}


class RuleBroken(DomainError):
    code = "rule_violation"
    message = "A leave rule prevents this."


@contextmanager
def enforcing_rules() -> Iterator[None]:
    """Turn the pure domain's RuleViolation into an API-ready error."""
    try:
        yield
    except RuleViolation as exc:
        raise RuleBroken(str(exc), details=[{"rule": exc.rule}]) from exc


def load(pk: int, *, lock: bool = True) -> LeaveApplication:
    found = sel.application(pk, lock=lock)
    if found is None:
        raise NotFoundError("Application not found.")
    return found


def require_owner(principal, application: LeaveApplication) -> None:
    if application.user_id != principal.user_id:
        raise NotFoundError("Application not found.")


def require_permission(principal, code: str) -> None:
    if not principal.has_permission(code):
        raise PermissionDeniedError()


def require_status(application: LeaveApplication, *allowed: str) -> None:
    if application.status not in allowed:
        raise ConflictError(
            f"This application is {application.status}; that action needs "
            f"{' or '.join(sorted(allowed))}.", code="wrong_state")


def move(application: LeaveApplication, to: str, *, action: str, actor_id: int | None,
         note: str = "", first: bool = False, role: str = "") -> LeaveEvent:
    """Change state, restart the SLA clock and leave a trail.

    When a role is given the move must be one the workflow allows that role to make.
    """
    if role:
        with enforcing_rules():
            check_move(application.status, to, role)
    event = LeaveEvent.objects.create(
        application=application, action=action,
        from_status="" if first else application.status,
        to_status=to, actor_user_id=actor_id, note=note[:300])
    application.status = to
    application.waiting_since = timezone.now()
    application.reminded_at = None
    application.escalated_at = None
    return event


def notify(application: LeaveApplication, topic: str, message: str, *,
           user_id: int | None = None, permission: str = "", key: str) -> None:
    if user_id is None and not permission:
        return
    try:
        with transaction.atomic():
            LeaveNotification.objects.create(
                recipient_user_id=user_id, recipient_permission=permission, topic=topic,
                message=message[:300], application=application,
                dedupe_key=f"app{application.pk}:{key}:{topic}:{user_id or permission}")
    except IntegrityError:
        return


def announce_task(application: LeaveApplication, key: str) -> None:
    """Tell whoever now owns the next step (BR-EL-015, BR-EL-017)."""
    owner = TASK_OWNER.get(application.status)
    label = f"{application.leave_type} {application.start_date}..{application.end_date}"
    if application.status == "AWAITING_SUBSTITUTE":
        notify(application, "leave.substitute_requested",
               f"You were named substitute for a leave: {label}.",
               user_id=application.substitute_user_id, key=key)
    elif owner in PERMISSION_FOR_OWNER:
        what = ("A resumption needs verification"
                if application.status == "RESUMPTION_PENDING" else "A leave needs your action")
        notify(application, "leave.task", f"{what}: {label}.",
               permission=PERMISSION_FOR_OWNER[owner], key=key)
