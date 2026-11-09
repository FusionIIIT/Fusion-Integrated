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
def assign(*, actor, role: str, user_id: int, ends_at):
    from core.api.exceptions import ConflictError

    if not isinstance(role, str) or role not in {"caretaker", "warden"}:
        raise ConflictError("Role must be caretaker or warden.", code="invalid_role")
    now = timezone.now()
    if ends_at <= now:
        raise ConflictError("Assignment must end in the future.",
                            code="invalid_assignment_period")
    employee = directory.get_users([user_id]).get(user_id)
    from modules.directory.models import UserRef

    identity_is_current = UserRef.objects.filter(
        user_id=user_id, is_active=True, kind__in=("faculty", "staff")).exists()
    if employee is None or not identity_is_current:
        raise ConflictError("Select an active institute employee from the directory.",
                            code="employee_not_found")
    list(RoleAssignment.objects.select_for_update().filter(
        role=role, is_current=True).values_list("pk", flat=True))
    RoleAssignment.objects.filter(
        role=role, is_current=True, starts_at__lte=now, ends_at__gt=now
    ).update(ends_at=now, updated_at=now)
    RoleAssignment.objects.filter(role=role, is_current=True).update(
        is_current=False, updated_at=now)
    try:
        with transaction.atomic():
            return RoleAssignment.objects.create(
                role=role, user_id=user_id, starts_at=now, ends_at=ends_at,
                is_current=True, assigned_by_user_id=actor.user_id)
    except IntegrityError as exc:
        raise ConflictError("A current assignment for this role already exists.",
                            code="assignment_conflict") from exc
