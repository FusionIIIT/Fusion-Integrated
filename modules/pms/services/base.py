"""Service plumbing: error translation, permission checks, locks and the status choke point."""
from __future__ import annotations

import functools
from collections.abc import Callable

from django.db.models import Model, QuerySet
from django.utils import timezone
from rest_framework import status

from core.api.exceptions import (
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.pms.domain import state_machine as sm
from modules.pms.domain.errors import InvalidInput, RuleViolation
from modules.pms.models import Application
from modules.pms.services import audit


class InvalidRequest(DomainError):
    code = "invalid"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


def ruled[F: Callable](fn: F) -> F:
    """Turn a domain refusal into the platform's error envelope, keeping its code and sentence."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except InvalidInput as exc:
            raise InvalidRequest(exc.message, code=exc.code) from exc
        except RuleViolation as exc:
            raise ConflictError(exc.message, code=exc.code) from exc
    return wrapper


def require(actor, *codes: str) -> None:
    """Write authority, checked again inside the service so a task or command cannot skip it."""
    if actor is None or getattr(actor, "user_id", None) is None:
        raise PermissionDeniedError("Sign in to use Patent Management.",
                                    code="not_authenticated")
    if not any(actor.has_permission(c) for c in codes):
        raise PermissionDeniedError("Your current role cannot do this. Switch to a role that "
                                    "can, or ask the PCC_ADMIN.", code="permission_denied")


def lock(scope: QuerySet, pk, what: str = "application") -> Model:
    """Lock one row inside the caller's scope; a row outside it is simply not found."""
    obj = scope.select_for_update(of=("self",)).filter(pk=pk).first()
    if obj is None:
        raise NotFoundError(f"No such {what}.", code="not_found")
    return obj


def lock_application(pk: int) -> Application:
    return Application.objects.select_for_update().get(pk=pk)


def move(app: Application, event: str, actor_kind: str, actor, *,
         details: dict | None = None, extra_fields: tuple[str, ...] = ()) -> str:
    """The only writer of Application.status (PMS-AFR-225); the caller holds the row lock."""
    t = sm.APPLICATION.resolve(app.status, event, actor_kind)
    frm, app.status = app.status, t.to
    app.save(update_fields=["status", "updated_at", *extra_fields])
    audit.record(actor, f"application.{event}", application=app, obj=app, frm=frm, to=t.to,
                 details=details)
    return frm


def move_record(machine: sm.Machine, obj: Model, event: str, actor_kind: str, actor, *,
                application: Application, details: dict | None = None,
                extra_fields: tuple[str, ...] = ()) -> str:
    """The only writer of each sub-record's status; the caller holds the row lock."""
    frm = obj.status if not obj._state.adding else sm.NEW
    t = machine.resolve(frm, event, actor_kind)
    obj.status = t.to
    if obj._state.adding:
        obj.save()
    else:
        obj.save(update_fields=["status", "updated_at", *extra_fields])
    audit.record(actor, f"{machine.name}.{event}", application=application, obj=obj, frm=frm,
                 to=t.to, details=details)
    return frm


def now():
    return timezone.now()


def today():
    return timezone.localdate()


def owner_only(actor, app: Application) -> None:
    if app.applicant_user_id != actor.user_id:
        raise PermissionDeniedError("Only the applicant who made this application can do this.",
                                    code="not_applicant")


def accepted_attorney_only(actor, app: Application) -> None:
    if not app.attorney_assignments.filter(attorney_user_id=actor.user_id,
                                           status=sm.ACCEPTED).exists():
        raise PermissionDeniedError("Only the attorney who accepted this case can do this.",
                                    code="not_assigned_attorney")


def inventor_ids(app: Application) -> list[int]:
    return [u for u in app.inventors.values_list("user_id", flat=True) if u is not None]


def conflicted(actor, app: Application) -> bool:
    """BR-PMS-027: an applicant or inventor never acts as the office on their own application."""
    return actor is not None and (actor.user_id == app.applicant_user_id
                                  or actor.user_id in inventor_ids(app))


def check_resolvable(machine: sm.Machine, frm: str, event: str, actor_kind: str) -> None:
    machine.resolve(frm, event, actor_kind)
