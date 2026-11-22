from datetime import UTC, datetime

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.badms.domain.state_machine import (
    STORAGE_APPROVED,
    InvalidStateTransitionError,
    UnauthorizedTransitionActorError,
    transition_storage_extension,
)
from modules.badms.domain.storage import (
    QuotaNotFullError,
    validate_storage_extension_eligibility,
)
from modules.badms.models import (
    StorageExtensionRequest,
    StorageLedgerEntry,
    UserStorageQuota,
)
from modules.badms.selectors import resolve_actor_department
from modules.badms.services.audit import log_audit_event


@transaction.atomic
def submit_storage_extension(
    actor, requested_extension_bytes: int, justification: str, department: str = ""
) -> StorageExtensionRequest:
    user_id = getattr(actor, "user_id", None) or 0
    dept = department or resolve_actor_department(actor, default="General")

    quota_obj, created = UserStorageQuota.objects.select_for_update().get_or_create(
        user_id=user_id,
        defaults={"allocated_quota_bytes": 10737418240, "used_storage_bytes": 0, "is_full": False},
    )
    if created:
        StorageLedgerEntry.objects.create(
            quota=quota_obj,
            amount_bytes=10737418240,
            entry_type=StorageLedgerEntry.ENTRY_CREDIT,
            reference="initial_baseline_quota",
            created_by_user_id=user_id,
        )

    try:
        validate_storage_extension_eligibility(
            quota_obj.used_storage_bytes, quota_obj.allocated_quota_bytes
        )
    except QuotaNotFullError as err:
        raise ConflictError(str(err)) from err

    target_state = transition_storage_extension("none", "submit", "user")

    ext_req = StorageExtensionRequest.objects.create(
        requester_user_id=user_id,
        department=dept,
        current_usage_bytes=quota_obj.used_storage_bytes,
        current_quota_bytes=quota_obj.allocated_quota_bytes,
        requested_extension_bytes=requested_extension_bytes,
        justification=justification,
        status=target_state,
    )
    log_audit_event(
        "storage_extension_submitted", actor, "StorageExtensionRequest", ext_req.id, dept
    )
    return ext_req


@transaction.atomic
def decide_storage_extension(
    actor, request_id: int, decision: str, remarks: str = ""
) -> StorageExtensionRequest:
    user_id = getattr(actor, "user_id", None) or 0
    dept = resolve_actor_department(actor, default="")

    ext_req = StorageExtensionRequest.objects.select_for_update().filter(id=request_id).first()
    if not ext_req:
        raise NotFoundError("Storage extension request not found.")

    if ext_req.department != dept and dept:
        raise NotFoundError("Storage extension request not found in your departmental scope.")

    event = "approve" if decision.lower() == "approve" else "reject"
    try:
        next_state = transition_storage_extension(ext_req.status, event, "hod")
    except (InvalidStateTransitionError, UnauthorizedTransitionActorError) as err:
        raise ConflictError(str(err)) from err

    ext_req.status = next_state
    ext_req.hod_reviewed_by_user_id = user_id
    ext_req.hod_decision_at = datetime.now(UTC)
    ext_req.hod_remarks = remarks
    ext_req.save()

    if next_state == STORAGE_APPROVED:
        quota_obj = (
            UserStorageQuota.objects.select_for_update()
            .filter(user_id=ext_req.requester_user_id)
            .first()
        )
        if quota_obj:
            StorageLedgerEntry.objects.create(
                quota=quota_obj,
                amount_bytes=ext_req.requested_extension_bytes,
                entry_type=StorageLedgerEntry.ENTRY_CREDIT,
                reference=f"extension_request_{ext_req.id}",
                created_by_user_id=user_id,
            )
            quota_obj.allocated_quota_bytes += ext_req.requested_extension_bytes
            quota_obj.is_full = quota_obj.used_storage_bytes >= quota_obj.allocated_quota_bytes
            quota_obj.save(update_fields=["allocated_quota_bytes", "is_full"])

    log_audit_event(
        f"storage_extension_{next_state}",
        actor,
        "StorageExtensionRequest",
        ext_req.id,
        ext_req.department,
    )
    return ext_req
