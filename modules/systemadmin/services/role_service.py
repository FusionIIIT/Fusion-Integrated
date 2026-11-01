"""Role Management Service for System Admin Control Plane.

Implements role definition inspection, assignment, reassignment, revocation,
validity extension, automatic expiry, reminders, and conflict enforcement
conforming to BR-SA-006..016, BR-SA-023, and CFR-SA-005..010.
"""
from datetime import date, timedelta
from typing import Any
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from modules.systemadmin.models.user_mgmt import BasicUserProfile
from modules.systemadmin.models.role_mgmt import (
    RoleDefinition,
    RoleConflict,
    RoleAssignment,
    RoleAssignmentHistory,
)
from modules.systemadmin.models.config import SystemAdminConfig
from modules.systemadmin.services.audit_service import AuditService
from modules.systemadmin.services.notification_service import NotificationService


class RoleManagementError(Exception):
    def __init__(self, message: str, code: str = "role_mgmt_error", details: list[str] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or []


class RoleService:
    @classmethod
    def get_config_val(cls, key: str, default: Any) -> Any:
        try:
            cfg = SystemAdminConfig.objects.filter(key=key).first()
            if cfg:
                return cfg.value
        except Exception:
            pass
        return default

    @classmethod
    def check_user_eligibility(cls, role: RoleDefinition, user: BasicUserProfile) -> None:
        """Validate user-type eligibility for role (BR-SA-010)."""
        allowed = role.allowed_user_types or []
        if allowed and user.user_type not in allowed:
            raise RoleManagementError(
                f"User of type '{user.user_type}' is not eligible for role '{role.name}'. "
                f"Allowed types: {', '.join(allowed)}.",
                code="ineligible_user_type"
            )

    @classmethod
    def check_role_conflicts(cls, role: RoleDefinition, user: BasicUserProfile) -> None:
        """Validate configured role conflict matrix (BR-SA-011)."""
        active_role_ids = RoleAssignment.objects.filter(
            user=user,
            status__in=["active", "scheduled", "extended"]
        ).values_list("role_id", flat=True)

        conflicts = RoleConflict.objects.filter(
            (Q(role_a=role) & Q(role_b_id__in=active_role_ids)) |
            (Q(role_b=role) & Q(role_a_id__in=active_role_ids))
        )

        if conflicts.exists():
            conflict = conflicts.first()
            other_role = conflict.role_b if conflict.role_a == role else conflict.role_a
            raise RoleManagementError(
                f"Role '{role.name}' conflicts with currently held role '{other_role.name}': {conflict.reason}.",
                code="role_conflict_detected"
            )

    @classmethod
    def check_singularity(
        cls,
        role: RoleDefinition,
        scope: str,
        start_date: date,
        end_date: date | None,
        exclude_assignment_id: int | None = None,
    ) -> None:
        """Validate singular role occupancy (BR-SA-007)."""
        if not role.is_singular:
            return

        qs = RoleAssignment.objects.filter(
            role=role,
            scope=scope,
            status__in=["active", "scheduled", "extended"]
        )
        if exclude_assignment_id:
            qs = qs.exclude(id=exclude_assignment_id)

        # Check temporal overlap
        for existing in qs:
            overlap = True
            if end_date and existing.start_date > end_date:
                overlap = False
            if existing.end_date and start_date > existing.end_date:
                overlap = False
            if overlap:
                raise RoleManagementError(
                    f"Singular role '{role.name}' already has an active or scheduled holder "
                    f"({existing.user.full_name}) for scope '{scope}'. Singular roles can have only one active holder.",
                    code="singular_role_occupied"
                )

    @classmethod
    @transaction.atomic
    def assign_role(
        cls,
        role_code: str,
        user_id: int,
        start_date: date,
        end_date: date | None = None,
        scope: str = "",
        reason: str = "",
        actor_username: str = "superadmin",
        ip_address: str | None = None,
    ) -> RoleAssignment:
        """Assign an additional role to an eligible basic user (UC-SA-008, CFR-SA-006)."""
        if (role_code or "").lower().replace("-", "_").replace(" ", "_") in ("super_admin", "superadmin"):
            raise RoleManagementError(
                "Super Admin status is immutable and cannot be assigned through standard role assignment (BR-SA-028).",
                code="super_admin_immutable",
            )
        role = RoleDefinition.objects.filter(code=role_code).first()
        if not role:
            raise RoleManagementError(f"Role with code '{role_code}' does not exist.", code="role_not_found")
        if role.status != "available":
            raise RoleManagementError(f"Role '{role.name}' is deprecated and cannot be assigned.", code="role_deprecated")

        user = BasicUserProfile.objects.filter(id=user_id).first()
        if not user:
            raise RoleManagementError(f"User with ID {user_id} does not exist.", code="user_not_found")
        if user.status != "active":
            raise RoleManagementError(
                f"User is '{user.status}'; roles can only be assigned to active basic users.",
                code="user_not_active"
            )

        # Dates validation (BR-SA-008)
        if not start_date:
            raise RoleManagementError("Start date is mandatory for all role assignments.", code="missing_start_date")
        if role.is_time_bound and not end_date:
            raise RoleManagementError(f"Role '{role.name}' is time-bound and requires an end date.", code="missing_end_date")
        if end_date and end_date < start_date:
            raise RoleManagementError("End date cannot be earlier than start date.", code="invalid_date_range")

        # Eligibility, conflict, and singularity checks (BR-SA-007, BR-SA-010, BR-SA-011)
        cls.check_user_eligibility(role, user)
        cls.check_role_conflicts(role, user)
        cls.check_singularity(role, scope, start_date, end_date)

        # Determine initial status: scheduled vs active (BW-SA-03, BW-SA-04, CW-SA-02)
        today = date.today()
        initial_status = "scheduled" if start_date > today else "active"

        assignment = RoleAssignment.objects.create(
            role=role,
            user=user,
            scope=scope or "",
            start_date=start_date,
            end_date=end_date,
            status=initial_status,
            assignment_reason=reason or "Assigned by Super Admin",
            assigned_by=actor_username,
        )

        RoleAssignmentHistory.objects.create(
            assignment=assignment,
            action="assigned",
            actor_username=actor_username,
            details={
                "status": initial_status,
                "start_date": str(start_date),
                "end_date": str(end_date) if end_date else None,
                "reason": reason,
            },
        )

        # Notify affected user within 1 hour (BR-SA-023, AFR-SA-029)
        NotificationService.send_notification(
            recipient_username=user.institute_id,
            title="Additional Role Assigned",
            message=(
                f"You have been assigned the role '{role.name}' ({scope or 'General'}). "
                f"Effective: {start_date} to {end_date or 'Indefinite'}. Status: {initial_status}."
            ),
            category="role_lifecycle",
            channel="in_system",
            recipient_role=role.name,
        )

        AuditService.log_action(
            actor_username=actor_username,
            action="ROLE_ASSIGN",
            result="SUCCESS",
            target_user=user.institute_id,
            target_role=role.code,
            ip_address=ip_address,
            reason_or_context=reason,
            metadata={"assignment_id": assignment.id, "status": initial_status},
        )

        return assignment

    @classmethod
    @transaction.atomic
    def activate_scheduled_roles(cls) -> int:
        """Activate scheduled assignments whose start date is reached (UC-SA-028)."""
        today = date.today()
        scheduled_assignments = RoleAssignment.objects.filter(
            status="scheduled",
            start_date__lte=today
        ).select_related("user", "role")

        activated_count = 0
        for assignment in scheduled_assignments:
            if assignment.user.status != "active":
                AuditService.log_action(
                    actor_username="system",
                    action="ROLE_ACTIVATE_FAILED",
                    result="FAILURE",
                    target_user=assignment.user.institute_id,
                    target_role=assignment.role.code,
                    reason_or_context="User is no longer active at scheduled start date",
                )
                continue

            assignment.status = "active"
            assignment.save()

            RoleAssignmentHistory.objects.create(
                assignment=assignment,
                action="activated",
                actor_username="system",
                details={"reason": "Scheduled start date reached"},
            )

            NotificationService.send_notification(
                recipient_username=assignment.user.institute_id,
                title="Role Activated",
                message=f"Your scheduled assignment for role '{assignment.role.name}' is now active.",
                category="role_lifecycle",
                channel="in_system",
                recipient_role=assignment.role.name,
            )

            AuditService.log_action(
                actor_username="system",
                action="ROLE_ACTIVATE_SCHEDULED",
                result="SUCCESS",
                target_user=assignment.user.institute_id,
                target_role=assignment.role.code,
                reason_or_context="Automatic start date activation",
            )
            activated_count += 1

        return activated_count

    @classmethod
    @transaction.atomic
    def reassign_role(
        cls,
        assignment_id: int | None = None,
        new_user_id: int = 0,
        effective_date: date | None = None,
        reason: str = "",
        is_emergency: bool = False,
        pending_task_disposition: str = "transfer",
        actor_username: str = "superadmin",
        ip_address: str | None = None,
        current_assignment_id: int | None = None,
    ) -> RoleAssignment:
        """Reassign an active role with work handover and history preservation (UC-SA-009, BR-SA-012)."""
        assignment_id = current_assignment_id or assignment_id
        current_assignment = RoleAssignment.objects.select_related("role", "user").filter(id=assignment_id).first()
        if not current_assignment:
            raise RoleManagementError(f"Role assignment #{assignment_id} not found.", code="assignment_not_found")
        if current_assignment.status not in ["active", "extended"]:
            raise RoleManagementError(
                f"Assignment is in status '{current_assignment.status}'; only active roles can be reassigned.",
                code="invalid_status_for_reassign"
            )

        new_user = BasicUserProfile.objects.filter(id=new_user_id).first()
        if not new_user:
            raise RoleManagementError(f"New user with ID {new_user_id} not found.", code="user_not_found")
        if new_user.status != "active":
            raise RoleManagementError("New role holder must be an active basic user.", code="user_not_active")

        # Validate eligibility & conflicts for new user
        role = current_assignment.role
        cls.check_user_eligibility(role, new_user)
        cls.check_role_conflicts(role, new_user)

        today = date.today()
        handover_date = today if is_emergency else effective_date
        if not is_emergency and handover_date < today:
            raise RoleManagementError("Effective date cannot be in the past.", code="invalid_effective_date")

        audit_days = int(cls.get_config_val("previous_holder_audit_period_days", 30))
        audit_until = handover_date + timedelta(days=audit_days)

        old_user = current_assignment.user

        # Mark current assignment reassigned
        current_assignment.status = "reassigned"
        current_assignment.reassigned_to_user = new_user
        current_assignment.reassignment_effective_date = handover_date
        current_assignment.previous_holder_audit_until = audit_until
        current_assignment.save()

        RoleAssignmentHistory.objects.create(
            assignment=current_assignment,
            action="reassigned",
            actor_username=actor_username,
            details={
                "reassigned_to": new_user.institute_id,
                "effective_date": str(handover_date),
                "is_emergency": is_emergency,
                "reason": reason,
                "audit_access_until": str(audit_until),
            },
        )

        # Create new role assignment for new holder
        new_status = "active" if handover_date <= today else "scheduled"
        new_assignment = RoleAssignment.objects.create(
            role=role,
            user=new_user,
            scope=current_assignment.scope,
            start_date=handover_date,
            end_date=current_assignment.end_date,
            status=new_status,
            assignment_reason=f"Reassigned from {old_user.institute_id}: {reason}",
            assigned_by=actor_username,
        )

        RoleAssignmentHistory.objects.create(
            assignment=new_assignment,
            action="assigned",
            actor_username=actor_username,
            details={"reassigned_from": old_user.institute_id, "status": new_status},
        )

        # Notify both users (AFR-SA-035A)
        NotificationService.send_notification(
            recipient_username=old_user.institute_id,
            title="Role Reassigned",
            message=(
                f"Your role '{role.name}' ({current_assignment.scope}) has been reassigned to {new_user.full_name} "
                f"effective {handover_date}. Pending tasks have been transferred. You retain read-only audit access "
                f"to your prior actions until {audit_until}."
            ),
            category="role_lifecycle",
            channel="in_system",
        )
        NotificationService.send_notification(
            recipient_username=new_user.institute_id,
            title="Role Reassigned to You",
            message=(
                f"You have been assigned the role '{role.name}' ({current_assignment.scope}) reassigned from "
                f"{old_user.full_name} effective {handover_date}. Pending tasks transferred."
            ),
            category="role_lifecycle",
            channel="in_system",
            recipient_role=role.name,
        )

        AuditService.log_action(
            actor_username=actor_username,
            action="ROLE_REASSIGN",
            result="SUCCESS",
            target_user=new_user.institute_id,
            target_role=role.code,
            ip_address=ip_address,
            reason_or_context=reason,
            metadata={
                "from_user": old_user.institute_id,
                "to_user": new_user.institute_id,
                "effective_date": str(handover_date),
                "is_emergency": is_emergency,
            },
        )

        return new_assignment

    @classmethod
    @transaction.atomic
    def revoke_role(
        cls,
        assignment_id: int,
        reason: str,
        pending_task_disposition: str = "close",  # transfer or close
        is_emergency: bool = False,
        effective_date: date | None = None,
        actor_username: str = "superadmin",
        ip_address: str | None = None,
    ) -> RoleAssignment:
        """Revoke a role before its scheduled end date (UC-SA-010, BR-SA-014)."""
        assignment = RoleAssignment.objects.select_related("role", "user").filter(id=assignment_id).first()
        if not assignment:
            raise RoleManagementError(f"Role assignment #{assignment_id} not found.", code="assignment_not_found")
        if assignment.status not in ["active", "scheduled", "extended"]:
            raise RoleManagementError(
                f"Assignment is '{assignment.status}'; only active or scheduled roles can be revoked.",
                code="invalid_status_for_revocation"
            )

        today = date.today()
        # BR-SA-014: Standard revocation requires at least 1 day notice
        if not is_emergency:
            if not effective_date or effective_date <= today:
                raise RoleManagementError(
                    "Standard role revocation requires at least one day's notice (effective date in the future). "
                    "Use emergency revocation if immediate effect is required.",
                    code="insufficient_notice_period"
                )
        else:
            effective_date = today

        assignment.status = "revoked"
        assignment.revoked_at = timezone.now()
        assignment.revocation_reason = reason
        assignment.revocation_task_disposition = pending_task_disposition
        assignment.save()

        RoleAssignmentHistory.objects.create(
            assignment=assignment,
            action="revoked",
            actor_username=actor_username,
            details={
                "effective_date": str(effective_date),
                "is_emergency": is_emergency,
                "disposition": pending_task_disposition,
                "reason": reason,
            },
        )

        # Notify affected user and module administrators (AFR-SA-039C)
        NotificationService.send_notification(
            recipient_username=assignment.user.institute_id,
            title="Role Revoked",
            message=(
                f"Your role '{assignment.role.name}' has been revoked effective {effective_date}. "
                f"Pending tasks disposition: {pending_task_disposition}. Reason: {reason}."
            ),
            category="role_lifecycle",
            channel="in_system",
        )
        NotificationService.send_notification(
            recipient_username="module_admin",
            title=f"Role Revocation Notification: {assignment.role.name}",
            message=(
                f"Role '{assignment.role.name}' held by {assignment.user.institute_id} has been revoked "
                f"by Super Admin. Effective date: {effective_date}."
            ),
            category="role_lifecycle",
            channel="in_system",
            recipient_role="Module Admin",
        )

        AuditService.log_action(
            actor_username=actor_username,
            action="ROLE_REVOKE",
            result="SUCCESS",
            target_user=assignment.user.institute_id,
            target_role=assignment.role.code,
            ip_address=ip_address,
            reason_or_context=reason,
            metadata={
                "effective_date": str(effective_date),
                "is_emergency": is_emergency,
                "disposition": pending_task_disposition,
            },
        )

        return assignment

    @classmethod
    @transaction.atomic
    def extend_role_validity(
        cls,
        assignment_id: int,
        new_end_date: date,
        reason: str,
        extension_approval_ref: str = "",
        actor_username: str = "superadmin",
        ip_address: str | None = None,
    ) -> RoleAssignment:
        """Extend the validity of a time-bound role (UC-SA-011, BR-SA-016, BW-SA-05)."""
        assignment = RoleAssignment.objects.select_related("role", "user").filter(id=assignment_id).first()
        if not assignment:
            raise RoleManagementError(f"Role assignment #{assignment_id} not found.", code="assignment_not_found")
        if assignment.status not in ["active", "extended"]:
            raise RoleManagementError(
                f"Assignment is '{assignment.status}'; only active or extended roles can be extended.",
                code="invalid_status_for_extension"
            )

        if not assignment.end_date:
            raise RoleManagementError("Permanent roles do not have an end date to extend.", code="role_not_time_bound")
        if new_end_date <= assignment.end_date:
            raise RoleManagementError(
                f"New end date ({new_end_date}) must be later than current end date ({assignment.end_date}).",
                code="invalid_extension_date"
            )

        old_end_date = assignment.end_date
        assignment.end_date = new_end_date
        assignment.status = "extended"
        assignment.extended_at = timezone.now()
        full_reason = f"{reason} (Ref: {extension_approval_ref})" if extension_approval_ref and extension_approval_ref not in reason else reason
        assignment.extension_reason = full_reason
        assignment.reminder_sent = False  # Reset reminder for new date
        assignment.save()

        RoleAssignmentHistory.objects.create(
            assignment=assignment,
            action="extended",
            actor_username=actor_username,
            details={"old_end_date": str(old_end_date), "new_end_date": str(new_end_date), "reason": reason},
        )

        NotificationService.send_notification(
            recipient_username=assignment.user.institute_id,
            title="Role Validity Extended",
            message=f"Validity for your role '{assignment.role.name}' has been extended to {new_end_date}.",
            category="role_lifecycle",
            channel="in_system",
            recipient_role=assignment.role.name,
        )

        AuditService.log_action(
            actor_username=actor_username,
            action="ROLE_EXTEND",
            result="SUCCESS",
            target_user=assignment.user.institute_id,
            target_role=assignment.role.code,
            ip_address=ip_address,
            reason_or_context=reason,
            metadata={"old_end_date": str(old_end_date), "new_end_date": str(new_end_date)},
        )

        return assignment

    @classmethod
    @transaction.atomic
    def expire_time_bound_roles(cls) -> int:
        """Expire time-bound roles whose end date is reached (UC-SA-029, BR-SA-009)."""
        today = date.today()
        expired_assignments = RoleAssignment.objects.filter(
            status__in=["active", "extended"],
            end_date__lt=today
        ).select_related("role", "user")

        count = 0
        for assignment in expired_assignments:
            assignment.status = "expired"
            assignment.save()

            RoleAssignmentHistory.objects.create(
                assignment=assignment,
                action="expired",
                actor_username="system",
                details={"reason": "End date reached"},
            )

            NotificationService.send_notification(
                recipient_username=assignment.user.institute_id,
                title="Role Expired",
                message=f"Your assignment for role '{assignment.role.name}' expired on {assignment.end_date}.",
                category="role_lifecycle",
                channel="in_system",
            )

            AuditService.log_action(
                actor_username="system",
                action="ROLE_EXPIRE",
                result="SUCCESS",
                target_user=assignment.user.institute_id,
                target_role=assignment.role.code,
                reason_or_context="Automatic time-bound role expiry",
            )
            count += 1

        return count

    @classmethod
    @transaction.atomic
    def send_expiry_reminders(cls) -> int:
        """Dispatch expiry reminders at configured lead time (UC-SA-030, BR-SA-016)."""
        lead_days = int(cls.get_config_val("role_expiry_reminder_lead_days", 30))
        target_date = date.today() + timedelta(days=lead_days)

        remindable = RoleAssignment.objects.filter(
            status__in=["active", "extended"],
            end_date__lte=target_date,
            end_date__gte=date.today(),
            reminder_sent=False
        ).select_related("role", "user")

        count = 0
        for assignment in remindable:
            NotificationService.send_notification(
                recipient_username=assignment.user.institute_id,
                title="Role Expiry Approaching",
                message=(
                    f"Reminder: Your assignment for role '{assignment.role.name}' will expire on "
                    f"{assignment.end_date} (within {lead_days} days). Contact Super Admin if an extension is required."
                ),
                category="role_lifecycle",
                channel="in_system",
                recipient_role=assignment.role.name,
            )
            NotificationService.send_notification(
                recipient_username="superadmin",
                title=f"Upcoming Role Expiry: {assignment.role.name}",
                message=(
                    f"Role '{assignment.role.name}' held by {assignment.user.institute_id} expires on "
                    f"{assignment.end_date}."
                ),
                category="role_lifecycle",
                channel="in_system",
                recipient_role="Super Admin",
            )
            assignment.reminder_sent = True
            assignment.save(update_fields=["reminder_sent"])
            count += 1

        return count


assign_role = RoleService.assign_role
activate_scheduled_roles = RoleService.activate_scheduled_roles
reassign_role = RoleService.reassign_role
revoke_role = RoleService.revoke_role
extend_role_validity = RoleService.extend_role_validity
expire_time_bound_roles = RoleService.expire_time_bound_roles
send_expiry_reminders = RoleService.send_expiry_reminders
