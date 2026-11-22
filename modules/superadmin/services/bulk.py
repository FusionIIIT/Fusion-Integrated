"""Bulk operations service with size bounding and validation (BR-SA-030)."""

import csv
import io

from django.db import transaction

from core.api.exceptions import BadRequestError
from modules.superadmin.domain.exceptions import DomainValidationError
from modules.superadmin.domain.validators import validate_batch_size
from modules.superadmin.models import UserAccountRecord, UserActivationStatus
from modules.superadmin.services.audit import log_audit_event
from modules.superadmin.services.users import create_user_account


def bulk_create_users(
    *,
    actor_user_id: int,
    csv_content: str,
    ip_address: str | None = None,
) -> dict:
    # UC-SA-006 & BR-SA-030: CSV batch user creation with pre-validation and limit check.
    reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(reader)

    try:
        validate_batch_size(len(rows))
    except DomainValidationError as e:
        raise BadRequestError(str(e), code="batch_limit_exceeded") from e

    created_records = []
    errors = []

    for i, row in enumerate(rows, start=1):
        try:
            with transaction.atomic():
                user_id = int(row.get("user_id", "0"))
                institute_id = row.get("institute_id", "").strip()
                email = row.get("email", "").strip()
                user_type = row.get("user_type", "").strip()
                dept = row.get("department", "").strip()
                prog = row.get("program", "").strip()
                batch = row.get("batch", "").strip()

                acc = create_user_account(
                    actor_user_id=actor_user_id,
                    user_id=user_id,
                    institute_id=institute_id,
                    email=email,
                    user_type=user_type,
                    department=dept,
                    program=prog,
                    batch=batch,
                    ip_address=ip_address,
                )
                created_records.append(acc.user_id)
        except Exception as e:  # noqa: BLE001
            errors.append({"row": i, "user_id": row.get("user_id"), "error": str(e)})

    log_audit_event(
        event_type="BULK_USERS_CREATED",
        actor_user_id=actor_user_id,
        target_entity="UserAccountRecord",
        target_id=f"batch_{len(rows)}",
        ip_address=ip_address,
        action_details={"total": len(rows), "success": len(created_records), "failed": len(errors)},
    )

    return {
        "total_submitted": len(rows),
        "successful_creations": len(created_records),
        "created_user_ids": created_records,
        "errors": errors,
    }


@transaction.atomic
def bulk_update_user_status(
    *,
    actor_user_id: int,
    user_ids: list[int],
    target_status: str,
    reason: str,
    ip_address: str | None = None,
) -> dict:
    # UC-SA-007 & BR-SA-030: Bulk status update with batch limit enforcement.
    try:
        validate_batch_size(len(user_ids))
    except DomainValidationError as e:
        raise BadRequestError(str(e), code="batch_limit_exceeded") from e

    status_upper = target_status.upper()
    if status_upper not in (UserActivationStatus.ACTIVE, UserActivationStatus.DEACTIVATED):
        raise BadRequestError(
            f"Unsupported bulk status transition to {target_status!r}.", code="invalid_status"
        )

    updated = UserAccountRecord.objects.filter(user_id__in=user_ids).update(
        activation_status=status_upper,
        deactivation_reason=reason if status_upper == UserActivationStatus.DEACTIVATED else "",
    )

    log_audit_event(
        event_type="BULK_USER_STATUS_UPDATED",
        actor_user_id=actor_user_id,
        target_entity="UserAccountRecord",
        target_id=f"bulk_{len(user_ids)}",
        ip_address=ip_address,
        action_details={"target_status": status_upper, "updated_count": updated, "reason": reason},
    )

    return {"updated_count": updated, "target_status": status_upper}
