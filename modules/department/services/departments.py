"""Department details: general updates (UC-DEPT-010) and official changes (CW-DEPT-03)."""

from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.department.domain import rules
from modules.department.domain import state_machine as sm
from modules.department.domain.roles import DEPT_ADMIN, ActorContext
from modules.department.models import Department, OfficialChange
from modules.department.selectors import scoping
from modules.department.services.common import (
    get_scoped,
    own_department,
    require_acting,
    translated,
)


@transaction.atomic
def update_general(ctx: ActorContext, code: str, **fields) -> Department:
    """AFR-DEPT-038: general fields only; an official field is refused, never silently saved."""
    require_acting(ctx, DEPT_ADMIN)
    dept = scoping.departments_for(ctx).select_for_update().filter(code=code).first()
    if dept is None:
        raise NotFoundError("That department does not exist or is not yours.")
    with translated():
        rules.check_general_update(fields)
    for field, value in fields.items():
        setattr(dept, field, value)
    dept.save()
    return dept


@transaction.atomic
def propose(ctx: ActorContext, *, field: str, value: str) -> OfficialChange:
    """UC-DEPT-010 official branch: pending, not published (BR-DEPT-011, AFR-DEPT-039)."""
    with translated():
        sm.resolve("official change", sm.NONE, sm.CHANGE_PENDING, ctx.role)
    dept = own_department(ctx, lock=True)
    with translated():
        rules.validate_official_change(field, value)
    try:
        with transaction.atomic():
            return OfficialChange.objects.create(
                department=dept,
                field=field,
                proposed_value=value,
                previous_value=getattr(dept, field),
                proposed_by=ctx.user_id,
            )
    except IntegrityError as exc:
        raise ConflictError(
            f"A change to {field} is already waiting for the HOD; wait for that decision.",
            code="change_pending",
        ) from exc


@transaction.atomic
def decide(ctx: ActorContext, change_id: int, *, approve: bool, reason: str = "") -> OfficialChange:
    """UC-DEPT-012: BR-DEPT-013; approval publishes, rejection keeps current data (AFR-DEPT-040)."""
    change = get_scoped(
        scoping.official_changes_for(ctx), change_id, lock=True, what="official change"
    )
    target = sm.CHANGE_APPROVED if approve else sm.CHANGE_REJECTED
    with translated():
        sm.resolve("official change", change.status, target, ctx.role)
    if approve:
        dept = Department.objects.select_for_update().get(pk=change.department_id)
        setattr(dept, change.field, change.proposed_value)
        dept.save()
    change.status, change.decided_by, change.decided_at, change.reason = (
        target,
        ctx.user_id,
        timezone.now(),
        reason,
    )
    change.save()
    return change
