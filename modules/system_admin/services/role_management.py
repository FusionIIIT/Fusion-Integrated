"""Role assignment, handover, revocation, and switching service for system_admin."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from django.db import transaction
from django.utils import timezone

from modules.system_admin.constants import (
    AuditAction,
    AuditResult,
    NotificationChannel,
    PendingTaskDisposition,
    RoleAssignmentState,
    RoleRevocationType,
)
from modules.system_admin.domain import validators
from modules.system_admin.domain.dataclasses import (
    RoleAssignmentSpec,
    RoleReassignmentSpec,
    RoleRevocationSpec,
)
from modules.system_admin.domain.exceptions import (
    DomainError,
    RoleConflictError,
    SingularRoleOccupiedError,
)
from modules.system_admin.domain.state_machine import RoleStateMachine
from modules.system_admin.models import (
    BasicUser,
    RoleAssignment,
    RoleAssignmentHistory,
    RoleDefinition,
    RoleHandoverLog,
    SuperAdminAuditLog,
)
from modules.system_admin.services import notifications


def assign_role(spec: RoleAssignmentSpec, performed_by_id: int) -> RoleAssignment:
    """Assign additional role to an eligible user (UC-SA-008, CFR-SA-006)."""
    role = RoleDefinition.objects.get(code=spec.role_code, is_active=True)

    # Validate eligibility & dating
    validators.validate_role_eligibility(role.code, spec.target_user_kind, role.get_allowed_kinds_set())
    validators.validate_role_dating(spec.start_date, role.is_time_bound, spec.end_date)

    # Singular role check (BR-SA-007)
    if role.is_singular:
        existing = RoleAssignment.objects.filter(
            role=role,
            scope=spec.scope,
            state__in=[RoleAssignmentState.ACTIVE, RoleAssignmentState.EXTENDED],
        ).first()
        if existing and existing.user_id != spec.target_user_id:
            raise SingularRoleOccupiedError(role.code, spec.scope, existing.user_id)

    # Conflict validation (BR-SA-011)
    conflicting_codes = role.compatibility_rules.get("conflicts_with", [])
    if conflicting_codes:
        active_conflict = RoleAssignment.objects.filter(
            user_id=spec.target_user_id,
            role_id__in=conflicting_codes,
            state__in=[RoleAssignmentState.ACTIVE, RoleAssignmentState.EXTENDED],
        ).first()
        if active_conflict:
            raise RoleConflictError(
                role.code, active_conflict.role_id, "Incompatible role combination."
            )

    today = date.today()
    initial_state = RoleStateMachine.validate_immediate_assignment(spec.start_date, today)
    activated_at = timezone.now() if initial_state == RoleAssignmentState.ACTIVE else None

    with transaction.atomic():
        assignment = RoleAssignment.objects.create(
            user_id=spec.target_user_id,
            role=role,
            scope=spec.scope,
            start_date=spec.start_date,
            end_date=spec.end_date,
            state=initial_state,
            assigned_by=performed_by_id,
            reason=spec.reason,
            activated_at=activated_at,
        )

        RoleAssignmentHistory.objects.create(
            assignment=assignment,
            action="assigned",
            from_state="",
            to_state=initial_state,
            performed_by=performed_by_id,
            effective_date=spec.start_date,
            reason=spec.reason,
        )

        # Notify within 1 hour SLA (BR-SA-023)
        user = BasicUser.objects.get(id=spec.target_user_id)
        notifications.queue_notification(
            recipient_id=user.id,
            email=user.email,
            channel=NotificationChannel.EMAIL,
            template_code="role_assigned",
            subject=f"New Role Assigned: {role.label}",
            body=f"You have been assigned the role '{role.label}' (scope: {spec.scope}) effective from {spec.start_date}.",
        )

        SuperAdminAuditLog.objects.create(
            actor_id=performed_by_id,
            actor_username="admin",
            action=AuditAction.ROLE_ASSIGN,
            target_user_id=spec.target_user_id,
            target_role_code=role.code,
            result=AuditResult.SUCCESS,
            reason=spec.reason,
        )

    return assignment


def reassign_role(spec: RoleReassignmentSpec, performed_by_id: int) -> RoleAssignment:
    """Reassign role with task handover and previous holder audit access (UC-SA-009, CFR-SA-007, BR-SA-012, BR-SA-013)."""
    curr = RoleAssignment.objects.select_related("role").get(id=spec.role_assignment_id)
    if curr.state not in [RoleAssignmentState.ACTIVE, RoleAssignmentState.EXTENDED]:
        raise DomainError("Only active or extended roles can be reassigned.")

    validators.validate_role_eligibility(
        curr.role.code, spec.new_holder_kind, curr.role.get_allowed_kinds_set()
    )

    now = timezone.now()
    audit_cutoff = spec.effective_date + timedelta(days=spec.audit_access_days)

    with transaction.atomic():
        # Revoke old assignment
        curr.state = RoleAssignmentState.REVOKED
        curr.revoked_at = now
        curr.revocation_type = RoleRevocationType.STANDARD
        curr.revocation_reason = f"Reassigned to user {spec.new_holder_id}: {spec.reason}"
        curr.save(update_fields=["state", "revoked_at", "revocation_type", "revocation_reason"])

        RoleAssignmentHistory.objects.create(
            assignment=curr,
            action="reassigned",
            from_state=RoleAssignmentState.ACTIVE,
            to_state=RoleAssignmentState.REVOKED,
            performed_by=performed_by_id,
            effective_date=spec.effective_date,
            reason=spec.reason,
        )

        # Create new assignment
        new_assignment = RoleAssignment.objects.create(
            user_id=spec.new_holder_id,
            role=curr.role,
            scope=curr.scope,
            start_date=spec.effective_date,
            state=RoleAssignmentState.ACTIVE,
            assigned_by=performed_by_id,
            reason=spec.reason,
            activated_at=now,
        )

        RoleAssignmentHistory.objects.create(
            assignment=new_assignment,
            action="assigned",
            from_state="",
            to_state=RoleAssignmentState.ACTIVE,
            performed_by=performed_by_id,
            effective_date=spec.effective_date,
            reason=f"Reassigned from user {spec.previous_holder_id}",
        )

        # Create handover log & previous holder audit access record (BR-SA-012, BR-SA-013)
        RoleHandoverLog.objects.create(
            role=curr.role,
            previous_holder_id=spec.previous_holder_id,
            new_holder_id=spec.new_holder_id,
            scope=curr.scope,
            effective_date=spec.effective_date,
            pending_tasks_count=0,
            tasks_disposition=PendingTaskDisposition.TRANSFER,
            audit_access_expires_at=audit_cutoff,
            reassigned_by=performed_by_id,
        )

        # Notify both users within 1 hour (BR-SA-023)
        prev_user = BasicUser.objects.get(id=spec.previous_holder_id)
        new_user = BasicUser.objects.get(id=spec.new_holder_id)

        notifications.queue_notification(
            recipient_id=prev_user.id,
            email=prev_user.email,
            channel=NotificationChannel.EMAIL,
            template_code="role_reassigned_previous",
            subject=f"Role Handover: {curr.role.label}",
            body=f"Your role '{curr.role.label}' has been reassigned to {new_user.username}. Read-only audit access is retained until {audit_cutoff}.",
        )
        notifications.queue_notification(
            recipient_id=new_user.id,
            email=new_user.email,
            channel=NotificationChannel.EMAIL,
            template_code="role_reassigned_new",
            subject=f"Role Assignment Handover: {curr.role.label}",
            body=f"You have been assigned '{curr.role.label}' following handover from {prev_user.username}.",
        )

        SuperAdminAuditLog.objects.create(
            actor_id=performed_by_id,
            actor_username="admin",
            action=AuditAction.ROLE_REASSIGN,
            target_user_id=spec.new_holder_id,
            target_role_code=curr.role.code,
            result=AuditResult.SUCCESS,
            reason=spec.reason,
        )

    return new_assignment


def revoke_role(spec: RoleRevocationSpec, performed_by_id: int) -> RoleAssignment:
    """Revoke role assignment with notice period validation (UC-SA-010, CFR-SA-008, BR-SA-014)."""
    validators.validate_revocation_notice(spec.is_emergency, spec.notice_date, spec.effective_date)

    assignment = RoleAssignment.objects.select_related("role", "user").get(id=spec.role_assignment_id)
    now = timezone.now()

    with transaction.atomic():
        prev_state = assignment.state
        assignment.state = RoleAssignmentState.REVOKED
        assignment.revoked_at = now
        assignment.revocation_type = (
            RoleRevocationType.EMERGENCY if spec.is_emergency else RoleRevocationType.STANDARD
        )
        assignment.revocation_reason = spec.reason
        assignment.notice_date = spec.notice_date
        assignment.save(update_fields=["state", "revoked_at", "revocation_type", "revocation_reason", "notice_date"])

        RoleAssignmentHistory.objects.create(
            assignment=assignment,
            action="revoked",
            from_state=prev_state,
            to_state=RoleAssignmentState.REVOKED,
            performed_by=performed_by_id,
            effective_date=spec.effective_date,
            reason=spec.reason,
        )

        notifications.queue_notification(
            recipient_id=assignment.user_id,
            email=assignment.user.email,
            channel=NotificationChannel.EMAIL,
            template_code="role_revoked",
            subject=f"Notice of Role Revocation: {assignment.role.label}",
            body=f"Your assignment for '{assignment.role.label}' has been revoked. Reason: {spec.reason}",
        )

        SuperAdminAuditLog.objects.create(
            actor_id=performed_by_id,
            actor_username="admin",
            action=AuditAction.ROLE_REVOKE,
            target_user_id=assignment.user_id,
            target_role_code=assignment.role.code,
            result=AuditResult.SUCCESS,
            reason=spec.reason,
        )

    return assignment


def extend_role_validity(
    assignment_id: int, new_end_date: date, reason: str, performed_by_id: int
) -> RoleAssignment:
    """Extend validity of active time-bound role (UC-SA-011, CFR-SA-009, BW-SA-05, BR-SA-016)."""
    assignment = RoleAssignment.objects.select_related("role").get(id=assignment_id)
    if assignment.state not in [RoleAssignmentState.ACTIVE, RoleAssignmentState.EXTENDED]:
        raise DomainError("Only active or extended roles can be extended.")
    if assignment.end_date and new_end_date <= assignment.end_date:
        raise DomainError("New end date must be strictly after the current end date (BR-SA-016).")

    with transaction.atomic():
        prev_state = assignment.state
        assignment.end_date = new_end_date
        assignment.state = RoleAssignmentState.EXTENDED
        assignment.save(update_fields=["end_date", "state"])

        RoleAssignmentHistory.objects.create(
            assignment=assignment,
            action="extended",
            from_state=prev_state,
            to_state=RoleAssignmentState.EXTENDED,
            performed_by=performed_by_id,
            effective_date=date.today(),
            reason=reason,
        )

        SuperAdminAuditLog.objects.create(
            actor_id=performed_by_id,
            actor_username="admin",
            action=AuditAction.ROLE_EXTEND,
            target_user_id=assignment.user_id,
            target_role_code=assignment.role.code,
            result=AuditResult.SUCCESS,
            reason=reason,
        )

    return assignment


def switch_active_role(user_id: int, target_role_code: str) -> None:
    """Validate user holds role and switch active role (UC-SA-013, CFR-SA-010, BR-SA-034)."""
    valid = RoleAssignment.objects.filter(
        user_id=user_id,
        role_id=target_role_code,
        state__in=[RoleAssignmentState.ACTIVE, RoleAssignmentState.EXTENDED],
    ).exists()
    if not valid:
        raise DomainError(f"User {user_id} does not hold an active assignment for role '{target_role_code}'.")
