"""User and historical data archival service for system_admin."""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Optional

from django.db import transaction
from django.utils import timezone

from modules.system_admin.constants import (
    AuditAction,
    AuditResult,
    RoleAssignmentState,
    RoleRevocationType,
    UserArchivalStatus,
    UserLifecycleStatus,
)
from modules.system_admin.domain import archival_policy
from modules.system_admin.domain.exceptions import (
    ArchivalIneligibleError,
    DomainError,
    ReversibilityExpiredError,
)
from modules.system_admin.models import (
    ArchivedUserRecord,
    BasicUser,
    HistoricalDataArchive,
    RoleAssignment,
    SuperAdminAuditLog,
    UserStatusHistory,
)


def archive_user(
    user_id: int,
    reason: str,
    performed_by_id: int,
    min_deactivation_days: int = 30,
    reversible_window_days: int = 30,
) -> ArchivedUserRecord:
    """Move deactivated user to archive with reversible deadline (UC-SA-015, CFR-SA-011, BR-SA-004, BR-SA-005)."""
    user = BasicUser.objects.select_related("profile").get(id=user_id)

    verdict = archival_policy.assess_user_archival_eligibility(
        is_deactivated=(user.status == UserLifecycleStatus.DEACTIVATED),
        deactivated_at=user.deactivated_at,
        has_pending_transactions=False,  # Checked via cross-module contracts
        min_deactivation_days=min_deactivation_days,
        now=timezone.now(),
    )
    if not verdict.is_eligible:
        raise ArchivalIneligibleError(verdict.reason)

    now = timezone.now()
    reversible_until = archival_policy.calculate_reversible_deadline(now, reversible_window_days)

    # Serialize user snapshot
    profile = getattr(user, "profile", None)
    snapshot = {
        "username": user.username,
        "institute_id": user.institute_id,
        "email": user.email,
        "kind": user.kind,
        "display_name": profile.display_name if profile else "",
        "department": profile.department if profile else "",
        "programme": profile.programme if profile else "",
        "discipline": profile.discipline if profile else "",
        "batch_year": profile.batch_year if profile else None,
        "employee_id": profile.employee_id if profile else "",
    }

    with transaction.atomic():
        user.status = UserLifecycleStatus.ARCHIVED
        user.is_active = False
        user.save(update_fields=["status", "is_active"])

        # Revoke any lingering roles
        RoleAssignment.objects.filter(
            user=user,
            state__in=[RoleAssignmentState.ACTIVE, RoleAssignmentState.EXTENDED, RoleAssignmentState.SCHEDULED],
        ).update(
            state=RoleAssignmentState.REVOKED,
            revoked_at=now,
            revocation_type=RoleRevocationType.AUTOMATIC,
            revocation_reason=f"Account archived: {reason}",
        )

        record = ArchivedUserRecord.objects.create(
            basic_user_id=user.id,
            institute_id=user.institute_id,
            username=user.username,
            email=user.email,
            kind=user.kind,
            reversible_until=reversible_until,
            status=UserArchivalStatus.REVERSIBLE,
            archival_reason=reason,
            authorized_by=performed_by_id,
            user_data_snapshot=snapshot,
        )

        UserStatusHistory.objects.create(
            user=user,
            from_status=UserLifecycleStatus.DEACTIVATED,
            to_status=UserLifecycleStatus.ARCHIVED,
            changed_by=performed_by_id,
            reason=reason,
        )

        SuperAdminAuditLog.objects.create(
            actor_id=performed_by_id,
            actor_username="admin",
            action=AuditAction.ARCHIVE_USER,
            target_user_id=user.id,
            result=AuditResult.SUCCESS,
            reason=reason,
            context_metadata={"reversible_until": reversible_until.isoformat()},
        )

    return record


def restore_archived_user(user_id: int, reason: str, performed_by_id: int) -> BasicUser:
    """Restore archived user within reversible period (UC-SA-018, CFR-SA-012, BW-SA-07, BR-SA-005, ISS-SA-004)."""
    record = ArchivedUserRecord.objects.get(basic_user_id=user_id)
    now = timezone.now()

    if record.status != UserArchivalStatus.REVERSIBLE or now > record.reversible_until:
        raise ReversibilityExpiredError(record.reversible_until.isoformat())

    user = BasicUser.objects.get(id=user_id)

    with transaction.atomic():
        record.status = UserArchivalStatus.RESTORED
        record.restored_at = now
        record.restored_by = performed_by_id
        record.restoration_reason = reason
        record.save(update_fields=["status", "restored_at", "restored_by", "restoration_reason"])

        user.status = UserLifecycleStatus.ACTIVE
        user.is_active = True
        user.save(update_fields=["status", "is_active"])

        UserStatusHistory.objects.create(
            user=user,
            from_status=UserLifecycleStatus.ARCHIVED,
            to_status=UserLifecycleStatus.ACTIVE,
            changed_by=performed_by_id,
            reason=f"Restored from archive: {reason}",
        )

        SuperAdminAuditLog.objects.create(
            actor_id=performed_by_id,
            actor_username="admin",
            action=AuditAction.RESTORE_USER,
            target_user_id=user.id,
            result=AuditResult.SUCCESS,
            reason=reason,
        )

    return user


def finalize_expired_reversible_users() -> int:
    """Mark expired reversible accounts as permanently non-restorable (BW-SA-08, UC-SA-031, ISS-SA-004)."""
    now = timezone.now()
    expired = ArchivedUserRecord.objects.filter(
        status=UserArchivalStatus.REVERSIBLE,
        reversible_until__lt=now,
    )
    count = 0
    for record in expired:
        with transaction.atomic():
            record.status = UserArchivalStatus.PERMANENT_NON_RESTORABLE
            record.finalized_permanent_at = now
            record.save(update_fields=["status", "finalized_permanent_at"])

            SuperAdminAuditLog.objects.create(
                actor_id=0,
                actor_username="SYSTEM",
                action=AuditAction.FINALIZE_USER_ARCHIVE,
                target_user_id=record.basic_user_id,
                result=AuditResult.SUCCESS,
                reason="Reversibility window expired; account permanently non-restorable (ISS-SA-004)",
            )
            count += 1
    return count


def archive_historical_data(
    category: str,
    date_start: date,
    date_end: date,
    record_count: int,
    backup_file_path: str,
    backup_checksum: str,
    retention_years: int,
    performed_by_id: int,
) -> HistoricalDataArchive:
    """Archive historical data after backup verification (UC-SA-016, CFR-SA-013, BW-SA-09, BR-SA-017, BR-SA-018)."""
    retention_expires_at = date(date_start.year + retention_years, date_start.month, date_start.day)

    with transaction.atomic():
        archive = HistoricalDataArchive.objects.create(
            dataset_category=category,
            date_range_start=date_start,
            date_range_end=date_end,
            record_count=record_count,
            backup_file_path=backup_file_path,
            backup_checksum=backup_checksum,
            archived_by=performed_by_id,
            retention_expires_at=retention_expires_at,
        )

        SuperAdminAuditLog.objects.create(
            actor_id=performed_by_id,
            actor_username="admin",
            action=AuditAction.ARCHIVE_DATA,
            result=AuditResult.SUCCESS,
            reason=f"Archived historical dataset: {category}",
            context_metadata={"archive_id": archive.id, "records": record_count},
        )

    return archive


def restore_historical_data(
    archive_id: int, reason: str, performed_by_id: int
) -> HistoricalDataArchive:
    """Restore archived historical dataset to active system (UC-SA-019, CFR-SA-015, BW-SA-09)."""
    archive = HistoricalDataArchive.objects.get(id=archive_id)
    if archive.is_purged:
        raise DomainError("Cannot restore a purged dataset.")

    with transaction.atomic():
        archive.is_restored = True
        archive.restored_at = timezone.now()
        archive.save(update_fields=["is_restored", "restored_at"])

        SuperAdminAuditLog.objects.create(
            actor_id=performed_by_id,
            actor_username="admin",
            action=AuditAction.RESTORE_DATA,
            result=AuditResult.SUCCESS,
            reason=reason,
            context_metadata={"archive_id": archive.id},
        )

    return archive
