"""User and historical data archival service for System Admin module.

Implements UC-SA-015 through UC-SA-023, UC-SA-031, CW-SA-01, CW-SA-03, and BW-SA-01, 02, 07, 08, 09:
- Archive deactivated users (interval check, pending transaction checks)
- Restore archived user within reversible period (ISS-SA-004)
- Finalize archived users as permanently non-restorable
- Archive historical data after retention and backup checks
- Request and dual-authorize permanent data purge (Super Admin + IT Head).
"""
from datetime import date, timedelta
from typing import Any
from django.db import transaction
from django.utils import timezone

from modules.system_admin.domain import (
    PurgeRequestStatus,
    UserStatus,
    validate_archived_user_reversibility,
    validate_critical_operation_reauth,
    validate_historical_data_archival_eligibility,
    validate_permanent_purge_eligibility,
    validate_purge_authorization,
    validate_user_archival_eligibility,
    validate_user_transition,
)
from modules.system_admin.models import (
    ArchivedRecord,
    BasicUser,
    PurgeRequest,
    RoleAssignment,
)
from modules.system_admin.services.audit_service import record_audit_event
from modules.system_admin.services.notification_service import (
    notify_super_admin,
    notify_user,
)


def archive_user(
    *,
    user_id: int,
    retention_years: int = 7,
    reversible_window_days: int = 180,
    min_deactivation_days: int = 30,
    reason: str = "",
    actor_user_id: int = 0,
    actor_username: str = "system",
    ip_address: str | None = None,
    reauthenticated: bool = True,
    now: Any = None,
) -> tuple[BasicUser, ArchivedRecord]:
    """UC-SA-015: Archive User (AFR-SA-047..050, BR-SA-004, CW-SA-03)."""
    current_time = now or timezone.now()
    validate_critical_operation_reauth(True, reauthenticated, "User archival")

    with transaction.atomic():
        user = BasicUser.objects.select_for_update().get(user_id=user_id)

        # Enforce BR-SA-004: Deactivated, min interval elapsed, no pending transactions
        validate_user_archival_eligibility(
            status=user.status,
            deactivated_at=user.deactivated_at,
            min_interval_days=min_deactivation_days,
            has_pending_transactions=user.has_pending_transactions,
            current_time=current_time,
        )

        validate_user_transition(
            UserStatus(user.status),
            UserStatus.ARCHIVED,
            deactivated_at=user.deactivated_at,
            min_interval_days=min_deactivation_days,
            has_pending_transactions=user.has_pending_transactions,
            current_time=current_time,
        )

        # Disable all credentials and revoke any remaining roles (AFR-SA-049A)
        RoleAssignment.objects.filter(
            user_id=user.user_id, status__in=["scheduled", "active"]
        ).update(
            status="revoked",
            effective_revoked_at=current_time,
            revocation_reason="User archived",
        )

        user.status = UserStatus.ARCHIVED.value
        user.archived_at = current_time
        user.archival_reason = reason
        user.dashboard_access_enabled = False
        user.reversible_until = current_time + timedelta(days=reversible_window_days)
        user.is_permanently_archived = False
        user.save()

        # Retain user snapshot in archive repository (AFR-SA-050)
        retention_until = (current_time + timedelta(days=retention_years * 365)).date()
        archive_entry = ArchivedRecord.objects.create(
            category="user_profile",
            identifier=user.institute_id,
            data_payload={
                "user_id": user.user_id,
                "institute_id": user.institute_id,
                "user_type": user.user_type,
                "email": user.email,
                "name": f"{user.first_name} {user.last_name}",
                "department": user.department,
                "archived_at": current_time.isoformat(),
            },
            retention_until=retention_until,
            backup_reference=f"backup_user_{user.user_id}_{current_time.strftime('%Y%m%d%H%M')}",
            archived_by_user_id=actor_user_id,
            reason=reason,
            status="archived",
        )

        notify_user(
            user_id=user.user_id,
            event="user.archived",
            title="Account Archived",
            message=f"Your account has been moved to the institutional archive. Reversible restoration window is {reversible_window_days} days.",
            email=user.email,
        )

        record_audit_event(
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            action="user.archive",
            result="success",
            target_type="basic_user",
            target_id=str(user.user_id),
            ip_address=ip_address,
            reason=reason,
            details={
                "archive_id": archive_entry.id,
                "reversible_until": user.reversible_until.isoformat(),
                "retention_until": str(retention_until),
            },
        )

    return user, archive_entry


def restore_archived_user(
    *,
    user_id: int,
    reason: str,
    actor_user_id: int,
    actor_username: str,
    ip_address: str | None = None,
    reauthenticated: bool = True,
    reversible_window_days: int = 180,
    now: Any = None,
) -> BasicUser:
    """UC-SA-018: Restore Archived User (AFR-SA-051A, BW-SA-07, BR-SA-005, ISS-SA-004).

    Restoration allowed ONLY within the configured reversible period.
    """
    current_time = now or timezone.now()
    validate_critical_operation_reauth(True, reauthenticated, "Archived user restoration")

    with transaction.atomic():
        user = BasicUser.objects.select_for_update().get(user_id=user_id)

        # Enforce BR-SA-005 & ISS-SA-004: strictly reject post-window restoration
        validate_archived_user_reversibility(
            archived_at=user.archived_at,
            reversible_window_days=reversible_window_days,
            is_permanently_archived=user.is_permanently_archived,
            current_time=current_time,
        )

        validate_user_transition(
            UserStatus(user.status),
            UserStatus.ACTIVE,
            archived_at=user.archived_at,
            reversible_window_days=reversible_window_days,
            is_permanently_archived=user.is_permanently_archived,
            current_time=current_time,
        )

        user.status = UserStatus.ACTIVE.value
        user.dashboard_access_enabled = True
        user.archived_at = None
        user.archival_reason = ""
        user.reversible_until = None
        user.save()

        # Update matching archived record status
        ArchivedRecord.objects.filter(
            category="user_profile", identifier=user.institute_id, status="archived"
        ).update(status="restored")

        notify_user(
            user_id=user.user_id,
            event="user.restored",
            title="Archived Account Restored",
            message="Your archived account has been restored to active status.",
            email=user.email,
        )

        record_audit_event(
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            action="user.restore_archived",
            result="success",
            target_type="basic_user",
            target_id=str(user.user_id),
            ip_address=ip_address,
            reason=reason,
        )

    return user


def finalize_non_restorable_archived_users(now: Any = None) -> int:
    """UC-SA-031: Finalize Archived User as Permanently Non-Restorable (AFR-SA-051B, BW-SA-08).

    Automated task / event handler.
    """
    current_time = now or timezone.now()
    expired_users = BasicUser.objects.filter(
        status="archived",
        is_permanently_archived=False,
        reversible_until__isnull=False,
        reversible_until__lt=current_time,
    )

    count = 0
    for user in expired_users:
        user.is_permanently_archived = True
        user.save(update_fields=["is_permanently_archived", "updated_at"])
        count += 1

        record_audit_event(
            actor_user_id=0,
            actor_username="scheduler",
            action="user.archival_reversibility_expired",
            result="success",
            target_type="basic_user",
            target_id=str(user.user_id),
            reason="Reversible period expired; account is now permanently non-restorable",
        )
    return count


def archive_historical_data(
    *,
    category: str,
    identifier: str,
    data_payload: dict[str, Any],
    retention_years: int = 7,
    has_pending_actions: bool = False,
    backup_reference: str = "",
    reason: str = "",
    actor_user_id: int = 0,
    actor_username: str = "system",
    ip_address: str | None = None,
    reauthenticated: bool = True,
    today: date | None = None,
) -> ArchivedRecord:
    """UC-SA-016: Archive Historical Data (AFR-SA-052..055B, BR-SA-017, BR-SA-018, BW-SA-09)."""
    current_date = today or date.today()
    validate_critical_operation_reauth(True, reauthenticated, "Historical data archival")
    validate_historical_data_archival_eligibility(category, has_pending_actions)

    if not backup_reference:
        backup_reference = f"bkp_{category}_{identifier}_{current_date.strftime('%Y%m%d')}"

    retention_until = current_date + timedelta(days=retention_years * 365)

    with transaction.atomic():
        record = ArchivedRecord.objects.create(
            category=category,
            identifier=identifier,
            data_payload=data_payload,
            retention_until=retention_until,
            backup_reference=backup_reference,
            archived_by_user_id=actor_user_id,
            reason=reason,
            status="archived",
        )

        record_audit_event(
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            action="archive.historical_data",
            result="success",
            target_type="archived_record",
            target_id=str(record.id),
            ip_address=ip_address,
            reason=reason,
            details={
                "category": category,
                "identifier": identifier,
                "retention_until": str(retention_until),
                "backup_ref": backup_reference,
            },
        )

    return record


def restore_historical_data(
    *,
    archive_id: int,
    reason: str,
    actor_user_id: int,
    actor_username: str,
    ip_address: str | None = None,
    reauthenticated: bool = True,
) -> ArchivedRecord:
    """UC-SA-019: Restore Archived Historical Data (AFR-SA-057, BW-SA-09)."""
    validate_critical_operation_reauth(True, reauthenticated, "Historical data restoration")

    with transaction.atomic():
        record = ArchivedRecord.objects.select_for_update().get(id=archive_id)
        if record.status != "archived":
            raise ValueError(f"Record cannot be restored from status: {record.status}")

        record.status = "restored"
        record.save(update_fields=["status", "updated_at"])

        record_audit_event(
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            action="archive.restore_data",
            result="success",
            target_type="archived_record",
            target_id=str(record.id),
            ip_address=ip_address,
            reason=reason,
        )

    return record


def request_permanent_purge(
    *,
    archive_id: int,
    reason: str,
    actor_user_id: int,
    actor_username: str,
    ip_address: str | None = None,
    reauthenticated: bool = True,
    today: date | None = None,
) -> PurgeRequest:
    """UC-SA-022: Request Permanent Data Purge (AFR-SA-061A, BR-SA-021, BR-SA-029, BW-SA-01).

    Enforces that the retention period has elapsed and creates a dual-authorization purge request.
    """
    current_date = today or date.today()
    validate_critical_operation_reauth(True, reauthenticated, "Permanent purge request")

    with transaction.atomic():
        record = ArchivedRecord.objects.select_for_update().get(id=archive_id)

        # Enforce BR-SA-021: Retention period must have elapsed
        validate_permanent_purge_eligibility(
            retention_until=record.retention_until,
            current_date=current_date,
            is_audit_log=(record.category.lower() in ["audit", "audit_log"]),
        )

        purge_req = PurgeRequest.objects.create(
            archived_record=record,
            requested_by_user_id=actor_user_id,
            reason=reason,
            status=PurgeRequestStatus.PENDING_IT_HEAD.value,
        )

        record.status = "purge_requested"
        record.save(update_fields=["status", "updated_at"])

        record_audit_event(
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            action="purge.request",
            result="success",
            target_type="purge_request",
            target_id=str(purge_req.id),
            ip_address=ip_address,
            reason=reason,
            details={"archive_id": record.id, "retention_until": str(record.retention_until)},
        )

    return purge_req


def authorize_permanent_purge(
    *,
    purge_request_id: int,
    decision: str,  # "approve" | "reject"
    it_head_user_id: int,
    it_head_username: str,
    rejection_reason: str = "",
    ip_address: str | None = None,
) -> PurgeRequest:
    """UC-SA-023: Authorize Permanent Data Purge (AFR-SA-061B, BR-SA-022, BW-SA-01, BW-SA-02).

    Dual authorization by IT Head.
    - If approved: marks record permanently purged (BW-SA-01).
    - If rejected: record remains retained (BW-SA-02).
    """
    with transaction.atomic():
        purge_req = (
            PurgeRequest.objects.select_for_update()
            .select_related("archived_record")
            .get(id=purge_request_id)
        )
        record = purge_req.archived_record

        new_status = validate_purge_authorization(
            status=PurgeRequestStatus(purge_req.status),
            it_head_authorized=bool(it_head_user_id),
            decision=decision,
        )

        purge_req.status = new_status.value
        purge_req.it_head_user_id = it_head_user_id
        purge_req.authorized_at = timezone.now()
        purge_req.rejection_reason = rejection_reason
        purge_req.save()

        if new_status == PurgeRequestStatus.APPROVED:
            # Permanently purge
            record.status = "purged"
            record.data_payload = {"purged": True, "purged_at": timezone.now().isoformat()}
            record.save()
        else:
            # Rejected: remains retained
            record.status = "archived"
            record.save()

        record_audit_event(
            actor_user_id=it_head_user_id,
            actor_username=it_head_username,
            action="purge.authorize",
            result="success",
            target_type="purge_request",
            target_id=str(purge_req.id),
            ip_address=ip_address,
            reason=f"IT Head decision: {decision}",
            details={"decision": decision, "archive_id": record.id},
        )

    return purge_req
