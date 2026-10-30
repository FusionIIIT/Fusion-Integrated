from datetime import date
from decimal import Decimal
from django.db import transaction
from rest_framework.exceptions import ValidationError

from modules.elm.domain.year_end import compute_year_end_outcomes
from modules.elm.models import (
    ApplicationTransition,
    EmployeeLeaveBalance,
    HolidayCalendar,
    LeaveApplication,
    YearEndTransaction,
)
from modules.elm.selectors.balances import get_user_balances
from modules.elm.services.authz import require


@transaction.atomic
def record_offline_leave(principal, data: dict) -> LeaveApplication:
    """Retrospectively record leave already sanctioned offline (Section 12)."""
    require(principal, "leave_elm.admin.manage")

    emp_user_id = data["user_id"]
    category = data["leave_category"]
    start_date = data["start_date"]
    end_date = data["end_date"]
    leave_days = Decimal(str(data["calculated_days"]))
    reference = data.get("offline_sanction_reference", "Offline Sanction")

    app = LeaveApplication.objects.create(
        user_id=emp_user_id,
        leave_category=category,
        start_date=start_date,
        end_date=end_date,
        calculated_days=leave_days,
        reason=data.get("reason", "Offline sanctioned leave"),
        status="approved",
        final_decision="approved",
        is_offline_sanctioned=True,
        offline_sanction_reference=reference,
    )

    bal = EmployeeLeaveBalance.objects.filter(
        user_id=emp_user_id, year=start_date.year, leave_category=category
    ).first()
    if bal:
        bal.availed_days += leave_days
        bal.save()

    ApplicationTransition.objects.create(
        application=app,
        from_status="none",
        to_status="approved",
        actor_user_id=principal.user_id,
        remarks=f"Offline sanctioned leave recorded. Ref: {reference}",
    )
    return app


@transaction.atomic
def run_year_end_processing(year: int, user_ids: list[int], is_faculty_map: dict[int, bool]) -> list[YearEndTransaction]:
    """Execute event-triggered year-end leave balance conversion and carry-forward (Section 13)."""
    tx_list: list[YearEndTransaction] = []

    for uid in user_ids:
        is_faculty = is_faculty_map.get(uid, False)
        balances = {b.leave_category: b for b in get_user_balances(uid, year)}
        avail_map = {cat: b.available_days for cat, b in balances.items()}

        outcomes = compute_year_end_outcomes(avail_map, is_faculty=is_faculty)

        for out in outcomes:
            tx = YearEndTransaction.objects.create(
                user_id=uid,
                year=year,
                leave_category=out.category,
                closing_balance=out.previous_unused,
                lapsed_days=out.lapsed,
                converted_to_el=out.converted_to_el,
                carried_forward=out.carried_forward,
            )
            tx_list.append(tx)

            # Create or update new year's balance record
            next_b, _ = EmployeeLeaveBalance.objects.get_or_create(
                user_id=uid,
                year=year + 1,
                leave_category=out.category,
                defaults={
                    "allocated_days": out.new_allocated,
                    "carried_forward": out.carried_forward,
                    "availed_days": Decimal("0.0"),
                    "pending_days": Decimal("0.0"),
                },
            )
            next_b.allocated_days = out.new_allocated
            next_b.carried_forward = out.carried_forward
            next_b.save()

    return tx_list


@transaction.atomic
def publish_holiday(principal, data: dict) -> HolidayCalendar:
    """Publish a holiday or restricted holiday (Section 12)."""
    require(principal, "leave_elm.admin.manage")
    return HolidayCalendar.objects.create(
        date=data["date"],
        name=data["name"],
        is_restricted_holiday=data.get("is_restricted_holiday", False),
        is_published=True,
        year=data["date"].year,
    )
