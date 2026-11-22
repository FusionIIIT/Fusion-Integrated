"""Dual-authorization permanent data purge service (BW-SA-01, BW-SA-02)."""

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.superadmin.domain.exceptions import PolicyConflictError
from modules.superadmin.domain.policy import validate_dual_authorization
from modules.superadmin.models import (
    ArchiveStatus,
    HistoricalArchiveRecord,
    PurgeRequestRecord,
    PurgeRequestStatus,
)
from modules.superadmin.services.audit import log_audit_event


@transaction.atomic
def request_permanent_purge(
    *,
    actor_user_id: int,
    archive_id: int,
    reason: str,
    ip_address: str | None = None,
) -> PurgeRequestRecord:
    # UC-SA-022 & BR-SA-021: Request permanent purge of retention-expired data.
    archive = HistoricalArchiveRecord.objects.select_for_update().filter(pk=archive_id).first()
    if not archive:
        raise NotFoundError("Archive record not found.", code="archive_not_found")

    if archive.status != ArchiveStatus.ARCHIVED:
        raise ConflictError(
            f"Cannot purge record in status {archive.status!r}.", code="invalid_archive_status"
        )

    now = timezone.now()
    if now < archive.purge_eligible_at:
        raise ConflictError(
            "Record is not yet eligible for purge. Retention expires at "
            f"{archive.purge_eligible_at.isoformat()}.",
            code="retention_period_active",
        )

    # Check for existing pending request.
    pending = PurgeRequestRecord.objects.filter(
        archive_record=archive,
        status=PurgeRequestStatus.PENDING_AUTHORIZATION,
    ).exists()
    if pending:
        raise ConflictError(
            "A purge authorization request is already pending for this record.",
            code="duplicate_purge_request",
        )

    request_rec = PurgeRequestRecord.objects.create(
        archive_record=archive,
        requested_by_user_id=actor_user_id,
        request_reason=reason,
        status=PurgeRequestStatus.PENDING_AUTHORIZATION,
    )

    log_audit_event(
        event_type="DATA_PURGE_REQUESTED",
        actor_user_id=actor_user_id,
        target_entity="PurgeRequestRecord",
        target_id=str(request_rec.pk),
        ip_address=ip_address,
        action_details={"archive_id": archive_id, "reason": reason},
    )
    return request_rec


@transaction.atomic
def authorize_permanent_purge(
    *,
    actor_user_id: int,
    request_id: int,
    action: str,
    rejection_reason: str = "",
    ip_address: str | None = None,
) -> PurgeRequestRecord:
    # UC-SA-023, BR-SA-022, BW-SA-01 & BW-SA-02: IT Head dual-authorization for purge.
    purge_req = (
        PurgeRequestRecord.objects.select_for_update()
        .select_related("archive_record")
        .filter(pk=request_id)
        .first()
    )
    if not purge_req:
        raise NotFoundError("Purge request not found.", code="purge_request_not_found")

    if purge_req.status != PurgeRequestStatus.PENDING_AUTHORIZATION:
        raise ConflictError(
            f"Purge request is already in status {purge_req.status!r}.", code="request_not_pending"
        )

    # BR-SA-022: Enforce dual authorization; authorizer cannot be the requester.
    try:
        validate_dual_authorization(purge_req.requested_by_user_id, actor_user_id)
    except PolicyConflictError as e:
        raise PermissionDeniedError(str(e), code="dual_auth_violation") from e

    now = timezone.now()
    action_upper = action.upper()

    if action_upper == "APPROVE":
        # BW-SA-01: Approved path -> permanent purge executed.
        purge_req.status = PurgeRequestStatus.COMPLETED
        purge_req.authorized_by_user_id = actor_user_id
        purge_req.authorized_at = now
        purge_req.save()

        archive = purge_req.archive_record
        archive.status = ArchiveStatus.PURGED
        archive.payload = {"_purged": True, "purged_at": now.isoformat()}
        archive.save(update_fields=["status", "payload", "updated_at"])

        log_audit_event(
            event_type="DATA_PURGE_EXECUTED",
            actor_user_id=actor_user_id,
            target_entity="PurgeRequestRecord",
            target_id=str(request_id),
            ip_address=ip_address,
            action_details={"archive_id": archive.pk, "status": "PURGED"},
        )
    elif action_upper == "REJECT":
        # BW-SA-02: Rejected path -> request marked rejected, data remains archived.
        purge_req.status = PurgeRequestStatus.REJECTED
        purge_req.authorized_by_user_id = actor_user_id
        purge_req.authorized_at = now
        purge_req.rejection_reason = rejection_reason
        purge_req.save()

        log_audit_event(
            event_type="DATA_PURGE_REJECTED",
            actor_user_id=actor_user_id,
            target_entity="PurgeRequestRecord",
            target_id=str(request_id),
            ip_address=ip_address,
            action_details={
                "archive_id": purge_req.archive_record.pk,
                "rejection_reason": rejection_reason,
            },
        )
    else:
        raise ConflictError(
            f"Invalid authorization action: {action!r}.", code="invalid_purge_action"
        )

    return purge_req
