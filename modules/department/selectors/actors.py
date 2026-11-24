"""Resolve the acting role and its department once per request."""

from __future__ import annotations

from django.utils import timezone

from modules.department.domain.roles import (
    CENTRAL,
    FACULTY,
    STUDENT,
    ActorContext,
    normalise_department,
    office_department,
    role_of,
)
from modules.department.models import RoleTenure
from modules.directory import contracts as directory


def holds_tenure(*, user_id: int, role: str, department_code: str, now=None) -> bool:
    """Q1: the designation gives the verb, an in-effect tenure gives the rows (BR-DEPT-024)."""
    now = now or timezone.now()
    return RoleTenure.objects.filter(
        user_id=user_id,
        role=role,
        department__code=department_code,
        valid_from__lte=now,
        valid_to__gt=now,
    ).exists()


def context_for(principal, *, now=None) -> ActorContext:
    """Fail closed: an unknown role or an unresolvable department gets no rows."""
    if principal is None:
        return ActorContext(user_id=None, role=None, department=None)
    user_id = getattr(principal, "user_id", None)
    active = getattr(principal, "active_role", None)
    role = role_of(active, getattr(principal, "kind", None))
    if role is None or user_id is None:
        return ActorContext(user_id=user_id, role=role, department=None)
    if role == CENTRAL:
        return ActorContext(user_id=user_id, role=role, department=None)
    if role in (STUDENT, FACULTY):
        user = directory.get_users([user_id]).get(user_id)
        if user is None:
            return ActorContext(user_id=user_id, role=role, department=None)
        raw = user.discipline if role == STUDENT else user.department
        return ActorContext(
            user_id=user_id,
            role=role,
            department=normalise_department(raw),
            programme=user.programme or "",
            batch_year=user.batch_year,
        )
    code = office_department(active)
    if code and holds_tenure(user_id=user_id, role=role, department_code=code, now=now):
        return ActorContext(user_id=user_id, role=role, department=code)
    return ActorContext(user_id=user_id, role=role, department=None)


def current_holders(department_ids, role: str, *, now=None) -> dict[int, int]:
    """department id -> user id of the tenure in effect now (AFR-DEPT-053)."""
    now = now or timezone.now()
    rows = RoleTenure.objects.filter(
        department_id__in=list(department_ids), role=role, valid_from__lte=now, valid_to__gt=now
    )
    return {r.department_id: r.user_id for r in rows}
