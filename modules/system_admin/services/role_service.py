"""Role lifecycle service for System Admin module.

Implements UC-SA-008 through UC-SA-013, UC-SA-028..030, CW-SA-02, and BW-SA-03..05:
- Assign additional role (eligibility, singularity, conflict checking)
- Reassign role with work handover and previous holder audit access
- Revoke role (standard notice or emergency, task disposition)
- Extend time-bound role validity
- Automated scheduled role activation and expiration
- Role expiry reminders
- User active role switching
- Full immutable audit logging and notifications.
"""
from datetime import date, timedelta
from typing import Any
from django.db import transaction
from django.utils import timezone

from modules.system_admin.domain import (
    PendingTaskDisposition,
    RoleAssignmentStatus,
    validate_active_role_selection,
    validate_no_self_super_admin_modification,
    validate_role_assignment_transition,
    validate_role_conflicts,
    validate_role_dates,
    validate_role_extension,
    validate_role_revocation,
    validate_role_user_type_eligibility,
    validate_singular_role_occupancy,
)
from modules.system_admin.models import (
    BasicUser,
    RoleAssignment,
    RoleDefinition,
)
from modules.system_admin.services.audit_service import record_audit_event
from modules.system_admin.services.notification_service import (
    notify_module_admin,
    notify_super_admin,
    notify_user,
)


def assign_role(
    *,
    user_id: int,
    role_code: str,
    start_date: date,
    end_date: date | None = None,
    scope_type: str = "institute",
    scope_id: str = "",
    reason: str = "",
    actor_user_id: int = 0,
    actor_username: str = "system",
    ip_address: str | None = None,
    today: date | None = None,
) -> RoleAssignment:
    """UC-SA-008: Assign Additional Role (AFR-SA-022..027, AFR-SA-029).

    Enforces BR-SA-006 (multiple concurrent), BR-SA-007 (singularity),
    BR-SA-008 (dates), BR-SA-010 (user-type eligibility), BR-SA-011 (conflicts),
    BR-SA-028 (no self-modification of Super Admin status).
    """
    current_date = today or date.today()

    # 1. Enforce BR-SA-028
    validate_no_self_super_admin_modification(actor_user_id, user_id, role_code)

    role = RoleDefinition.objects.get(code=role_code)
    user = BasicUser.objects.get(user_id=user_id)

    # 2. Enforce BR-SA-008: Dates
    is_time_bound = role.default_validity_days is not None or end_date is not None
    if is_time_bound and end_date is None and role.default_validity_days:
        end_date = start_date + timedelta(days=role.default_validity_days)
    validate_role_dates(start_date, end_date, is_time_bound=is_time_bound)

    # 3. Enforce BR-SA-010: User-type eligibility
    validate_role_user_type_eligibility(role.allowed_user_types, user.user_type)

    # 4. Enforce BR-SA-007: Singular role occupancy
    scope_key = f"{scope_type}:{scope_id}"
    active_holders = list(
        RoleAssignment.objects.filter(
            role=role, scope_type=scope_type, scope_id=scope_id, status="active"
        ).values_list("user_id", flat=True)
    )
    validate_singular_role_occupancy(role.is_singular, scope_key, active_holders, user_id)

    # 5. Enforce BR-SA-011: Configured role conflicts
    existing_roles = list(
        RoleAssignment.objects.filter(user_id=user_id, status__in=["scheduled", "active"])
        .values_list("role__code", flat=True)
    )
    validate_role_conflicts(existing_roles, role.conflict_role_codes)

    # 6. Status: active if start_date <= today, else scheduled (BW-SA-03 / BW-SA-04)
    status = (
        RoleAssignmentStatus.ACTIVE.value
        if start_date <= current_date
        else RoleAssignmentStatus.SCHEDULED.value
    )

    with transaction.atomic():
        assignment = RoleAssignment.objects.create(
            user_id=user_id,
            role=role,
            start_date=start_date,
            end_date=end_date,
            scope_type=scope_type,
            scope_id=scope_id,
            reason=reason,
            status=status,
            assigned_by_user_id=actor_user_id,
        )

        # Notify affected user within 1 hour (AFR-SA-029, BR-SA-023)
        notify_user(
            user_id=user_id,
            event="role.assigned",
            title=f"New Role Assigned: {role.name}",
            message=(
                f"You have been assigned the role '{role.name}' ({role.code}) "
                f"effective from {start_date} to {end_date or 'indefinite'}."
            ),
            email=user.email,
        )

        # Notify module administrator (AFR-SA-070)
        notify_module_admin(
            module_code=role.module_association,
            event="module_role.assigned",
            title=f"Role Assigned in Module: {role.name}",
            message=f"User {user.institute_id} ({user.first_name} {user.last_name}) assigned {role.name}.",
        )

        # Record immutable audit entry (AFR-SA-031, BR-SA-025)
        record_audit_event(
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            action="role.assign",
            result="success",
            target_type="role_assignment",
            target_id=str(assignment.id),
            ip_address=ip_address,
            reason=reason or "Role assignment",
            details={
                "role_code": role.code,
                "target_user_id": user_id,
                "start_date": str(start_date),
                "end_date": str(end_date) if end_date else None,
                "status": status,
            },
        )

    return assignment


def reassign_role(
    *,
    current_assignment_id: int,
    new_user_id: int,
    effective_date: date,
    reason: str,
    actor_user_id: int,
    actor_username: str,
    ip_address: str | None = None,
    audit_access_days: int = 30,
    today: date | None = None,
) -> tuple[RoleAssignment, RoleAssignment]:
    """UC-SA-009: Reassign Role (AFR-SA-032..037, BR-SA-012, BR-SA-013).

    - Removes role access from old holder and transfers to new holder on effective date.
    - Transfers pending tasks via system services without exposing operational content.
    - Grants previous holder read-only audit access to their own prior actions (BR-SA-013).
    - Notifies both holders (AFR-SA-035A).
    """
    current_date = today or date.today()
    if not reason or not reason.strip():
        raise ValueError("Reason is mandatory for role reassignment.")

    with transaction.atomic():
        old_assignment = (
            RoleAssignment.objects.select_for_update()
            .select_related("role")
            .get(id=current_assignment_id)
        )
        role = old_assignment.role
        old_user = BasicUser.objects.get(user_id=old_assignment.user_id)
        new_user = BasicUser.objects.get(user_id=new_user_id)

        # Validate eligibility for new user
        validate_role_user_type_eligibility(role.allowed_user_types, new_user.user_type)
        validate_no_self_super_admin_modification(actor_user_id, new_user_id, role.code)

        # Reassignment execution
        # Set previous holder audit access period (BR-SA-013)
        old_assignment.status = RoleAssignmentStatus.REASSIGNED.value
        old_assignment.effective_revoked_at = timezone.now()
        old_assignment.revocation_reason = f"Reassigned to user {new_user_id}: {reason}"
        old_assignment.previous_holder_audit_until = timezone.now() + timedelta(days=audit_access_days)
        old_assignment.save()

        # Create new assignment for the new holder
        is_immediate = effective_date <= current_date
        new_status = (
            RoleAssignmentStatus.ACTIVE.value
            if is_immediate
            else RoleAssignmentStatus.SCHEDULED.value
        )

        new_assignment = RoleAssignment.objects.create(
            user_id=new_user_id,
            role=role,
            start_date=effective_date,
            end_date=old_assignment.end_date,
            scope_type=old_assignment.scope_type,
            scope_id=old_assignment.scope_id,
            reason=reason,
            status=new_status,
            assigned_by_user_id=actor_user_id,
            previous_assignment=old_assignment,
            pending_task_disposition=PendingTaskDisposition.TRANSFER.value,
        )

        # Notifications to both holders (AFR-SA-035A)
        notify_user(
            user_id=old_user.user_id,
            event="role.reassigned_from",
            title=f"Role Handover: {role.name}",
            message=(
                f"Your role '{role.name}' has been reassigned to {new_user.first_name} {new_user.last_name} "
                f"effective {effective_date}. You retain read-only audit access to your prior actions for {audit_access_days} days."
            ),
            email=old_user.email,
        )
        notify_user(
            user_id=new_user.user_id,
            event="role.reassigned_to",
            title=f"Role Assigned via Handover: {role.name}",
            message=(
                f"You have taken over the role '{role.name}' effective {effective_date}. "
                "All pending tasks associated with this role have been transferred to your queue."
            ),
            email=new_user.email,
        )

        # Audit record
        record_audit_event(
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            action="role.reassign",
            result="success",
            target_type="role_assignment",
            target_id=str(new_assignment.id),
            ip_address=ip_address,
            reason=reason,
            details={
                "role_code": role.code,
                "from_user_id": old_user.user_id,
                "to_user_id": new_user.user_id,
                "effective_date": str(effective_date),
                "tasks_transferred": True,
            },
        )

    return old_assignment, new_assignment


def revoke_role(
    *,
    assignment_id: int,
    effective_date: date,
    reason: str,
    pending_task_disposition: PendingTaskDisposition | str,
    is_emergency: bool = False,
    actor_user_id: int = 0,
    actor_username: str = "system",
    ip_address: str | None = None,
    today: date | None = None,
) -> RoleAssignment:
    """UC-SA-010: Revoke Role (AFR-SA-038, AFR-SA-039A..D).

    Enforces BR-SA-014: Standard revocation requires >= 1 day notice; emergency is immediate.
    Handles pending tasks (transfer or close) and notifies user & module admin.
    """
    current_date = today or date.today()
    disposition = (
        PendingTaskDisposition(pending_task_disposition)
        if isinstance(pending_task_disposition, str)
        else pending_task_disposition
    )

    validate_role_revocation(
        effective_date=effective_date,
        is_emergency=is_emergency,
        reason=reason,
        pending_task_disposition=disposition,
        today=current_date,
    )

    with transaction.atomic():
        assignment = (
            RoleAssignment.objects.select_for_update()
            .select_related("role")
            .get(id=assignment_id)
        )
        role = assignment.role
        user = BasicUser.objects.get(user_id=assignment.user_id)

        assignment.status = RoleAssignmentStatus.REVOKED.value
        assignment.effective_revoked_at = timezone.now()
        assignment.revocation_reason = reason
        assignment.pending_task_disposition = disposition.value
        assignment.save()

        # Notifications (AFR-SA-039C, AFR-SA-070)
        notify_user(
            user_id=user.user_id,
            event="role.revoked",
            title=f"Role Revocation: {role.name}",
            message=f"Your assignment for '{role.name}' has been revoked. Reason: {reason}.",
            email=user.email,
        )
        notify_module_admin(
            module_code=role.module_association,
            event="module_role.revoked",
            title=f"Role Revoked in Module: {role.name}",
            message=f"Role '{role.name}' revoked for user {user.institute_id}.",
        )

        record_audit_event(
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            action="role.revoke",
            result="success",
            target_type="role_assignment",
            target_id=str(assignment.id),
            ip_address=ip_address,
            reason=reason,
            details={
                "is_emergency": is_emergency,
                "pending_disposition": disposition.value,
                "effective_date": str(effective_date),
            },
        )

    return assignment


def extend_role_validity(
    *,
    assignment_id: int,
    new_end_date: date,
    reason: str,
    actor_user_id: int,
    actor_username: str,
    ip_address: str | None = None,
) -> RoleAssignment:
    """UC-SA-011: Extend Role Validity (AFR-SA-043, AFR-SA-044A, BW-SA-05, BR-SA-016)."""
    with transaction.atomic():
        assignment = (
            RoleAssignment.objects.select_for_update()
            .select_related("role")
            .get(id=assignment_id)
        )
        validate_role_extension(assignment.end_date, new_end_date, reason)

        old_end_date = assignment.end_date
        assignment.end_date = new_end_date
        assignment.save(update_fields=["end_date", "updated_at"])

        user = BasicUser.objects.get(user_id=assignment.user_id)
        notify_user(
            user_id=user.user_id,
            event="role.extended",
            title=f"Role Validity Extended: {assignment.role.name}",
            message=f"Your validity for role '{assignment.role.name}' has been extended to {new_end_date}.",
            email=user.email,
        )

        record_audit_event(
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            action="role.extend",
            result="success",
            target_type="role_assignment",
            target_id=str(assignment.id),
            ip_address=ip_address,
            reason=reason,
            details={
                "old_end_date": str(old_end_date) if old_end_date else None,
                "new_end_date": str(new_end_date),
            },
        )

    return assignment


def activate_scheduled_roles(today: date | None = None) -> int:
    """UC-SA-028: Activate Scheduled Role Assignment (AFR-SA-027, BR-SA-009).

    Automated task / event handler.
    """
    current_date = today or date.today()
    to_activate = RoleAssignment.objects.filter(
        status="scheduled", start_date__lte=current_date
    )
    count = 0
    for assignment in to_activate:
        assignment.status = RoleAssignmentStatus.ACTIVE.value
        assignment.save(update_fields=["status", "updated_at"])
        count += 1
        record_audit_event(
            actor_user_id=0,
            actor_username="scheduler",
            action="role.auto_activate",
            result="success",
            target_type="role_assignment",
            target_id=str(assignment.id),
            reason="Start date reached",
        )
    return count


def expire_time_bound_roles(today: date | None = None) -> int:
    """UC-SA-029: Expire Time-Bound Role (AFR-SA-028, AFR-SA-040A, AFR-SA-044B, BR-SA-009).

    Automated task / event handler.
    """
    current_date = today or date.today()
    to_expire = RoleAssignment.objects.filter(
        status="active", end_date__isnull=False, end_date__lte=current_date
    ).select_related("role")

    count = 0
    for assignment in to_expire:
        assignment.status = RoleAssignmentStatus.EXPIRED.value
        assignment.effective_revoked_at = timezone.now()
        assignment.save(update_fields=["status", "effective_revoked_at", "updated_at"])
        count += 1

        user = BasicUser.objects.filter(user_id=assignment.user_id).first()
        if user:
            notify_user(
                user_id=user.user_id,
                event="role.expired",
                title=f"Role Expired: {assignment.role.name}",
                message=f"Your assignment for '{assignment.role.name}' expired on {assignment.end_date}.",
                email=user.email,
            )

        record_audit_event(
            actor_user_id=0,
            actor_username="scheduler",
            action="role.auto_expire",
            result="success",
            target_type="role_assignment",
            target_id=str(assignment.id),
            reason="Role validity end date reached",
        )
    return count


def send_role_expiry_reminders(lead_days: int = 30, today: date | None = None) -> int:
    """UC-SA-030: Send Role-Expiry Reminder (AFR-SA-042, BR-SA-016)."""
    current_date = today or date.today()
    reminder_cutoff = current_date + timedelta(days=lead_days)
    approaching = RoleAssignment.objects.filter(
        status="active",
        end_date__isnull=False,
        end_date__gt=current_date,
        end_date__lte=reminder_cutoff,
    ).select_related("role")

    count = 0
    for assignment in approaching:
        days_left = (assignment.end_date - current_date).days
        user = BasicUser.objects.filter(user_id=assignment.user_id).first()
        if user:
            notify_user(
                user_id=user.user_id,
                event="role.expiry_reminder",
                title=f"Role Expiry Reminder: {assignment.role.name}",
                message=f"Your role '{assignment.role.name}' will expire in {days_left} days on {assignment.end_date}.",
                email=user.email,
            )
        notify_super_admin(
            event="role.expiry_approaching",
            title=f"Upcoming Role Expiry: {assignment.role.name}",
            message=f"Role assignment {assignment.id} for user {assignment.user_id} expires on {assignment.end_date}.",
        )
        count += 1

    return count


def switch_active_role(user_id: int, selected_role_code: str) -> dict[str, Any]:
    """UC-SA-013: Switch Active Role (AFR-SA-045, AFR-SA-046, BR-SA-034).

    Validates that the selected role is currently assigned and active for this user.
    Returns effective role and granted permissions context.
    """
    active_assignments = RoleAssignment.objects.filter(
        user_id=user_id, status="active"
    ).select_related("role")
    active_codes = [a.role.code for a in active_assignments]

    validate_active_role_selection(active_codes, selected_role_code)

    selected_assignment = next(a for a in active_assignments if a.role.code == selected_role_code)
    role = selected_assignment.role

    return {
        "active_role": role.code,
        "role_name": role.name,
        "scope_type": selected_assignment.scope_type,
        "scope_id": selected_assignment.scope_id,
        "permissions": role.permissions,
        "module": role.module_association,
    }
