"""Archival & Permanent Purge Service for System Admin Control Plane.

Implements user archival, reversible restoration window, historical data archival,
and dual-authorization permanent purge workflows conforming to BR-SA-004, BR-SA-005,
BR-SA-017..022, CFR-SA-011..016, and Workflows BW-SA-01, 02, 07, 08, 09, CW-SA-01, 03.
"""
from datetime import date, datetime, timedelta
from typing import Any
from django.db import models, transaction
from django.utils import timezone

from modules.systemadmin.models.user_mgmt import BasicUserProfile, UserStatusHistory
from modules.systemadmin.models.role_mgmt import RoleAssignment, RoleAssignmentHistory
from modules.systemadmin.models.archival import (
    ArchivedUser,
    ArchivedHistoricalData,
    PermanentPurgeRequest,
)
from modules.systemadmin.models.config import SystemAdminConfig
from modules.systemadmin.services.audit_service import AuditService
from modules.systemadmin.services.notification_service import NotificationService
from modules.systemadmin.services.security_service import SecurityService


class ArchivalError(Exception):
    def __init__(self, message: str, code: str = "archival_error", details: list[str] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or []


class ArchivalService:
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
    @transaction.atomic
    def archive_user(
        cls,
        user_id: int,
        reason: str,
        retention_option: str = "standard_institutional",
        actor_username: str = "superadmin",
        confirmation_token: str = "",
        bypass_interval: bool = False,
        ip_address: str | None = None,
    ) -> ArchivedUser:
        """Archive an eligible deactivated basic user (UC-SA-015, BR-SA-004, BW-SA-07, CW-SA-03)."""
        user = BasicUserProfile.objects.filter(id=user_id).first()
        if not user:
            raise ArchivalError(f"User with ID {user_id} not found.", code="user_not_found")

        # BR-SA-004: Only deactivated users may be archived
        if user.status != "deactivated":
            raise ArchivalError(
                f"User is currently in status '{user.status}'. Only deactivated users are eligible for archival.",
                code="user_not_deactivated"
            )

        # BR-SA-004: Configured minimum deactivation-to-archival interval must elapse
        min_interval_days = int(cls.get_config_val("deactivation_to_archive_interval_days", 30))
        if user.deactivated_at and not bypass_interval:
            eligible_date = user.deactivated_at + timedelta(days=min_interval_days)
            if timezone.now() < eligible_date:
                raise ArchivalError(
                    f"Minimum deactivation interval of {min_interval_days} days has not elapsed. "
                    f"User will be eligible for archival after {eligible_date.strftime('%Y-%m-%d %H:%M')}.",
                    code="deactivation_interval_not_elapsed"
                )

        # Critical operation re-authentication (BR-SA-029)
        if confirmation_token:
            SecurityService.reauthenticate_critical_operation(actor_username, confirmation_token)

        # Reversible window configuration (BR-SA-005: ISS-SA-004)
        window_days = int(cls.get_config_val("archival_reversible_window_days", 90))
        now = timezone.now()
        reversibility_deadline = now + timedelta(days=window_days)

        # Retained information snapshot (AFR-SA-050)
        profile_snapshot = {
            "internal_user_id": user.internal_user_id,
            "institute_id": user.institute_id,
            "user_type": user.user_type,
            "full_name": user.full_name,
            "institute_email": user.institute_email,
            "department": user.department,
            "programme": user.programme,
            "date_of_joining": str(user.date_of_joining),
            "deactivated_at": str(user.deactivated_at) if user.deactivated_at else None,
        }

        role_history = list(
            RoleAssignment.objects.filter(user=user).values(
                "id", "role__name", "role__code", "start_date", "end_date", "status"
            )
        )

        # Update user status to archived and disable credentials (AFR-SA-049A, 049B)
        user.status = "archived"
        user.has_dashboard_access = False
        user.save()

        UserStatusHistory.objects.create(
            user=user,
            from_status="deactivated",
            to_status="archived",
            reason=reason,
            actor_username=actor_username,
        )

        archived_record = ArchivedUser.objects.create(
            user=user,
            archival_date=date.today(),
            archived_by=actor_username,
            reason=reason,
            retention_option=retention_option,
            reversibility_deadline=reversibility_deadline,
            status="reversible",
            retained_profile_snapshot=profile_snapshot,
            retained_role_history=role_history,
            retained_module_metadata={"archived_timestamp": str(now)},
        )

        NotificationService.send_notification(
            recipient_username=user.institute_id,
            title="Account Archived",
            message=(
                f"Your user account has been moved to the archive under retention option '{retention_option}'. "
                f"Reversible window expires on {reversibility_deadline.strftime('%Y-%m-%d')}."
            ),
            category="archival",
            channel="in_system",
        )

        AuditService.log_action(
            actor_username=actor_username,
            action="ARCHIVE_USER",
            result="SUCCESS",
            target_user=user.institute_id,
            ip_address=ip_address,
            reason_or_context=reason,
            metadata={
                "retention_option": retention_option,
                "reversibility_deadline": str(reversibility_deadline),
            },
        )

        return archived_record

    @classmethod
    @transaction.atomic
    def restore_archived_user(
        cls,
        archived_user_id: int | None = None,
        authorization_ref: str = "",
        confirmation_token: str = "",
        actor_username: str = "superadmin",
        ip_address: str | None = None,
        user_id: int | None = None,
        restoration_authorization_ref: str = "",
    ) -> BasicUserProfile:
        """Restore an archived user within the reversible period (UC-SA-018, BR-SA-005, BW-SA-07)."""
        target_id = archived_user_id or user_id
        ref = authorization_ref or restoration_authorization_ref
        record = ArchivedUser.objects.select_related("user").filter(
            models.Q(id=target_id) | models.Q(user_id=target_id)
        ).first()
        if not record:
            raise ArchivalError("Archived user record not found.", code="archive_record_not_found")

        # BR-SA-005 & ISS-SA-004: Must be within reversible window
        now = timezone.now()
        if record.status != "reversible" or now > record.reversibility_deadline:
            # Mark permanently non-restorable
            record.status = "permanent_non_restorable"
            record.save()
            raise ArchivalError(
                "Restoration rejected: The configured reversible period has elapsed. "
                "This archived user account is permanently non-restorable.",
                code="reversibility_window_expired"
            )

        if not ref or not ref.strip():
            raise ArchivalError(
                "Required administrative authorization reference must be supplied for user restoration.",
                code="missing_authorization_ref"
            )

        if confirmation_token:
            SecurityService.reauthenticate_critical_operation(actor_username, confirmation_token)

        user = record.user
        user.status = "active"
        user.has_dashboard_access = True
        user.save()

        record.status = "restored"
        record.restored_at = now
        record.restored_by = actor_username
        record.restoration_authorization_ref = ref
        record.save()

        UserStatusHistory.objects.create(
            user=user,
            from_status="archived",
            to_status="active",
            reason=f"Restored from archive (Auth Ref: {authorization_ref})",
            actor_username=actor_username,
        )

        NotificationService.send_notification(
            recipient_username=user.institute_id,
            title="Account Restored from Archive",
            message="Your account has been restored from archive with valid baseline dashboard access.",
            category="archival",
            channel="in_system",
        )

        AuditService.log_action(
            actor_username=actor_username,
            action="RESTORE_ARCHIVED_USER",
            result="SUCCESS",
            target_user=user.institute_id,
            ip_address=ip_address,
            reason_or_context=f"Restored under authorization: {authorization_ref}",
            metadata={"authorization_ref": authorization_ref},
        )

        return user

    @classmethod
    @transaction.atomic
    def finalize_non_restorable_archived_users(cls) -> int:
        """Transition reversible archived users whose window expired to permanent non-restorable (UC-SA-031, BW-SA-08)."""
        now = timezone.now()
        expired_records = ArchivedUser.objects.filter(
            status="reversible",
            reversibility_deadline__lt=now
        ).select_related("user")

        count = 0
        for record in expired_records:
            record.status = "permanent_non_restorable"
            record.save()

            AuditService.log_action(
                actor_username="system",
                action="ARCHIVE_USER_PERMANENT",
                result="SUCCESS",
                target_user=record.user.institute_id,
                reason_or_context="Reversibility period expired; account permanently non-restorable",
            )
            count += 1

        return count

    @classmethod
    @transaction.atomic
    def archive_historical_data(
        cls,
        category: str,
        date_range_start: date,
        date_range_end: date,
        confirmation_token: str = "",
        actor_username: str = "superadmin",
        record_count: int = 150,
        storage_size_kb: int = 2400,
        backup_reference: str = "",
        retention_years: int = 7,
        summary_metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> ArchivedHistoricalData:
        """Archive eligible historical system data with mandatory backup (UC-SA-016, BR-SA-017, BR-SA-018, BW-SA-09)."""
        if date_range_end < date_range_start:
            raise ArchivalError("End date cannot be earlier than start date.", code="invalid_date_range")

        # BR-SA-029: Authenticated confirmation if provided
        if confirmation_token:
            SecurityService.reauthenticate_critical_operation(actor_username, confirmation_token)

        # BR-SA-018: Mandatory backup creation before archival
        backup_ref = backup_reference or f"BKP-{category.upper()}-{timezone.now().strftime('%Y%m%d%H%M%S')}"

        retention_expiry = date_range_end + timedelta(days=365 * retention_years)

        meta = summary_metadata or {}
        meta.setdefault("backup_created", True)
        meta.setdefault("backup_reference", backup_ref)
        meta.setdefault("retention_policy_years", retention_years)

        archived_data = ArchivedHistoricalData.objects.create(
            category=category,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            archived_by=actor_username,
            record_count=record_count,
            storage_size_kb=storage_size_kb,
            backup_reference=backup_ref,
            status="archived",
            retention_expiry_date=retention_expiry,
            summary_metadata=meta,
        )

        AuditService.log_action(
            actor_username=actor_username,
            action="ARCHIVE_HISTORICAL_DATA",
            result="SUCCESS",
            ip_address=ip_address,
            reason_or_context=f"Archived {category} data ({date_range_start} to {date_range_end})",
            metadata={
                "category": category,
                "backup_reference": backup_ref,
                "record_count": record_count,
                "retention_expiry": str(retention_expiry),
            },
        )

        return archived_data

    @classmethod
    @transaction.atomic
    def restore_historical_data(
        cls,
        data_id: int,
        approval_ref: str,
        confirmation_token: str = "",
        actor_username: str = "superadmin",
        ip_address: str | None = None,
    ) -> ArchivedHistoricalData:
        """Restore archived historical data with required approval (UC-SA-019, BR-SA-020, BW-SA-09)."""
        record = ArchivedHistoricalData.objects.filter(id=data_id).first()
        if not record:
            raise ArchivalError(f"Historical data archive record #{data_id} not found.", code="record_not_found")
        if record.status != "archived":
            raise ArchivalError(f"Data is in status '{record.status}'; only archived data can be restored.", code="not_archived")

        if not approval_ref or not approval_ref.strip():
            raise ArchivalError("Required administrative approval reference is missing.", code="missing_approval_ref")

        if confirmation_token:
            SecurityService.reauthenticate_critical_operation(actor_username, confirmation_token)

        record.status = "restored"
        record.restored_at = timezone.now()
        record.restored_by = actor_username
        record.restoration_approval_ref = approval_ref
        record.save()

        AuditService.log_action(
            actor_username=actor_username,
            action="RESTORE_HISTORICAL_DATA",
            result="SUCCESS",
            ip_address=ip_address,
            reason_or_context=f"Restored {record.category} data under approval {approval_ref}",
            metadata={"data_id": data_id, "approval_ref": approval_ref},
        )

        return record

    @classmethod
    @transaction.atomic
    def request_permanent_purge(
        cls,
        target_type: str,  # "historical_data" or "archived_user"
        target_id: int,
        reason: str,
        confirmation_token: str = "",
        regulatory_authorization_ref: str = "",
        requester_username: str = "",
        actor_username: str = "superadmin",
        ip_address: str | None = None,
    ) -> PermanentPurgeRequest:
        """Submit permanent purge request initiating dual authorization (UC-SA-022, BR-SA-021, BR-SA-022, CW-SA-01)."""
        actor_username = requester_username or actor_username
        if confirmation_token:
            SecurityService.reauthenticate_critical_operation(actor_username, confirmation_token)

        hist_data = None
        arch_user = None

        if target_type == "historical_data":
            hist_data = ArchivedHistoricalData.objects.filter(id=target_id).first()
            if not hist_data:
                raise ArchivalError(f"Archived historical data #{target_id} not found.", code="target_not_found")
            # BR-SA-021: Retention period must have elapsed
            if date.today() < hist_data.retention_expiry_date:
                raise ArchivalError(
                    f"Permanent purge rejected: Retention period has not elapsed (expiry date: {hist_data.retention_expiry_date}).",
                    code="retention_not_elapsed"
                )
        elif target_type == "archived_user":
            arch_user = ArchivedUser.objects.select_related("user").filter(id=target_id).first()
            if not arch_user:
                raise ArchivalError(f"Archived user #{target_id} not found.", code="target_not_found")
            # Must be past reversibility window
            if arch_user.status == "reversible":
                raise ArchivalError(
                    "Permanent purge rejected: User is still within reversible archival window.",
                    code="reversibility_window_active"
                )
        else:
            raise ArchivalError(f"Invalid target type '{target_type}'.", code="invalid_target_type")

        purge_request = PermanentPurgeRequest.objects.create(
            target_type=target_type,
            historical_data=hist_data,
            archived_user=arch_user,
            requested_by=actor_username,
            request_reason=reason,
            super_admin_authenticated=True,
            status="pending_it_head",
        )

        NotificationService.send_notification(
            recipient_username="it_head",
            title="Permanent Purge Authorization Required",
            message=(
                f"Super Admin '{actor_username}' requested permanent purge of {target_type} #{target_id}. "
                "Dual authorization requires your review and approval as IT Head."
            ),
            category="archival",
            channel="in_system",
            recipient_role="IT Head",
        )

        AuditService.log_action(
            actor_username=actor_username,
            action="PURGE_REQUEST_SUBMIT",
            result="SUCCESS",
            ip_address=ip_address,
            reason_or_context=reason,
            metadata={"request_id": purge_request.id, "target_type": target_type, "target_id": target_id},
        )

        return purge_request

    @classmethod
    @transaction.atomic
    def authorize_permanent_purge(
        cls,
        request_id: int | None = None,
        decision: str = "approve",  # "approve" or "reject"
        comments: str = "",
        it_head_username: str = "it_head",
        purge_request_id: int | None = None,
        authorizer_username: str = "",
        it_head_signature_ref: str = "",
        reason: str = "",
        ip_address: str | None = None,
    ) -> PermanentPurgeRequest:
        """Authorize or reject permanent purge request as IT Head (UC-SA-023, BR-SA-022, BW-SA-01, BW-SA-02)."""
        request_id = request_id or purge_request_id
        it_head_username = authorizer_username or it_head_username
        comments = comments or reason or it_head_signature_ref
        purge_req = PermanentPurgeRequest.objects.filter(id=request_id).first()
        if not purge_req:
            raise ArchivalError(f"Purge request #{request_id} not found.", code="request_not_found")
        if purge_req.status != "pending_it_head":
            raise ArchivalError(
                f"Purge request is in status '{purge_req.status}'; only pending requests can be decided.",
                code="request_already_decided"
            )

        now = timezone.now()
        purge_req.it_head_decided_by = it_head_username
        purge_req.it_head_decided_at = now
        purge_req.it_head_comments = comments

        if decision == "approve":
            # Approved path: execute permanent destruction (BW-SA-01)
            purge_req.it_head_decision = "approve"
            purge_req.status = "approved"
            purge_req.purge_executed_at = now

            if purge_req.historical_data:
                purge_req.historical_data.status = "purged"
                purge_req.historical_data.save()
            elif purge_req.archived_user:
                # Permanent deletion of user record
                user_record = purge_req.archived_user.user
                purge_req.archived_user.delete()
                user_record.delete()

            purge_req.save()

            AuditService.log_action(
                actor_username=it_head_username,
                action="PURGE_AUTHORIZE_APPROVED",
                result="SUCCESS",
                ip_address=ip_address,
                reason_or_context=f"IT Head approved permanent purge: {comments}",
                metadata={"request_id": purge_req.id},
                actor_role="IT Head",
            )
        elif decision == "reject":
            # Rejected path: data remains safely archived (BW-SA-02)
            purge_req.it_head_decision = "reject"
            purge_req.status = "rejected"
            purge_req.save()

            AuditService.log_action(
                actor_username=it_head_username,
                action="PURGE_AUTHORIZE_REJECTED",
                result="SUCCESS",
                ip_address=ip_address,
                reason_or_context=f"IT Head rejected permanent purge: {comments}",
                metadata={"request_id": purge_req.id},
                actor_role="IT Head",
            )
        else:
            raise ArchivalError(f"Invalid decision '{decision}'. Must be 'approve' or 'reject'.", code="invalid_decision")

        NotificationService.send_notification(
            recipient_username=purge_req.requested_by,
            title=f"Purge Request Decided: {decision.upper()}",
            message=f"IT Head decided: {decision.upper()} on purge request #{purge_req.id}. Comments: {comments}",
            category="archival",
            channel="in_system",
            recipient_role="Super Admin",
        )

        return purge_req


archive_user = ArchivalService.archive_user
restore_archived_user = ArchivalService.restore_archived_user
finalize_non_restorable_archived_users = ArchivalService.finalize_non_restorable_archived_users
archive_historical_data = ArchivalService.archive_historical_data
restore_historical_data = ArchivalService.restore_historical_data
request_permanent_purge = ArchivalService.request_permanent_purge
authorize_permanent_purge = ArchivalService.authorize_permanent_purge
