"""Time-bound Caretaker/Warden assignment and active-role authorization."""
from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.directory import contracts as directory
from modules.mms.models import RoleAssignment


def is_active_role(user_id: int, role: str, *, at=None) -> bool:
    at = at or timezone.now()
    return RoleAssignment.objects.filter(
        user_id=user_id, role=role, is_current=True, starts_at__lte=at,
        ends_at__gt=at).exists()


def require_role(actor, role: str) -> None:
    from core.api.exceptions import PermissionDeniedError

    if not is_active_role(actor.user_id, role):
        raise PermissionDeniedError(
            f"Only the active Mess {role.title()} may perform this action.",
            code="active_role_required")


def current_assignments():
    now = timezone.now()
    return {
        role: RoleAssignment.objects.filter(
            role=role, is_current=True, starts_at__lte=now, ends_at__gt=now).first()
        for role, _ in RoleAssignment.ROLE
    }


@transaction.atomic
def assign(*, actor, role: str, user_id: int, starts_at=None, ends_at=None):
    from core.api.exceptions import ConflictError

    if not isinstance(role, str) or role not in {"caretaker", "warden"}:
        raise ConflictError("Role must be caretaker or warden.", code="invalid_role")
    now = timezone.now()
    starts_at = starts_at or now
    if ends_at is None:
        raise ConflictError("Assignment must have an end time.",
                            code="invalid_assignment_period")
    if starts_at > ends_at:
        raise ConflictError("Assignment must end after it starts.",
                            code="invalid_assignment_period")
    if ends_at <= now:
        raise ConflictError("Assignment must end in the future.",
                            code="invalid_assignment_period")
    employee = directory.get_users([user_id]).get(user_id)
    is_employee = user_id in directory.held_employee_ids()
    if employee is None or not is_employee:
        raise ConflictError("Select an active institute employee from the directory.",
                            code="employee_not_found")
    current = list(RoleAssignment.objects.select_for_update().filter(
        role=role, is_current=True).order_by("-starts_at"))
    effective_now = starts_at <= now
    for row in current:
        if effective_now:
            overlaps = row.starts_at < ends_at and row.ends_at > starts_at
        else:
            overlaps = row.starts_at < ends_at and row.ends_at > starts_at
        if overlaps and row.user_id != user_id:
            raise ConflictError("A current assignment for this role already exists.",
                                code="assignment_conflict")
    if effective_now:
        for row in current:
            if row.user_id != user_id:
                continue
            row.ends_at = starts_at
            row.is_current = False
            row.save(update_fields=["ends_at", "is_current", "updated_at"])
        RoleAssignment.objects.filter(
            role=role, is_current=True, starts_at__lte=now, ends_at__gt=now
        ).exclude(user_id=user_id).update(ends_at=now, updated_at=now)
        RoleAssignment.objects.filter(role=role, is_current=True).exclude(
            user_id=user_id).update(is_current=False, updated_at=now)
    try:
        with transaction.atomic():
            return RoleAssignment.objects.create(
                role=role, user_id=user_id, starts_at=starts_at, ends_at=ends_at,
                is_current=effective_now, assigned_by_user_id=actor.user_id)
    except IntegrityError as exc:
        raise ConflictError("A current assignment for this role already exists.",
                            code="assignment_conflict") from exc
