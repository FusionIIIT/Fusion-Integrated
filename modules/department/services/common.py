"""Shared service plumbing: domain errors become HTTP errors here, never in domain/."""

from __future__ import annotations

from contextlib import contextmanager

from core.api.exceptions import ConflictError, DomainError, NotFoundError, PermissionDeniedError
from modules.department.domain.errors import ActorNotAllowed, InvalidTransition, RuleViolation
from modules.department.domain.roles import CENTRAL, DEPT_ADMIN, FACULTY, HOD, STUDENT, ActorContext
from modules.department.models import Department


@contextmanager
def translated():
    try:
        yield
    except RuleViolation as exc:
        raise DomainError(exc.message, code=exc.code, details=exc.details) from exc
    except InvalidTransition as exc:
        raise ConflictError(str(exc), code="invalid_transition") from exc
    except ActorNotAllowed as exc:
        raise PermissionDeniedError(str(exc), code="actor_not_allowed") from exc


def own_department(ctx: ActorContext, *, lock: bool = False) -> Department:
    """The actor's department row, or a refusal that says how to get one."""
    if ctx.department is None:
        raise DomainError(
            "You are not attached to a department in this role. Ask the academic office to "
            "record your department or your tenure.",
            code="no_department",
        )
    qs = Department.objects.select_for_update() if lock else Department.objects
    dept = qs.filter(code=ctx.department).first()
    if dept is None:
        raise DomainError(
            f"Department {ctx.department} has not been set up yet. Run seed_departments.",
            code="department_missing",
        )
    return dept


def get_scoped(queryset, pk, *, lock: bool = False, what: str = "record"):
    qs = queryset.select_for_update(of=("self",)) if lock else queryset
    row = qs.filter(pk=pk).first()
    if row is None:
        raise NotFoundError(f"That {what} does not exist or is not visible to you.")
    return row


_ROLE_NAMES = {
    STUDENT: "Student",
    FACULTY: "Faculty",
    HOD: "HOD",
    DEPT_ADMIN: "Dept_Admin",
    CENTRAL: "Institute Admin",
}


def require_acting(ctx: ActorContext, *roles: str) -> None:
    """The IAM sends every held role's permissions, so the acting role is checked here too."""
    if ctx.role not in roles:
        names = " or ".join(_ROLE_NAMES[r] for r in roles)
        raise PermissionDeniedError(
            f"Only someone acting as {names} can do this. Switch your role and try again.",
            code="wrong_acting_role",
        )
