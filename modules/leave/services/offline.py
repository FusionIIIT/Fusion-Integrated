"""Offline leave recording service (EL-UC-016, BR-EL-029)."""
from __future__ import annotations

import datetime
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError
from modules.leave.models import (
    HolidayCalendar,
    LeaveActionHistory,
    LeaveApplication,
    LeaveLedgerEntry,
)
from modules.leave.domain.categories import is_eligible_for_category
from modules.leave.domain.counting import calculate_leave_days
from modules.leave.selectors.applications import get_active_overlapping_leaves
from modules.leave.selectors.balances import get_or_create_balance


@transaction.atomic
def record_offline_leave(
    *,
    admin_user_id: int,
    employee_user_id: int,
    category: str,
    start_date: datetime.date,
    end_date: datetime.date,
    days_count: Decimal,
    offline_reference_no: str,
    offline_sanction_date: datetime.date,
    purpose: str,
) -> LeaveApplication:
    """Retrospectively record leave already sanctioned offline (EL-UC-016)."""
    if not offline_reference_no.strip():
        raise BadRequestError("Offline reference/sanction order number is required.", code="missing_reference")
    if end_date < start_date or start_date.year != end_date.year:
        raise BadRequestError("Offline leave dates must be a valid single-year interval.", code="invalid_dates")
    from modules.directory import contracts as directory
    employee = directory.get_users([employee_user_id]).get(employee_user_id)
    if employee is None or employee.kind not in {"faculty", "staff"}:
        raise BadRequestError("Offline leave can only be recorded for an active employee.", code="invalid_employee")

    balance = get_or_create_balance(employee_user_id, start_date.year)
    if not is_eligible_for_category(category, balance.is_faculty):
        raise BadRequestError("Employee is not eligible for this leave category.", code="ineligible_category")
    holidays = HolidayCalendar.objects.filter(year=start_date.year, is_published=True)
    closed_dates = {row.date for row in holidays if row.kind == "closed"}
    rh_dates = {row.date for row in holidays if row.kind == "restricted"}
    expected_days = calculate_leave_days(category, start_date, end_date,
                                         closed_holidays=closed_dates, rh_holidays=rh_dates)
    if expected_days != days_count:
        raise BadRequestError("Entered leave days do not match the configured calendar calculation.", code="invalid_days_count")
    if get_active_overlapping_leaves(employee_user_id, start_date, end_date).exists():
        raise ConflictError("Offline record overlaps an existing pending or approved leave.", code="overlapping_leave")
    available = balance.get_category_balance(category)
    if available < days_count:
        raise ConflictError(
            f"Cannot synchronize: employee has insufficient {category} balance ({available} available).",
            code="insufficient_balance",
        )

    balance.deduct(category, days_count)
    balance.save()

    app = LeaveApplication.objects.create(
        user_id=employee_user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        days_count=days_count,
        purpose=purpose,
        status="approved",
        is_offline_sanctioned=True,
        offline_reference_no=offline_reference_no,
        offline_sanction_date=offline_sanction_date,
        sanctioned_at=timezone.now(),
    )

    LeaveLedgerEntry.objects.create(
        balance=balance,
        user_id=employee_user_id,
        category=category,
        entry_type="debit",
        change_amount=-days_count,
        balance_after=balance.get_category_balance(category),
        reference_id=app.pk,
        remarks=f"Offline sanction sync: ref {offline_reference_no}",
    )

    LeaveActionHistory.objects.create(
        application=app,
        actor_user_id=admin_user_id,
        actor_role="leave_admin",
        action="offline_synchronized",
        remarks=f"Offline order: {offline_reference_no}",
    )

    return app
