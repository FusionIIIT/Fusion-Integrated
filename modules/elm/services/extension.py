"""Extension services for ongoing leave (EL-UC-009, CW-EL-03).

Enforces BR-EL-025.
"""
from __future__ import annotations

import datetime
from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.domain.constants import CONTINUOUS_COUNT_CATEGORIES, LeaveCategory
from modules.elm.domain.counting import calculate_chargeable_days
from modules.elm.models import LeaveApplication, LeaveBalance, LeaveExtensionRequest
from modules.elm.services.audit import record_audit


def request_extension(
    actor,
    application_id: int,
    new_end_date: datetime.date,
    reason: str,
    substitute_id: int | None = None,
) -> LeaveExtensionRequest:
    """Request extension of ongoing EL/COL/VL (EL-UC-009, BR-EL-025)."""
    user_id = getattr(actor, "user_id", None) or getattr(actor, "id", None)

    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().select_related("leave_type").get(id=application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError("Leave application not found.", code="not_found")

        if app.employee_id != user_id:
            raise PermissionDeniedError("Cannot request extension for another employee's leave.", code="permission_denied")

        if app.status != "APPROVED":
            raise ConflictError("Only approved leave can be extended.", code="invalid_state")

        # BR-EL-025: Extension is available only for EL, COL, VL
        if LeaveCategory(app.leave_type.code) not in CONTINUOUS_COUNT_CATEGORIES:
            raise BadRequestError(
                f"Extension is only applicable for EL, COL, or VL, not '{app.leave_type.code}'.",
                code="extension_category_invalid",
            )

        if new_end_date <= app.end_date:
            raise BadRequestError(
                f"New end date ({new_end_date}) must be after current end date ({app.end_date}).",
                code="invalid_dates",
            )

        # Calculate incremental days (BR-EL-025: posts only the incremental additional leave period)
        incremental_start = app.end_date + datetime.timedelta(days=1)
        incremental_days = calculate_chargeable_days(
            category=app.leave_type.code,
            start_date=incremental_start,
            end_date=new_end_date,
        )

        # Verify sufficient balance for incremental days
        balance = LeaveBalance.objects.get(
            employee_id=user_id,
            leave_type=app.leave_type,
            year=app.start_date.year,
        )
        available = float(balance.allotted - balance.used)
        if available < incremental_days:
            raise ConflictError(
                f"Insufficient balance for extension. Required: {incremental_days}, Available: {available}.",
                code="insufficient_balance",
            )

        ext = LeaveExtensionRequest.objects.create(
            original_application=app,
            employee_id=user_id,
            start_date=incremental_start,
            end_date=new_end_date,
            days=incremental_days,
            reason=reason,
            substitute_id=substitute_id,
            substitute_status="PENDING" if substitute_id else "NONE",
            status="AWAITING_UNIT_HEAD",
        )

        record_audit(
            application=app,
            actor_id=user_id,
            action="REQUEST_EXTENSION",
            from_status=app.status,
            to_status=app.status,
            remarks=f"Extension requested to {new_end_date} (+{incremental_days} days).",
        )

    return ext


def decide_extension(
    actor,
    extension_id: int,
    approve: bool,
    remarks: str = "",
) -> LeaveExtensionRequest:
    """Sanctioning authority decides on extension (BR-EL-025)."""
    user_id = getattr(actor, "user_id", None) or getattr(actor, "id", None)

    with transaction.atomic():
        try:
            ext = LeaveExtensionRequest.objects.select_for_update().select_related("original_application", "original_application__leave_type").get(id=extension_id)
        except LeaveExtensionRequest.DoesNotExist:
            raise NotFoundError("Extension request not found.", code="not_found")

        app = ext.original_application
        if app.employee_id == user_id:
            raise PermissionDeniedError("Cannot decide on own extension.", code="self_review")

        if approve:
            # Deduct incremental balance
            balance = LeaveBalance.objects.select_for_update().get(
                employee_id=app.employee_id,
                leave_type=app.leave_type,
                year=app.start_date.year,
            )
            balance.used += ext.days
            balance.save(update_fields=["used", "updated_at"])

            # Extend original application end date and days
            app.end_date = ext.end_date
            app.days += ext.days
            app.save(update_fields=["end_date", "days", "updated_at"])

            ext.status = "APPROVED"
            action_name = "EXTENSION_APPROVED"
        else:
            # Rejection preserves original approved leave unchanged (BR-EL-025)
            ext.status = "REJECTED"
            action_name = "EXTENSION_REJECTED"

        ext.approver_id = user_id
        ext.remarks = remarks
        ext.decided_at = timezone.now()
        ext.save()

        record_audit(
            application=app,
            actor_id=user_id,
            action=action_name,
            from_status="APPROVED",
            to_status="APPROVED",
            remarks=remarks,
        )

    return ext
