from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.vms.models import AuditEvent, VmsRoleAssignment


@transaction.atomic
def assign_role(*, user_id, role, scope_type, scope_value, starts_at, ends_at, actor_id):
    if ends_at and ends_at <= starts_at:
        raise ConflictError(
            "Role assignment end must be after its start.", code="invalid_role_window"
        )
    if scope_type == "campus" and scope_value:
        raise ConflictError(
            "Campus assignments cannot include a narrower scope value.", code="invalid_role_scope"
        )
    if scope_type != "campus" and not scope_value.strip():
        raise ConflictError(
            "Zone and gate assignments require a scope value.", code="invalid_role_scope"
        )
    overlap = VmsRoleAssignment.objects.filter(
        user_id=user_id,
        role=role,
        scope_type=scope_type,
        scope_value=scope_value,
        revoked_at__isnull=True,
    )
    overlap = overlap.filter(ends_at__isnull=True) | overlap.filter(ends_at__gt=starts_at)
    if ends_at:
        overlap = overlap.filter(starts_at__lt=ends_at)
    if overlap.exists():
        raise ConflictError(
            "An overlapping role assignment already exists.", code="role_assignment_overlap"
        )
    assignment = VmsRoleAssignment.objects.create(
        user_id=user_id,
        role=role,
        scope_type=scope_type,
        scope_value=scope_value.strip(),
        starts_at=starts_at,
        ends_at=ends_at,
        assigned_by_user_id=actor_id,
    )
    AuditEvent.objects.create(
        actor_user_id=actor_id,
        actor_kind="super_admin",
        action="role.assign",
        object_type="VmsRoleAssignment",
        object_id=str(assignment.pk),
        after={
            "user_id": user_id,
            "role": role,
            "scope_type": scope_type,
            "scope_value": assignment.scope_value,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat() if ends_at else None,
        },
    )
    return assignment


@transaction.atomic
def revoke_role(*, assignment_id, actor_id):
    assignment = (
        VmsRoleAssignment.objects.select_for_update()
        .filter(pk=assignment_id, revoked_at__isnull=True)
        .first()
    )
    if assignment is None:
        raise NotFoundError("Active role assignment not found.")
    assignment.revoked_at = timezone.now()
    assignment.revoked_by_user_id = actor_id
    assignment.save(update_fields=["revoked_at", "revoked_by_user_id", "updated_at"])
    AuditEvent.objects.create(
        actor_user_id=actor_id,
        actor_kind="super_admin",
        action="role.revoke",
        object_type="VmsRoleAssignment",
        object_id=str(assignment.pk),
        after={"user_id": assignment.user_id, "role": assignment.role},
    )
    return assignment


def has_active_assignment(*, user_id, role, scope_type, scope_value="", at=None):
    now = at or timezone.now()
    qs = VmsRoleAssignment.objects.filter(
        user_id=user_id, role=role, revoked_at__isnull=True, starts_at__lte=now
    ).filter(ends_at__isnull=True) | VmsRoleAssignment.objects.filter(
        user_id=user_id, role=role, revoked_at__isnull=True, starts_at__lte=now, ends_at__gt=now
    )
    return (
        qs.filter(scope_type="campus").exists()
        or qs.filter(scope_type=scope_type, scope_value=scope_value).exists()
    )
