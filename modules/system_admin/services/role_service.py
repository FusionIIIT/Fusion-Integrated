"""Role assignment, reassignment, revocation, and lifecycle service."""
from __future__ import annotations

from datetime import date

from django.db import transaction
from django.db.models import Q

from modules.system_admin.domain.exceptions import (
    DomainValidationError,
    RoleAssignmentNotFoundError,
    UserNotFoundError,
)
from modules.system_admin.domain.rules import (
    validate_role_dates,
    validate_singular_role_occupancy,
    validate_sod_conflicts,
    validate_user_type_role_eligibility,
)
from modules.system_admin.domain.state_machines import transition_role_state
from modules.system_admin.models.audit import SystemAuditLog
from modules.system_admin.models.role_assignment import RoleAssignment
from modules.system_admin.models.user_account import UserAccount


@transaction.atomic
def assign_role(
    *,
    role_code: str,
    user_id: int,
    start_date: date,
    end_date: date | None = None,
    scope: str = "",
    reason: str = "",
    role_name: str = "",
    is_singular: bool = False,
    actor_id: int = 1,
    ip_address: str | None = None,
) -> RoleAssignment:
    """Assign a role to an active user (UC-SA-008, BW-SA-03, BW-SA-04)."""
    # 1. User active check (BR-SA-015)
    try:
        user = UserAccount.objects.get(user_id=user_id)
    except UserAccount.DoesNotExist as err:
        raise UserNotFoundError(f"User {user_id} does not exist.") from err

    if user.status != "active":
        raise DomainValidationError(
            f"Cannot assign role to user {user_id} with status '{user.status}'."
        )

    # 2. Date validations (BR-SA-008)
    validate_role_dates(start_date=start_date, end_date=end_date, is_time_bound=bool(end_date))

    # 3. User type eligibility check (BR-SA-010)
    validate_user_type_role_eligibility(user_type=user.user_type, role_code=role_code)

    # 4. Separation of Duties (SOD) check (BR-SA-011)
    current_active_roles = list(
        RoleAssignment.objects.filter(
            user_id=user_id,
            status="active",
        ).values_list("role_code", flat=True)
    )
    validate_sod_conflicts(new_role=role_code, active_roles=current_active_roles)

    # 5. Singular role occupancy check (BR-SA-007)
    from modules.system_admin.selectors.role_selectors import KNOWN_SINGULAR_ROLES
    singular_codes = {r[0] for r in KNOWN_SINGULAR_ROLES}
    is_singular_role = is_singular or (role_code in singular_codes)
    if is_singular_role:
        current_holders = list(
            RoleAssignment.objects.filter(
                Q(role_code=role_code) | Q(role_name=role_code),
                status="active",
            ).values_list("user_id", flat=True)
        )
        validate_singular_role_occupancy(
            role_code=role_code,
            is_singular=True,
            current_active_holders=len(current_holders),
        )

    # 6. State determination
    today = date.today()
    initial_status = "scheduled" if start_date > today else "active"

    assignment = RoleAssignment.objects.create(
        role_code=role_code,
        role_name=role_name or role_code.replace("_", " ").title(),
        user_id=user_id,
        status=initial_status,
        is_singular=is_singular_role,
        start_date=start_date,
        end_date=end_date,
        scope=scope,
        reason=reason,
        assigned_by=actor_id,
    )

    SystemAuditLog.objects.create(
        actor_id=actor_id,
        action="system_admin.role.manage",
        target_id=str(assignment.id),
        ip_address=ip_address,
        result="success",
        context={
            "operation": "assign",
            "role_code": role_code,
            "user_id": user_id,
            "status": initial_status,
        },
    )

    return assignment


@transaction.atomic
def reassign_role(
    *,
    role_assignment_id: int,
    new_user_id: int,
    effective_date: date,
    reason: str,
    transfer_pending_tasks: bool = True,
    actor_id: int = 1,
    ip_address: str | None = None,
) -> tuple[RoleAssignment, RoleAssignment]:
    """Reassign an active role from one user to another (UC-SA-009, BR-SA-012)."""
    try:
        old_assignment = RoleAssignment.objects.select_for_update().get(id=role_assignment_id)
    except RoleAssignment.DoesNotExist as err:
        raise RoleAssignmentNotFoundError(
            f"RoleAssignment {role_assignment_id} does not exist."
        ) from err

    if old_assignment.status != "active":
        raise DomainValidationError(
            f"Cannot reassign role with status '{old_assignment.status}'."
        )

    # Revoke old assignment
    old_assignment.status = "revoked"
    old_assignment.save(update_fields=["status", "updated_at"])

    # Create new assignment for target user
    new_assignment = assign_role(
        role_code=old_assignment.role_code,
        user_id=new_user_id,
        start_date=effective_date,
        end_date=old_assignment.end_date,
        scope=old_assignment.scope,
        reason=f"Reassigned from user {old_assignment.user_id}: {reason}",
        role_name=old_assignment.role_name,
        is_singular=old_assignment.is_singular,
        actor_id=actor_id,
        ip_address=ip_address,
    )

    SystemAuditLog.objects.create(
        actor_id=actor_id,
        action="system_admin.role.manage",
        target_id=str(new_assignment.id),
        ip_address=ip_address,
        result="success",
        context={
            "operation": "reassign",
            "old_assignment_id": old_assignment.id,
            "previous_user_id": old_assignment.user_id,
            "new_user_id": new_user_id,
            "transfer_pending_tasks": transfer_pending_tasks,
        },
    )

    return old_assignment, new_assignment


@transaction.atomic
def revoke_role(
    *,
    role_assignment_id: int,
    reason: str,
    is_emergency: bool = False,
    actor_id: int = 1,
    ip_address: str | None = None,
) -> RoleAssignment:
    """Revoke an active role assignment (UC-SA-010, BR-SA-014)."""
    try:
        assignment = RoleAssignment.objects.select_for_update().get(id=role_assignment_id)
    except RoleAssignment.DoesNotExist as err:
        raise RoleAssignmentNotFoundError(
            f"RoleAssignment {role_assignment_id} does not exist."
        ) from err

    event = "revoke_emergency" if is_emergency else "revoke_standard"
    next_state = transition_role_state(assignment.status, event, "super_admin")
    assignment.status = next_state
    assignment.save(update_fields=["status", "updated_at"])

    SystemAuditLog.objects.create(
        actor_id=actor_id,
        action="system_admin.role.manage",
        target_id=str(assignment.id),
        ip_address=ip_address,
        result="success",
        context={
            "operation": "revoke",
            "is_emergency": is_emergency,
            "reason": reason,
        },
    )

    return assignment


@transaction.atomic
def extend_role_validity(
    *,
    role_assignment_id: int,
    new_end_date: date,
    reason: str,
    actor_id: int = 1,
    ip_address: str | None = None,
) -> RoleAssignment:
    """Extend the end date of an active role assignment (UC-SA-011, BW-SA-05, BR-SA-016)."""
    try:
        assignment = RoleAssignment.objects.select_for_update().get(id=role_assignment_id)
    except RoleAssignment.DoesNotExist as err:
        raise RoleAssignmentNotFoundError(
            f"RoleAssignment {role_assignment_id} does not exist."
        ) from err

    if assignment.status != "active":
        raise DomainValidationError(
            f"Cannot extend validity for role with status '{assignment.status}'."
        )

    validate_role_dates(
        start_date=assignment.start_date,
        end_date=new_end_date,
        is_time_bound=True,
    )

    assignment.end_date = new_end_date
    assignment.save(update_fields=["end_date", "updated_at"])

    SystemAuditLog.objects.create(
        actor_id=actor_id,
        action="system_admin.role.manage",
        target_id=str(assignment.id),
        ip_address=ip_address,
        result="success",
        context={
            "operation": "extend",
            "new_end_date": str(new_end_date),
            "reason": reason,
        },
    )

    return assignment


@transaction.atomic
def process_role_expiries(current_date: date | None = None) -> int:
    """System job to transition roles past their end date to 'expired' (UC-SA-029)."""
    ref_date = current_date or date.today()
    expired_qs = RoleAssignment.objects.filter(
        status="active",
        end_date__lt=ref_date,
    )
    count = expired_qs.count()
    if count > 0:
        expired_qs.update(status="expired")
        SystemAuditLog.objects.create(
            actor_id=1,
            action="system_admin.role.manage",
            target_id=f"expired_batch_{count}",
            result="success",
            context={"expired_count": count, "reference_date": str(ref_date)},
        )
    return count
