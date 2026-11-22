"""Role assignment, extension, reassignment, and expiry lifecycle service."""

from datetime import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.superadmin.domain.exceptions import (
    DomainValidationError,
    PolicyConflictError,
)
from modules.superadmin.domain.policy import check_role_conflicts
from modules.superadmin.domain.state_machine import (
    ACTOR_SUPERADMIN,
    ACTOR_SYSTEM,
    EVT_ROLE_ACTIVATE_SCHEDULED,
    EVT_ROLE_EXPIRE,
    EVT_ROLE_EXTEND,
    EVT_ROLE_REASSIGN,
    EVT_ROLE_REVOKE,
    resolve_role_transition,
)
from modules.superadmin.domain.validators import validate_role_dates
from modules.superadmin.models import (
    RoleAssignmentRecord,
    RoleAssignmentStatus,
    RoleHandoverRecord,
    UserAccountRecord,
)
from modules.superadmin.services.audit import log_audit_event


@transaction.atomic
def assign_role(
    *,
    actor_user_id: int,
    user_id: int,
    role_name: str,
    valid_from: datetime,
    valid_to: datetime | None = None,
    scope_type: str = "",
    scope_id: str = "",
    is_singular: bool = False,
    reason: str = "",
    ip_address: str | None = None,
) -> RoleAssignmentRecord:
    # UC-SA-008: Assign additional role with validity dates and conflict checking.
    try:
        validate_role_dates(valid_from, valid_to)
    except DomainValidationError as e:
        raise BadRequestError(str(e), code="invalid_dates") from e

    user = UserAccountRecord.objects.filter(user_id=user_id).first()
    if not user:
        raise NotFoundError(f"User {user_id} not found.", code="user_not_found")

    # Check user eligibility and conflicting roles.
    existing = list(
        RoleAssignmentRecord.objects.filter(
            user_id=user_id,
            status__in=[
                RoleAssignmentStatus.ACTIVE,
                RoleAssignmentStatus.SCHEDULED,
                RoleAssignmentStatus.EXTENDED,
            ],
        ).values_list("role_name", flat=True)
    )
    try:
        check_role_conflicts(user.user_type, role_name, existing)
    except PolicyConflictError as e:
        raise ConflictError(str(e), code="role_conflict") from e

    # Singular role occupancy check.
    if is_singular:
        active_holder = RoleAssignmentRecord.objects.filter(
            role_name=role_name,
            status__in=[RoleAssignmentStatus.ACTIVE, RoleAssignmentStatus.EXTENDED],
        ).exists()
        if active_holder:
            raise ConflictError(
                f"Role {role_name!r} is singular and already occupied.",
                code="singular_role_occupied",
            )

    now = timezone.now()
    initial_status = (
        RoleAssignmentStatus.ACTIVE if valid_from <= now else RoleAssignmentStatus.SCHEDULED
    )

    assignment = RoleAssignmentRecord.objects.create(
        user_id=user_id,
        role_name=role_name,
        scope_type=scope_type,
        scope_id=scope_id,
        valid_from=valid_from,
        valid_to=valid_to,
        status=initial_status,
        is_singular=is_singular,
        assigned_by_user_id=actor_user_id,
        assignment_reason=reason,
    )

    log_audit_event(
        event_type="ROLE_ASSIGNED",
        actor_user_id=actor_user_id,
        target_entity="RoleAssignmentRecord",
        target_id=str(assignment.pk),
        ip_address=ip_address,
        action_details={"user_id": user_id, "role_name": role_name, "status": initial_status},
    )
    return assignment


@transaction.atomic
def extend_role_validity(
    *,
    actor_user_id: int,
    assignment_id: int,
    new_valid_to: datetime,
    reason: str,
    ip_address: str | None = None,
) -> RoleAssignmentRecord:
    # UC-SA-011 & BW-SA-05: Extend validity of active role assignment.
    assignment = RoleAssignmentRecord.objects.select_for_update().filter(pk=assignment_id).first()
    if not assignment:
        raise NotFoundError("Role assignment not found.", code="assignment_not_found")

    if assignment.status not in (RoleAssignmentStatus.ACTIVE, RoleAssignmentStatus.EXTENDED):
        raise ConflictError(
            f"Cannot extend role in status {assignment.status!r}.", code="invalid_role_status"
        )

    if assignment.valid_to and new_valid_to <= assignment.valid_to:
        raise BadRequestError(
            "New validity end date must be later than existing end date.",
            code="invalid_extension_date",
        )

    resolve_role_transition(assignment.status, EVT_ROLE_EXTEND, ACTOR_SUPERADMIN)

    assignment.status = RoleAssignmentStatus.EXTENDED
    assignment.valid_to = new_valid_to
    assignment.save(update_fields=["status", "valid_to", "updated_at"])

    log_audit_event(
        event_type="ROLE_EXTENDED",
        actor_user_id=actor_user_id,
        target_entity="RoleAssignmentRecord",
        target_id=str(assignment_id),
        ip_address=ip_address,
        action_details={"new_valid_to": new_valid_to.isoformat(), "reason": reason},
    )
    return assignment


@transaction.atomic
def revoke_role(
    *,
    actor_user_id: int,
    assignment_id: int,
    reason: str,
    ip_address: str | None = None,
) -> RoleAssignmentRecord:
    # UC-SA-010: Immediate administrative role revocation.
    assignment = RoleAssignmentRecord.objects.select_for_update().filter(pk=assignment_id).first()
    if not assignment:
        raise NotFoundError("Role assignment not found.", code="assignment_not_found")

    if assignment.status in (
        RoleAssignmentStatus.REVOKED,
        RoleAssignmentStatus.EXPIRED,
        RoleAssignmentStatus.REASSIGNED,
    ):
        raise ConflictError(
            f"Role is already in terminal status {assignment.status!r}.",
            code="role_terminal_status",
        )

    resolve_role_transition(assignment.status, EVT_ROLE_REVOKE, ACTOR_SUPERADMIN)

    assignment.status = RoleAssignmentStatus.REVOKED
    assignment.save(update_fields=["status", "updated_at"])

    log_audit_event(
        event_type="ROLE_REVOKED",
        actor_user_id=actor_user_id,
        target_entity="RoleAssignmentRecord",
        target_id=str(assignment_id),
        ip_address=ip_address,
        action_details={"reason": reason},
    )
    return assignment


@transaction.atomic
def reassign_role_with_handover(
    *,
    actor_user_id: int,
    assignment_id: int,
    successor_user_id: int,
    effective_date: datetime,
    handover_summary: str = "",
    ip_address: str | None = None,
) -> tuple[RoleAssignmentRecord, RoleAssignmentRecord]:
    # UC-SA-009 & BR-SA-012: Reassign role with handover transfer.
    old_assignment = (
        RoleAssignmentRecord.objects.select_for_update().filter(pk=assignment_id).first()
    )
    if not old_assignment:
        raise NotFoundError("Role assignment not found.", code="assignment_not_found")

    if old_assignment.status not in (RoleAssignmentStatus.ACTIVE, RoleAssignmentStatus.EXTENDED):
        raise ConflictError(
            f"Cannot reassign role in status {old_assignment.status!r}.", code="invalid_role_status"
        )

    if old_assignment.user_id == successor_user_id:
        raise BadRequestError(
            "Successor must be different from current role holder.", code="same_holder_reassignment"
        )

    resolve_role_transition(old_assignment.status, EVT_ROLE_REASSIGN, ACTOR_SUPERADMIN)
    old_assignment.status = RoleAssignmentStatus.REASSIGNED
    old_assignment.save(update_fields=["status", "updated_at"])

    # Create new assignment for successor starting on effective_date.
    new_assignment = RoleAssignmentRecord.objects.create(
        user_id=successor_user_id,
        role_name=old_assignment.role_name,
        scope_type=old_assignment.scope_type,
        scope_id=old_assignment.scope_id,
        valid_from=effective_date,
        valid_to=old_assignment.valid_to,
        status=RoleAssignmentStatus.ACTIVE
        if effective_date <= timezone.now()
        else RoleAssignmentStatus.SCHEDULED,
        is_singular=old_assignment.is_singular,
        assigned_by_user_id=actor_user_id,
        assignment_reason=f"Reassigned from user {old_assignment.user_id}",
    )

    # Record handover history.
    RoleHandoverRecord.objects.create(
        role_assignment=old_assignment,
        from_user_id=old_assignment.user_id,
        to_user_id=successor_user_id,
        effective_date=effective_date,
        pending_work_summary=handover_summary,
        audit_access_granted=True,
    )

    log_audit_event(
        event_type="ROLE_REASSIGNED",
        actor_user_id=actor_user_id,
        target_entity="RoleAssignmentRecord",
        target_id=str(assignment_id),
        ip_address=ip_address,
        action_details={
            "successor_user_id": successor_user_id,
            "new_assignment_id": new_assignment.pk,
        },
    )
    return old_assignment, new_assignment


@transaction.atomic
def activate_scheduled_roles(limit: int = 100) -> int:
    # UC-SA-028 & BW-SA-04: Periodic Celery task activates scheduled role assignments.
    now = timezone.now()
    scheduled = RoleAssignmentRecord.objects.select_for_update().filter(
        status=RoleAssignmentStatus.SCHEDULED,
        valid_from__lte=now,
    )[:limit]
    count = 0
    for a in scheduled:
        resolve_role_transition(a.status, EVT_ROLE_ACTIVATE_SCHEDULED, ACTOR_SYSTEM)
        a.status = RoleAssignmentStatus.ACTIVE
        a.save(update_fields=["status", "updated_at"])
        count += 1
    return count


@transaction.atomic
def expire_time_bound_roles(limit: int = 100) -> int:
    # UC-SA-029 & BW-SA-03: Periodic Celery task expires elapsed role assignments.
    now = timezone.now()
    expired = RoleAssignmentRecord.objects.select_for_update().filter(
        status__in=[RoleAssignmentStatus.ACTIVE, RoleAssignmentStatus.EXTENDED],
        valid_to__isnull=False,
        valid_to__lte=now,
    )[:limit]
    count = 0
    for a in expired:
        resolve_role_transition(a.status, EVT_ROLE_EXPIRE, ACTOR_SYSTEM)
        a.status = RoleAssignmentStatus.EXPIRED
        a.save(update_fields=["status", "updated_at"])
        count += 1
    return count
