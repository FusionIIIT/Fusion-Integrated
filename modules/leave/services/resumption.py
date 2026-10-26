"""Resumption of duty services (EL-UC-010, EL-UC-011, BR-EL-027, BR-EL-028, WF-EL-05)."""

from __future__ import annotations

import datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError
from modules.leave.domain import (
    RESUMPTION_REVIEWED_EARLY,
    RESUMPTION_REVIEWED_LATE,
    RESUMPTION_REVIEWED_NORMAL,
    RESUMPTION_SUBMITTED,
    InvalidStateTransitionError,
    LeaveCalculationError,
    calculate_leave_days,
    validate_transition,
)
from modules.leave.models import (
    HolidayCalendar,
    LeaveActionHistory,
    LeaveApplication,
    LeaveLedgerEntry,
)
from modules.leave.selectors.applications import get_application_by_id
from modules.leave.selectors.balances import get_or_create_balance
from modules.leave.services.notifications import enqueue as enqueue_notification


def _safe_calculate_leave_days(*args, **kwargs) -> Decimal:
    try:
        return calculate_leave_days(*args, **kwargs)
    except LeaveCalculationError as exc:
        raise BadRequestError(exc.message, code=exc.code) from exc


def _safe_validate_transition(current: str, target: str) -> None:
    try:
        validate_transition(current, target)
    except InvalidStateTransitionError as exc:
        raise ConflictError(exc.message, code=exc.code) from exc


@transaction.atomic
def submit_resumption_declaration(
    *,
    user_id: int,
    application_id: int,
    resumption_date: datetime.date,
    remarks: str = "",
) -> LeaveApplication:
    """Employee reports back to duty after EL, COL, or VL (EL-UC-010)."""
    app = get_application_by_id(application_id, user_id=user_id, for_update=True)
    if app.status != "approved":
        raise ConflictError(
            f"Cannot submit resumption for application in status {app.status!r}.",
            code="not_approved",
        )
    if app.resumption_reviewed_at is not None:
        raise ConflictError(
            "Resumption has already been reviewed for this leave.",
            code="resumption_already_reviewed",
        )
    if app.category not in {"EL", "COL", "VL"}:
        raise BadRequestError(
            "Formal resumption review applies only to EL, COL, and VL.",
            code="resumption_not_applicable",
        )
    if resumption_date < app.start_date:
        raise BadRequestError(
            "Resumption date cannot be before the leave start date.", code="invalid_resumption_date"
        )

    _safe_validate_transition(app.status, RESUMPTION_SUBMITTED)
    app.resumption_date = resumption_date
    app.resumption_remarks = remarks
    app.status = "resumption_submitted"
    app.save(update_fields=["resumption_date", "resumption_remarks", "status", "updated_at"])

    LeaveActionHistory.objects.create(
        application=app,
        actor_user_id=user_id,
        actor_role="employee",
        action="resumption_submitted",
        remarks=f"Resumed duty on {resumption_date}. {remarks}",
    )
    enqueue_notification(
        recipient_user_id=app.sanctioning_authority_user_id or app.establishment_user_id,
        topic="resumption.assigned",
        dedupe_key=f"leave:{app.pk}:resumption-assigned",
        subject="Leave resumption requires review",
        body=f"Resumption for leave #{app.pk} is awaiting review.",
    )

    return app


@transaction.atomic
def review_resumption_declaration(
    *,
    reviewer_user_id: int,
    application_id: int,
    remarks: str = "",
) -> LeaveApplication:
    """Sanctioning Authority reviews resumption and adjusts balance (EL-UC-011, BR-EL-028)."""
    app = get_application_by_id(application_id, for_update=True)
    if app.status != "resumption_submitted":
        raise ConflictError(
            "Application is not pending resumption review.", code="not_resumption_submitted"
        )

    if app.resumption_date == app.end_date:
        reviewed_status = RESUMPTION_REVIEWED_NORMAL
    elif app.resumption_date < app.end_date:
        reviewed_status = RESUMPTION_REVIEWED_EARLY
    else:
        reviewed_status = RESUMPTION_REVIEWED_LATE
    _safe_validate_transition(app.status, reviewed_status)

    balance = get_or_create_balance(app.user_id, app.start_date.year)
    if app.resumption_date == app.start_date:
        # Returning on the first approved day means no leave days were actually used.
        actual_days = Decimal("0.0")
    else:
        actual_end_date = (
            app.end_date
            if app.resumption_date == app.end_date
            else app.resumption_date - datetime.timedelta(days=1)
        )

        # Recalculate days count for the actual interval, not just the approved dates.
        holidays = HolidayCalendar.objects.filter(year=app.start_date.year, is_published=True)
        closed_dates = {h.date for h in holidays if h.kind == "closed"}
        actual_days = _safe_calculate_leave_days(
            category=app.category,
            start_date=app.start_date,
            end_date=actual_end_date,
            closed_holidays=closed_dates,
        )

    days_diff = (
        Decimal("0.0") if app.resumption_date == app.end_date else app.days_count - actual_days
    )
    if days_diff > Decimal("0.0"):
        # Early resumption: credit back unused days
        balance.credit(app.category, days_diff)
        balance.save()
        LeaveLedgerEntry.objects.create(
            balance=balance,
            user_id=app.user_id,
            category=app.category,
            entry_type="adjustment",
            change_amount=days_diff,
            balance_after=balance.get_category_balance(app.category),
            reference_id=app.pk,
            remarks=f"Early resumption on {app.resumption_date}: restored {days_diff} days",
        )
    elif days_diff < Decimal("0.0"):
        # Late resumption: deduct additional days
        extra = abs(days_diff)
        balance.deduct(app.category, extra)
        balance.save()
        LeaveLedgerEntry.objects.create(
            balance=balance,
            user_id=app.user_id,
            category=app.category,
            entry_type="adjustment",
            change_amount=-extra,
            balance_after=balance.get_category_balance(app.category),
            reference_id=app.pk,
            remarks=f"Late resumption on {app.resumption_date}: deducted additional {extra} days",
        )

    app.actual_days_count = actual_days
    app.resumption_reviewed_at = timezone.now()
    app.status = reviewed_status
    app.save(update_fields=["actual_days_count", "resumption_reviewed_at", "status", "updated_at"])

    LeaveActionHistory.objects.create(
        application=app,
        actor_user_id=reviewer_user_id,
        actor_role="authority",
        action="resumption_reviewed",
        remarks=remarks,
    )
    enqueue_notification(
        recipient_user_id=app.user_id,
        topic="resumption.reviewed",
        dedupe_key=f"leave:{app.pk}:resumption-reviewed",
        subject="Leave resumption reviewed",
        body=f"Resumption for leave #{app.pk} has been reviewed.",
    )

    return app
