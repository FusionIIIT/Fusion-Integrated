"""Dual-authorization permanent purge service for system_admin (CW-SA-01, BW-SA-01..02)."""
from __future__ import annotations

from datetime import date
from typing import Optional

from django.db import transaction
from django.utils import timezone

from modules.system_admin.constants import (
    AuditAction,
    AuditResult,
    NotificationChannel,
    PurgeRequestStatus,
)
from modules.system_admin.domain.exceptions import (
    DomainError,
    PurgeDualAuthRequiredError,
)
from modules.system_admin.models import (
    HistoricalDataArchive,
    PurgeRequest,
    SuperAdminAuditLog,
)
from modules.system_admin.services import notifications


def request_permanent_purge(
    archive_id: int, reason: str, super_admin_id: int
) -> PurgeRequest:
    """Request permanent purge of retention-expired data (UC-SA-022, CFR-SA-016, BR-SA-021)."""
    archive = HistoricalDataArchive.objects.get(id=archive_id)

    if archive.is_purged:
        raise DomainError("Dataset is already purged.")
    if date.today() < archive.retention_expires_at:
        raise DomainError(
            f"Retention period has not yet elapsed (retention expires on {archive.retention_expires_at}) (BR-SA-021)."
        )

    with transaction.atomic():
        req = PurgeRequest.objects.create(
            archive=archive,
            status=PurgeRequestStatus.PENDING_IT_HEAD,
            requested_by=super_admin_id,
            request_reason=reason,
        )

        SuperAdminAuditLog.objects.create(
            actor_id=super_admin_id,
            actor_username="admin",
            action=AuditAction.PURGE_REQUEST,
            result=AuditResult.SUCCESS,
            reason=reason,
            context_metadata={"archive_id": archive.id, "purge_request_id": req.id},
        )

    return req


def authorize_permanent_purge(
    request_id: int, it_head_id: int, approved: bool, comments: str = ""
) -> PurgeRequest:
    """IT Head authorizes or rejects permanent purge (UC-SA-023, CW-SA-01, BW-SA-01, BW-SA-02, BR-SA-022)."""
    req = PurgeRequest.objects.select_related("archive").get(id=request_id)

    if req.status != PurgeRequestStatus.PENDING_IT_HEAD:
        raise DomainError(f"Purge request is not pending authorization (current: '{req.status}').")

    # Dual authorization check: IT Head must be different from requesting Super Admin (BR-SA-022)
    if req.requested_by == it_head_id:
        raise PurgeDualAuthRequiredError("Distinct IT Head authorization required; requester cannot self-authorize.")

    now = timezone.now()

    with transaction.atomic():
        req.it_head_id = it_head_id
        req.it_head_decision_at = now
        req.it_head_comments = comments

        if approved:
            # BW-SA-01: Approved path
            req.status = PurgeRequestStatus.APPROVED
            req.purged_at = now
            req.purge_execution_summary = {
                "deleted_backup": req.archive.backup_file_path,
                "records_purged": req.archive.record_count,
            }
            req.archive.is_purged = True
            req.archive.save(update_fields=["is_purged"])
            req.status = PurgeRequestStatus.PURGED
            req.save()

            SuperAdminAuditLog.objects.create(
                actor_id=it_head_id,
                actor_username="it_head",
                action=AuditAction.PURGE_AUTHORIZE,
                result=AuditResult.SUCCESS,
                reason=f"Approved and permanently purged: {comments}",
                context_metadata={"purge_request_id": req.id, "outcome": "purged"},
            )
        else:
            # BW-SA-02: Rejected path
            req.status = PurgeRequestStatus.REJECTED
            req.save()

            SuperAdminAuditLog.objects.create(
                actor_id=it_head_id,
                actor_username="it_head",
                action=AuditAction.PURGE_AUTHORIZE,
                result=AuditResult.SUCCESS,
                reason=f"Rejected purge request: {comments}",
                context_metadata={"purge_request_id": req.id, "outcome": "rejected"},
            )

        # Notify the requesting Super Admin
        notifications.queue_notification(
            recipient_id=req.requested_by,
            email="",
            channel=NotificationChannel.IN_APP,
            template_code="purge_decision",
            subject="Purge Request Decision",
            body=f"Your purge request for archive #{req.archive_id} was {'APPROVED' if approved else 'REJECTED'} by IT Head.",
        )

    return req
