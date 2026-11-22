"""Archival lifecycle, restoration, and dual-authorization purge service."""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from django.db import transaction

from modules.system_admin.domain.exceptions import (
    DomainValidationError,
    PurgeDualAuthError,
    UserNotFoundError,
)
from modules.system_admin.domain.rules import (
    validate_archival_eligibility,
    validate_purge_eligibility,
    validate_restoration_window,
)
from modules.system_admin.domain.state_machines import (
    transition_purge_state,
    transition_user_state,
)
from modules.system_admin.models.archive import (
    ArchivedUserRecord,
    HistoricalDatasetArchive,
    PermanentPurgeRequest,
)
from modules.system_admin.models.audit import SystemAuditLog
from modules.system_admin.models.user_account import UserAccount


@transaction.atomic
def archive_user(
    *,
    user_id: int,
    reason: str,
    retention_option: str = "standard_7yr",
    reversible_days: int = 90,
    actor_id: int = 1,
    ip_address: str | None = None,
) -> ArchivedUserRecord:
    """Archive a deactivated user account (UC-SA-015, BW-SA-07, BR-SA-004, BR-SA-019)."""
    try:
        user = UserAccount.objects.select_for_update().get(user_id=user_id)
    except UserAccount.DoesNotExist as err:
        raise UserNotFoundError(f"User {user_id} does not exist.") from err

    now = datetime.now(UTC)
    validate_archival_eligibility(
        status=user.status,
        deactivation_date=user.deactivated_at,
        current_time=now,
        min_interval_days=0,
        has_pending_transactions=False,
    )

    next_state = transition_user_state(user.status, "archive", "super_admin")
    user.status = next_state
    user.save(update_fields=["status", "updated_at"])

    reversible_until = now + timedelta(days=reversible_days)

    snapshot = {
        "user_id": user.user_id,
        "institute_id": user.institute_id,
        "username": user.username,
        "email": user.email,
        "user_type": user.user_type,
        "name": user.name,
        "department": user.department,
        "programme": user.programme,
        "discipline": user.discipline,
        "batch_year": user.batch_year,
    }

    archive_record, _ = ArchivedUserRecord.objects.update_or_create(
        user_id=user_id,
        defaults={
            "institute_id": user.institute_id,
            "username": user.username,
            "email": user.email,
            "user_type": user.user_type,
            "reason": reason,
            "retention_option": retention_option,
            "archived_by": actor_id,
            "archived_at": now,
            "reversible_until": reversible_until,
            "is_permanent": False,
            "snapshot": snapshot,
        },
    )

    SystemAuditLog.objects.create(
        actor_id=actor_id,
        action="system_admin.archive.manage",
        target_id=str(user_id),
        ip_address=ip_address,
        result="success",
        context={
            "operation": "archive_user",
            "retention_option": retention_option,
            "reversible_until": reversible_until.isoformat(),
        },
    )

    return archive_record


@transaction.atomic
def restore_archived_user(
    *,
    user_id: int,
    reason: str,
    actor_id: int = 1,
    ip_address: str | None = None,
) -> UserAccount:
    """Restore an archived user within the reversible window (UC-SA-018, BW-SA-07, BR-SA-005)."""
    try:
        archive_record = ArchivedUserRecord.objects.get(user_id=user_id)
    except ArchivedUserRecord.DoesNotExist as err:
        raise DomainValidationError(f"Archived record for user {user_id} not found.") from err

    now = datetime.now(UTC)
    validate_restoration_window(
        is_permanent=archive_record.is_permanent,
        archived_at=archive_record.archived_at,
        window_days=90,
        current_time=now,
    )

    user = UserAccount.objects.get(user_id=user_id)
    next_state = transition_user_state(user.status, "restore", "super_admin")
    user.status = next_state
    user.save(update_fields=["status", "updated_at"])

    # Remove or mark archived record
    archive_record.delete()

    SystemAuditLog.objects.create(
        actor_id=actor_id,
        action="system_admin.archive.manage",
        target_id=str(user_id),
        ip_address=ip_address,
        result="success",
        context={"operation": "restore_user", "reason": reason},
    )

    return user


@transaction.atomic
def archive_historical_dataset(
    *,
    category: str,
    description: str,
    date_range_start: date,
    date_range_end: date,
    backup_reference: str,
    record_count: int = 0,
    actor_id: int = 1,
    ip_address: str | None = None,
) -> HistoricalDatasetArchive:
    """Archive historical dataset records (UC-SA-020, BR-SA-020)."""
    if date_range_start > date_range_end:
        raise DomainValidationError("Start date cannot be after end date.")

    dataset = HistoricalDatasetArchive.objects.create(
        category=category,
        description=description,
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        record_count=record_count,
        backup_reference=backup_reference,
        archived_by=actor_id,
        is_restored=False,
    )

    SystemAuditLog.objects.create(
        actor_id=actor_id,
        action="system_admin.archive.manage",
        target_id=str(dataset.id),
        ip_address=ip_address,
        result="success",
        context={
            "operation": "archive_dataset",
            "category": category,
            "records": record_count,
        },
    )

    return dataset


@transaction.atomic
def request_permanent_purge(
    *,
    dataset_identifier: str,
    retention_years: float,
    reason: str,
    actor_id: int = 1,
    ip_address: str | None = None,
) -> PermanentPurgeRequest:
    """Step 1 of dual authorization: Super Admin requests permanent purge.

    Enforces UC-SA-022, BW-SA-01, and BR-SA-021.
    """
    now = datetime.now(UTC)
    archived_at = now - timedelta(days=int(retention_years * 365.25))
    validate_purge_eligibility(
        archived_at=archived_at,
        retention_years=7,
        current_time=now,
    )

    purge_request = PermanentPurgeRequest.objects.create(
        dataset_identifier=dataset_identifier,
        requested_by=actor_id,
        retention_verified=True,
        reason=reason,
        status="pending_it_head",
    )

    SystemAuditLog.objects.create(
        actor_id=actor_id,
        action="system_admin.archive.manage",
        target_id=str(purge_request.id),
        ip_address=ip_address,
        result="success",
        context={
            "operation": "request_permanent_purge",
            "dataset_identifier": dataset_identifier,
            "retention_years": retention_years,
        },
    )

    return purge_request


@transaction.atomic
def authorize_permanent_purge(
    *,
    purge_request_id: int,
    approve: bool,
    it_head_user_id: int,
    remarks: str = "",
    ip_address: str | None = None,
) -> PermanentPurgeRequest:
    """Step 2 of dual authorization: IT Head approves or rejects permanent purge.

    Enforces UC-SA-023, BW-SA-01..02, and BR-SA-022.
    """
    try:
        purge_req = PermanentPurgeRequest.objects.select_for_update().get(id=purge_request_id)
    except PermanentPurgeRequest.DoesNotExist as err:
        raise DomainValidationError(
            f"Purge request {purge_request_id} does not exist."
        ) from err

    # Dual authorization constraint: requester and authorizer must differ (BR-SA-022)
    if purge_req.requested_by == it_head_user_id:
        msg = "Dual authorization violation: Purge requester and IT Head cannot be same person."
        raise PurgeDualAuthError(msg)

    if purge_req.status != "pending_it_head":
        raise DomainValidationError(
            f"Purge request is in state '{purge_req.status}', cannot decide."
        )

    now = datetime.now(UTC)
    event = "approve" if approve else "reject"
    next_state = transition_purge_state("pending_it_head", event, "it_head")

    final_status = "purged" if next_state == "permanently_purged" else "rejected"
    purge_req.status = final_status
    purge_req.it_head_user_id = it_head_user_id
    purge_req.it_head_decided_at = now
    purge_req.it_head_remarks = remarks
    purge_req.save()

    SystemAuditLog.objects.create(
        actor_id=it_head_user_id,
        action="system_admin.archive.manage",
        target_id=str(purge_req.id),
        ip_address=ip_address,
        result="success",
        context={
            "operation": "authorize_purge",
            "approved": approve,
            "status": final_status,
            "remarks": remarks,
        },
    )

    return purge_req
